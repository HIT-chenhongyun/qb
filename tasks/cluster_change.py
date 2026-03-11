import logging
import os
import re
import glob
import pickle
from datetime import datetime
from typing import Any
from flask_sqlalchemy import SQLAlchemy
from openai.types.chat import ChatCompletionUserMessageParam
from config import pd_config
from celery import shared_task
from tqdm import tqdm
import json
from base.cluster import Task, Quality
from utils.closeai import CloseAI
import numpy as np
from sklearn.cluster import KMeans

# ================= 配置与全局客户端初始化 =================
llm = CloseAI(base_url=pd_config.LLM_URL, api_key=pd_config.LLM_API_KEY)
extra_body = {"enable_thinking": False}
embedding_openAI = CloseAI(base_url=pd_config.EMBEDDING_URL, api_key=pd_config.EMBEDDING_API_KEY)
sim_rate = pd_config.SIM_RATE  # 0.5
rerank_rate = pd_config.RERANK_RATE  # 0.2
rerank_min_count = pd_config.RERANK_MIN_COUNT  # 最少需要3个rerank分数大于阈值
rerank_openAI = CloseAI(base_url=pd_config.RERANK_URL, api_key=pd_config.RERANK_API_KEY)
llm_name = pd_config.LLM_NAME
max_cluster = 30
top_k = 20
pattern = "```json\n(.*?)```"
prompt = """
请根据偏差描述提取其中的"物项"和"存在的不足"，结果请返回json，如果出现多个结果，输出其中重要的一个即可。
# 任务文本
{desc}
# 输出示例
```json
{{"subject":<物项>，"status":<存在的不足>}}
"""
summary_prompt = """
请用少于10个字总结一下任务文本。输出格式为json。
# 任务文本
{desc}
# 输出示例
```json
{{"summary":<10个字的总结>}}
"""
pkl_path = "pkl"
os.makedirs(pkl_path, exist_ok=True)

# ================= 新增：DBStream 流式聚类核心类 =================
class MicroCluster:
    def init(self, center, timestamp):
        self.center = center
        self.weight = 1.0
        self.last_update = timestamp
        self.points_count = 1

class DBStreamManager:
    def init(self, radius_epsilon=0.6, lambda_factor=0.01, batch_size=64):
        self.micro_clusters = []
        self.epsilon = radius_epsilon
        self.lambda_factor = lambda_factor
        self.all_embeddings = []
        self.all_texts = []
        self.buffer = []
        self.batch_size = batch_size

    def _get_embedding_batch(self, texts):
        if not texts: return []
        try:
            # 复用系统全局的 embedding_openAI 客户端
            response = embedding_openAI.embeddings.create(input=texts, model="bge-m3")
            return [np.array(item.embedding) for item in response.data]
        except Exception as e:
            print(f"API批次请求失败: {e}")
            return [None] * len(texts)

    def _decay_function(self, current_time, last_time):
        delta_t = (current_time - last_time).total_seconds()
        return np.exp(-self.lambda_factor * delta_t)

    def _update_cluster_logic(self, new_vec, current_time):
        if new_vec is None: return
        best_mc, min_dist = None, float('inf')

        for mc in self.micro_clusters:
            decay = self._decay_function(current_time, mc.last_update)
            mc.weight *= decay
            mc.last_update = current_time
            # 严格使用欧氏距离
            dist = np.linalg.norm(new_vec - mc.center)
            if dist < min_dist:
                min_dist, best_mc = dist, mc

        if best_mc and min_dist <= self.epsilon:
            new_weight = best_mc.weight + 1.0
            best_mc.center = (best_mc.center * best_mc.weight + new_vec) / new_weight
            best_mc.weight, best_mc.points_count = new_weight, best_mc.points_count + 1
        else:
            self.micro_clusters.append(MicroCluster(new_vec, current_time))

    def process_text(self, text):
        self.buffer.append(text)
        if len(self.buffer) >= self.batch_size:
            self._flush_buffer()

    def _flush_buffer(self):
        if not self.buffer: return
        current_time = datetime.now()
        embeddings = self._get_embedding_batch(self.buffer)

        for text, vec in zip(self.buffer, embeddings):
            if vec is not None:
                self._update_cluster_logic(vec, current_time)
                self.all_embeddings.append(vec)
                self.all_texts.append(text)
        self.buffer = []

    def cluster_exported_vectors(self, k, indices=None):
        if not self.all_embeddings:
            return None, "没有可用的向量数据"

        if indices is None:
            target_vecs = np.array(self.all_embeddings)
            target_texts = self.all_texts
        else:
            target_vecs = np.array([self.all_embeddings[i] for i in indices])
            target_texts = [self.all_texts[i] for i in indices]

        actual_k = min(k, len(target_vecs))
        if actual_k == 0:
            return None, "数据不足"

        kmeans = KMeans(n_clusters=actual_k, init='k-means++', n_init=10)
        labels = kmeans.fit_predict(target_vecs)
        return target_texts, labels

    def save_to_file(self, filepath):
        self._flush_buffer()
        state = {
            "micro_clusters": self.micro_clusters,
            "all_embeddings": self.all_embeddings,
            "all_texts": self.all_texts,
            "params": {"epsilon": self.epsilon, "lambda": self.lambda_factor}
        }
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)

    @classmethod
    def load_from_file(cls, filepath, **init_kwargs):
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        instance = cls(
            radius_epsilon=state['params']['epsilon'],
            lambda_factor=state['params']['lambda'],
            **init_kwargs
        )
        instance.micro_clusters = state['micro_clusters']
        instance.all_embeddings = state['all_embeddings']
        instance.all_texts = state['all_texts']
        return instance