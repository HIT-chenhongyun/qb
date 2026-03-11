import logging
import os
import re
import glob
import pickle
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


llm = CloseAI(base_url=pd_config.LLM_URL, api_key=pd_config.LLM_API_KEY)
extra_body = {"enable_thinking":False}
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
```
"""
summary_prompt = """
请用少于10个字总结一下任务文本。输出格式为json。
# 任务文本
{desc}
# 输出示例
```json
{{"summary":<10个字的总结>}}
```
"""
pkl_path = "pkl"
os.makedirs(pkl_path, exist_ok=True)

@shared_task
def index_task(celery_id:str):
    from flask import current_app
    current_app.logger.info(f"indexing {celery_id}")
    db :SQLAlchemy= current_app.extensions.get("sqlalchemy")
    task :Task = db.session.query(Task).filter_by(celery_id=celery_id).first()
    quality:list[Quality] = db.session.query(Quality).filter(Quality.task_id==task.id, Quality.subject == None, Quality.status == None).all()
    tasks :list[str]= [str(item.quality) for item in quality]
    task.state = "indexing"
    db.session.commit()
    try:
        for info in llm_deal(tasks,current_app.logger):
            current_app.logger.debug(f"info {info}")
            if info["state"] == "indexing":
                one_qual = quality[info["index"]]
                one_qual.status = str(info['status'][0])
                one_qual.subject = str(info['subject'][0])
                one_qual.total = info["meta"]["total"]
                one_qual.current = info["meta"]["current"]
                one_qual.used_time = info["meta"]["used_time"]
                one_qual.total_time = info["meta"]["total_time"]
                one_qual.remain_time = info["meta"]["remain_time"]
                db.session.commit()
            if info["state"] == "index_finish":
                task.state = info["state"]
                db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        task.state = "error"
        task.error = "index state:"+str(e)
        db.session.commit()

@shared_task
def cluster_task(parent_output:Any,celery_id:str):
    from flask import current_app
    current_app.logger.info(f"clustering {celery_id}")
    db: SQLAlchemy = current_app.extensions.get("sqlalchemy")
    task :Task = db.session.query(Task).filter_by(celery_id=celery_id).first()
    task.state = "clustering"
    db.session.commit()
    quality:list[Quality] = db.session.query(Quality).filter(Quality.task_id==task.id, Quality.subject != None, Quality.status != None).all()
    subject = [item.subject for item in quality]
    status = [item.status for item in quality]
    try:
        for info in cluster(subject,status,celery_id,current_app.logger):
            if info["state"] == "clustering":
                one_qual = quality[info["index"]]
                one_qual.classify = int(info["type"])
                one_qual.total = info["meta"]["total"]
                one_qual.current = info["meta"]["current"]
                one_qual.used_time = info["meta"]["used_time"]
                one_qual.total_time = info["meta"]["total_time"]
                one_qual.remain_time = info["meta"]["remain_time"]
                db.session.commit()
        task.state = "cluster_finished"
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        task.state = "error"
        task.error = "index state:"+str(e)
        db.session.commit()

@shared_task
def summary_task(parent_output:Any,celery_id:str):
    from flask import current_app
    db: SQLAlchemy = current_app.extensions.get("sqlalchemy")
    task: Task = db.session.query(Task).filter_by(celery_id=celery_id).first()
    task.state = "summary"
    db.session.commit()
    quality: list[Quality] = db.session.query(Quality).filter(Quality.task_id == task.id, Quality.classify != None).all()
    quality_text = [item.quality for item in quality]
    classify = [item.classify for item in quality]
    classify_name = [item.classify_name for item in quality]
    for info in summary(quality_text,classify,classify_name,current_app.logger):
        if info["state"] == "summary":
            for index,item in enumerate(info["summary"]):
                if item is None:
                    continue
                one_qual = quality[index]
                one_qual.classify_name = item
                one_qual.total = info["meta"]["total"]
                one_qual.current = info["meta"]["current"]
                one_qual.used_time = info["meta"]["used_time"]
                one_qual.total_time = info["meta"]["total_time"]
                one_qual.remain_time = info["meta"]["remain_time"]
            db.session.commit()
    task.state = "finished"
    db.session.commit()

def cosine_similarity(vec, vec_list):
    sim = np.dot(vec, vec_list.T)
    return sim

def summary(quality:list[str], classify:list[int], classify_name:list[str], logger:logging.Logger=None):
    unique_classify,classify_count = np.unique(classify,return_counts=True)
    healthy_unique_classify = unique_classify[classify_count>=max_cluster]
    # healthy_quality = np.isin(quality, healthy_unique_classify)
    # healthy_classify = np.isin(classify, healthy_unique_classify)
    iter = tqdm(healthy_unique_classify)
    for unique_classify in iter:
        timed = iter.last_print_t-iter.start_t
        total_time = (timed / iter.last_print_n) * iter.total if iter.last_print_n != 0 else 0
        extra_time = total_time - timed
        classify_names = np.array(classify_name)[np.array(classify)==unique_classify]
        classify_named = classify_names[classify_names != None]
        if len(classify_named)!=0:
            old_names = np.array([None]*len(classify))
            old_names[np.array(classify)==unique_classify] = classify_named[0]
            yield {
                "state": "summary",
                "error": None,
                "summary": old_names,
                "meta": {
                    "total": iter.total,
                    "current": iter.last_print_n,
                    "used_time": timed,
                    "total_time": total_time,
                    "remain_time": extra_time,
                }
            }
        unique_quality = np.array(quality)[np.array(classify)==unique_classify][:top_k]  # 从 quality 数组中，筛选出那些对应的 classify 标签等于 unique_classify 的元素，并取筛选结果的前 top_k
        message = ChatCompletionUserMessageParam(
            content=summary_prompt.format(desc=str(unique_quality.tolist())),
            role="user")
        resp = llm.chat.completions.create(messages=[message], model=llm_name,extra_body=extra_body)
        logger.debug(resp.choices[0].message.content)
        res = json.loads(
            re.search(pattern, resp.choices[0].message.content, re.DOTALL).group(1))
        new_names = np.array([None] * len(classify))
        new_names[np.array(classify)==unique_classify]=res["summary"]
        yield {
            "state": "summary",
            "error": None,
            "summary": new_names,
            "meta": {
                "total": iter.total,
                "current": iter.last_print_n,
                "used_time": timed,
                "total_time": total_time,
                "remain_time": extra_time,
            }
        }
    timed = iter.last_print_t-iter.start_t
    total_time = (timed / iter.last_print_n) * iter.total if iter.last_print_n != 0 else 0
    extra_time = total_time - timed
    yield {
        "state": "finished",
        "error": None,
        "meta": {
            "total": iter.total,
            "current": iter.last_print_n,
            "used_time": timed,
            "total_time": total_time,
            "remain_time": extra_time,
        }
    }

def cluster(subject:list[str],status:list[str],celery_id:str,logger:logging.Logger=None):
    pak_pattern = os.path.join(pkl_path, f"{celery_id}*")
    files = glob.glob(pak_pattern)
    # 存储聚类中心信息
    cluster_centers = []  # 每个聚类的中心向量
    cluster_members = []  # 每个聚类的成员数量
    cluster_descriptions = []  # 每个聚类的代表性描述

    result_type = []
    result_items = []
    if len(files) > 0:
        try:
            cluster_centers = pickle.load(open(os.path.join(pkl_path, f"{celery_id}-cluster_centers.pkl"), "rb"))
            cluster_members = pickle.load(open(os.path.join(pkl_path, f"{celery_id}-cluster_members.pkl"), "rb"))
            cluster_descriptions = pickle.load(open(os.path.join(pkl_path, f"{celery_id}-cluster_descriptions.pkl"), "rb"))
            result_type = pickle.load(open(os.path.join(pkl_path, f"{celery_id}-result_type.pkl"), "rb"))
            result_items = pickle.load(open(os.path.join(pkl_path, f"{celery_id}-result_items.pkl"), "rb"))
        except Exception as e:
            if logger:
                logger.error(e)
    i = 0
    iter = tqdm(zip(subject, status),total=len(subject))
    for item,item2 in iter:
        timed = iter.last_print_t-iter.start_t
        total_time = (timed / iter.last_print_n) * iter.total if iter.last_print_n != 0 else 0
        extra_time = total_time - timed
        item=str(item)
        item2=str(item2)
        embedding_res = np.array([embedding_openAI.embeddings.create(input=item, model="bge-m3").data[0].embedding])

        if len(cluster_centers) == 0:
            # 第一个样本，创建第一个聚类
            cluster_centers.append(embedding_res[0])
            cluster_members.append(1)
            cluster_descriptions.append([item])
            result_type.append(0)
            yield {
                "state": "clustering",
                "index": i,
                "error": None,
                "type":0,
                "meta": {
                    "total": iter.total,
                    "current": iter.last_print_n,
                    "used_time": timed,
                    "total_time": total_time,
                    "remain_time": extra_time,
                }
            }
        else:
            # 与所有聚类中心计算相似度
            sim_vec = cosine_similarity(embedding_res[0], np.array(cluster_centers))
            top = np.zeros(len(sim_vec),dtype=bool)
            top[np.argsort(sim_vec)[::-1][:5]] = True
            # 找出所有相似度大于阈值的聚类
            candidate_indices = np.where((sim_vec >= sim_rate) & top)[0]
            if candidate_indices.size > 0:
                index_top = np.isin(result_type, candidate_indices)
                index_type = np.array(result_type)[index_top]
                item_index = np.array(result_items)[index_top]
                # res = embedding_openAI.embeddings.create(input=item_index.tolist(), model="bge-m3")
                embedding_subject_res = np.array(
                    [e.embedding for e in embedding_openAI.embeddings.create(input=item2, model="bge-m3").data])
                embedding_item_res = np.array(
                    [e.embedding for e in embedding_openAI.embeddings.create(input=item_index, model="bge-m3").data])
                sim_vec = cosine_similarity(embedding_subject_res[0], embedding_item_res)
                index_type = index_type[sim_vec >= sim_rate]
                # 按相似度从高到低排序候选聚类
                candidate_scores = sim_vec[sim_vec >= sim_rate]
                sorted_indices = index_type[np.argsort(candidate_scores)[::-1]]

                assigned = False
                best_cluster_idx = None
                best_high_score_count = 0

                # 逐一检查每个候选聚类
                for cluster_idx in sorted_indices:
                    current_cluster_size = cluster_members[cluster_idx]

                    # 与当前聚类中的代表性样本进行rerank
                    rerank_res = rerank_openAI.rerank.create(  # 调用 utils\closeai.py 定义的 creat 方法
                        query=item,
                        documents=cluster_descriptions[cluster_idx],
                        model="bge-reranker-v2-m3"
                    )
                    # 获取所有rerank分数
                    rerank_scores = [result.relevance_score for result in rerank_res.results]

                    # 统计大于阈值的rerank分数数量
                    high_score_count = sum(score >= rerank_rate for score in rerank_scores)
                    avg_score = sum(rerank_scores) / len(rerank_scores) if rerank_scores else 0

                    # 启发式策略：根据聚类大小调整判断条件
                    if current_cluster_size < rerank_min_count:
                        # 对于小聚类，宽松条件
                        if high_score_count >= 1 or avg_score >= rerank_rate:
                            best_cluster_idx = cluster_idx
                            best_high_score_count = high_score_count
                            assigned = True
                            break  # 找到第一个满足条件的就分配
                    else:
                        # 对于大聚类，严格条件
                        if high_score_count >= rerank_min_count:
                            best_cluster_idx = cluster_idx
                            best_high_score_count = high_score_count
                            assigned = True
                            break  # 找到第一个满足条件的就分配
                        # 如果没有立即满足，记录最好的候选（用于后续选择）
                        elif high_score_count > best_high_score_count:
                            best_cluster_idx = cluster_idx
                            best_high_score_count = high_score_count

                if assigned:
                    yield {
                        "state": "clustering",
                        "index": i,
                        "error": None,
                        "type": best_cluster_idx,
                        "meta": {
                            "total": iter.total,
                            "current": iter.last_print_n,
                            "used_time": timed,
                            "total_time": total_time,
                            "remain_time": extra_time,
                        }
                    }
                    # 分配到现有聚类
                    result_type.append(best_cluster_idx)
                    # 更新聚类中心
                    n = cluster_members[best_cluster_idx]
                    old_center = cluster_centers[best_cluster_idx]
                    new_center = (old_center * n + embedding_res[0]) / (n + 1)
                    cluster_centers[best_cluster_idx] = new_center
                    cluster_members[best_cluster_idx] += 1
                    # 添加代表性描述
                    if len(cluster_descriptions[best_cluster_idx]) < 10:
                        cluster_descriptions[best_cluster_idx].append(item)
                    else:
                        # 替换策略：可以替换分数最低的或最旧的
                        cluster_descriptions[best_cluster_idx].pop(0)  # 移除最旧的
                        cluster_descriptions[best_cluster_idx].append(item)
                else:
                    # 如果没有聚类满足条件，但存在候选聚类，选择最好的一个
                    if best_cluster_idx is not None and best_high_score_count > 0:
                        # 启发式：如果最好的候选有至少1个高分，还是分配过去
                        yield {
                            "state": "clustering",
                            "index": i,
                            "error": None,
                            "type": best_cluster_idx,
                            "meta": {
                                "total": iter.total,
                                "current": iter.last_print_n,
                                "used_time": timed,
                                "total_time": total_time,
                                "remain_time": extra_time,
                            }
                        }
                        result_type.append(best_cluster_idx)
                        n = cluster_members[best_cluster_idx]
                        old_center = cluster_centers[best_cluster_idx]
                        new_center = (old_center * n + embedding_res[0]) / (n + 1)
                        cluster_centers[best_cluster_idx] = new_center
                        cluster_members[best_cluster_idx] += 1
                        if len(cluster_descriptions[best_cluster_idx]) < 10:
                            cluster_descriptions[best_cluster_idx].append(item)
                    else:
                        # 创建新聚类
                        new_cluster_idx = len(cluster_centers)
                        cluster_centers.append(embedding_res[0])
                        cluster_members.append(1)
                        cluster_descriptions.append([item])
                        yield {
                            "state": "clustering",
                            "index": i,
                            "error": None,
                            "type": new_cluster_idx,
                            "meta": {
                                "total": iter.total,
                                "current": iter.last_print_n,
                                "used_time": timed,
                                "total_time": total_time,
                                "remain_time": extra_time,
                            }
                        }
                        result_type.append(new_cluster_idx)

            else:
                # 没有相似度大于阈值的聚类，创建新聚类
                new_cluster_idx = len(cluster_centers)
                cluster_centers.append(embedding_res[0])
                cluster_members.append(1)
                cluster_descriptions.append([item])
                yield {
                    "state": "clustering",
                    "index": i,
                    "error": None,
                    "type": new_cluster_idx,
                    "meta": {
                        "total": iter.total,
                        "current": iter.last_print_n,
                        "used_time": timed,
                        "total_time": total_time,
                        "remain_time": extra_time,
                    }
                }
                result_type.append(new_cluster_idx)
        result_items.append(item2)
        pickle.dump(cluster_centers,open(os.path.join(pkl_path,f"{celery_id}-cluster_centers.pkl"), "wb"))
        pickle.dump(cluster_members,open(os.path.join(pkl_path,f"{celery_id}-cluster_members.pkl"), "wb"))
        pickle.dump(cluster_descriptions,open(os.path.join(pkl_path,f"{celery_id}-cluster_descriptions.pkl"), "wb"))
        pickle.dump(result_type,open(os.path.join(pkl_path,f"{celery_id}-result_type.pkl"), "wb"))
        pickle.dump(result_items,open(os.path.join(pkl_path,f"{celery_id}-result_items.pkl"), "wb"))
        i+=1


def llm_deal(tasks:list[str],logger:logging.Logger=None):
    subject = []
    status = []
    iter = tqdm(tasks)
    i=0
    for task in iter:
        error_time = 3
        while True:
            timed = iter.last_print_t-iter.start_t
            total_time = (timed / iter.last_print_n) * iter.total if iter.last_print_n != 0 else 0
            extra_time = total_time - timed
            try:
                message = ChatCompletionUserMessageParam(
                    content=prompt.format(desc=task),
                    role="user")
                resp = llm.chat.completions.create(messages=[message], model=llm_name,extra_body=extra_body)
                logger.debug(resp.choices[0].message.content)
                res = json.loads(
                    re.search(pattern, resp.choices[0].message.content, re.DOTALL).group(1))
                subject.append(res.get("subject", ""))
                status.append(res.get("status", ""))
                yield {
                    "state":"indexing",
                    "index":i,
                    "error": None,
                    "subject":[res.get("subject", "")],
                    "status":[res.get("status", "")],
                    "meta":{
                        "total":iter.total,
                        "current":iter.last_print_n,
                        "used_time":timed,
                        "total_time":total_time,
                        "remain_time":extra_time,
                    }
                }
                break
            except Exception as e:
                if error_time ==0:
                    raise e
                error_time-=1
                if logger:
                    logger.error(e)
        i+=1
    yield {
                "state":"index_finish",
                "index": -1,
                "error": None,
                "subject": subject,
                "status": status,
                "meta":{
                    "total":iter.total,
                    "current":iter.last_print_n,
                    "used_time":iter.last_print_t-iter.start_t,
                    "total_time":((iter.last_print_t-iter.start_t) / iter.last_print_n) * iter.total if iter.last_print_n != 0 else 0,
                    "remain_time":0.,
                }
            }