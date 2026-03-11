import uuid
from flask import Blueprint,current_app
from flask_pydantic import validate
from services.cluster import TaskService
from entity.cluster import QueryTaskInput, CreateTaskInput, TaskOutput
from tasks.cluster import index_task, cluster_task, summary_task
from base import db

router = Blueprint("info", __name__,url_prefix="/api/v1/task")
# 创建一个名为"info"的蓝图
# 路由前缀：所有在这个文件中定义的接口，URL都会已 /api/v1/task 开头，例如下面的 /query 会变成 /api/v1/task/query/<iden>
# 模块化：允许将路由逻辑从 app.py 中剥离出来，方便管理

@router.route('/query/<iden>', methods=['GET'])
@validate()
def task_query(query:QueryTaskInput, iden):
    task_service = TaskService(db)
    if not query.immediately:
        return task_service.simple_query(iden)
    return task_service.complex_query(iden)

@router.route('/create', methods=['POST'])
@validate()
def task_create(body:CreateTaskInput):
    # 1. 生成或复用 Task ID
    if body.task_id is None:
        task_id = str(uuid.uuid4())
    else:
        task_id = body.task_id
    # 2. 存入数据库
    task_service = TaskService(db)
    task_service.task_insert(task_id, body.quality)
    # 3. 编排并执行 Celery 异步任务链
    complex_task = (index_task.s(task_id)|cluster_task.s(task_id)|summary_task.s(task_id))()
    # 执行耗时任务
    # 4. 返回结果
    return TaskOutput(task_id=task_id)

# Flask应用中的控制器层，主要职责是定义API接口路由，接收HTTP请求，调用业务逻辑(service)，并安排后台异步任务(celery)

