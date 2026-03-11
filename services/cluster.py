from sqlalchemy import desc
from base.cluster import Task, Quality
from entity.cluster import SimpleTask, ComplexTask, QualityTask, QualityInput
from entity.exception import TaskIndexError, TaskNotFoundError

class TaskService:
    def __init__(self, db):
        self.db = db

    def simple_query(self,celery_id:str):
        task :Task= self.db.session.query(Task).filter_by(celery_id=celery_id).first()
        if task is None:
            raise TaskNotFoundError("队列不存在："+celery_id)
        quality :Quality= self.db.session.query(Quality).filter_by(task_id=task.id).order_by(desc(Quality.updated_at)).first()
        return SimpleTask(error=task.error if task.error is not None else "",
                          state=task.state if task.state is not None else "",
                          total=quality.total if quality.total is not None else 0,
                          current=quality.current if quality.current is not None else 0,
                          used_time=quality.used_time if quality.used_time is not None else 0.,
                          total_time=quality.total_time if quality.total_time is not None else 0.,
                          remain_time=quality.remain_time if quality.remain_time is not None else 0.)

    def complex_query(self,celery_id:str):
        complex_result :ComplexTask= ComplexTask(**self.simple_query(celery_id).model_dump())
        task: Task = self.db.session.query(Task).filter_by(celery_id=celery_id).first()
        quality: list[Quality] = self.db.session.query(Quality).filter_by(task_id=task.id).all()
        complex_result.quality = [QualityTask(quality=item.quality,
                                              iden=item.business_id if item.business_id is not  None else "",
                                              subject=item.subject if item.subject is not None else "",
                                              status=item.status if item.status is not None else "",
                                              classify=item.classify if item.classify is not None else -1,
                                              classify_name=item.classify_name if item.classify_name is not None else "") for item in quality]
        return complex_result

    def task_insert(self,celery_id:str, data:list[QualityInput]):
        task = self.db.session.query(Task).filter_by(celery_id=celery_id).first()
        if task is None:
            task = Task()
            task.celery_id = celery_id
            self.db.session.add(task)
            self.db.session.commit()
            self.db.session.refresh(task)
        else:
            if task.state != "finished":
                raise TaskIndexError("上一个任务还未完成")
        qualities = []
        for item in data:
            quality: Quality = Quality()
            quality.task_id=task.id
            quality.quality = item.quality.strip()
            quality.business_id = item.iden
            qualities.append(quality)
        self.db.session.add_all(qualities)
        self.db.session.commit()


# 服务层(Service Layer)，具体实现了关于"任务(Task)"的核心业务逻辑

# 简单查询 (simple_query)
# 作用：查询任务的概要信息（进度、耗时、状态），不包含具体每个条目的详情。
# 逻辑流程：
# 查主表：根据 celery_id（任务ID）去 Task 表查询。
# 异常检查：如果没查到，直接抛出 TaskNotFoundError。这会触发 entity/exception.py 里的逻辑，最终返回 400 错误。
# 查子表：去 Quality 表查属于该任务的记录。order_by(desc(Quality.updated_at)) 取最新的一条，通常用来代表当前的整体进度（total, current）。
# 数据转换 (ORM -> Pydantic)：
# 数据库里取出来的是 SQLAlchemy 对象（Task, Quality）。
# 返回给 Controller 的必须是 Pydantic 对象 (SimpleTask)。
# 这里做了大量繁琐的 if x is not None else default 判断，防止数据库字段为空导致程序崩溃。

# 复杂查询 (complex_query)
# 作用：查询任务的完整信息，包括所有子项的具体数据。
# 逻辑流程：
# 复用代码：先调用 self.simple_query(celery_id) 获取基础信息。
# 转换基类：利用 SimpleTask 的数据初始化一个 ComplexTask 对象。
# 查所有子项：filter_by(task_id=task.id).all() 获取该任务下所有的 Quality 记录。
# 列表推导式：遍历数据库查出的列表，逐个转换成 QualityTask 对象，放入 complex_result.quality 列表中。

# 任务插入 (task_insert)
# 作用：在开始跑任务之前，先把任务信息和待处理的数据写入数据库。
# 逻辑流程：
# 幂等性/防重检查：
# 先查一下这个 celery_id 是否已存在。
# 如果不存在：创建新 Task，入库。
# 如果存在：检查状态。如果 state != "finished"（即任务还在跑或失败），抛出 TaskIndexError("上一个任务还未完成")。这是非常重要的业务保护逻辑，防止同一个 ID 被重复提交导致数据混乱。
# 批量准备数据：
# 遍历传入的 data (类型是 list[QualityInput])。
# 将 QualityInput（API 接收的数据）转换为 Quality（数据库实体）。
# 关联外键 quality.task_id = task.id。
# 批量写入：使用 db.session.add_all(qualities) 一次性写入，提高性能。