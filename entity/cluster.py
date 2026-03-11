from pydantic import BaseModel, Field, conlist

class SimpleTask(BaseModel):  # 基础任务状态模型，包含错误信息、任务状态、进度及时间统计字段
    error:str = Field(default="")  # 默认空字符串
    state:str = Field(default="")
    total:int = Field(default=0)
    current:int = Field(default=0)
    used_time:float = Field(default=0.)  # 默认 0.0
    total_time:float = Field(default=0.)
    remain_time:float = Field(default=0.)

class QualityTask(BaseModel):  # 质量检测任务模型，包含任务标识(iden)、物项、状态、质量评级等字段
    iden:str = Field(default="")
    subject:str = Field(default="")
    status:str = Field(default="")
    quality:str = Field(default="")
    classify:int = Field(default=-1)
    classify_name: str = Field(default="")

class ComplexTask(SimpleTask):  # 继承自 SimpleTask，扩展了 quality 字段，表示包含多个质检任务的复杂任务状态
    # ComplexTask 继承自 SimpleTask，复用基础字段并扩展新字段
    quality:list[QualityTask] = Field(default=[])

class QueryTaskInput(BaseModel):  # 查询任务输入模型，immediately 表示是否立即刷新任务状态
    immediately:bool = Field(default=False)

class QualityInput(BaseModel):  # 质检输入项模型，iden 和 quality 为必填字段
    iden:str = Field()
    quality:str = Field()

class CreateTaskInput(BaseModel):  # 创建任务输入模型，包含可选的 task_id 和必填的质检项列表(长度限制 1~10000)
    task_id:str = Field(default=None)
    quality:conlist(QualityInput,min_length=1,max_length=10000) = Field()  # conlist：用于定义列表的长度限制

class TaskOutput(BaseModel):  # 任务创建响应模型，仅返回 task_id
    task_id: str = Field(default="")

# BaseModel 是 Pydantic 库的核心基类，它的核心作用是数据验证和结构化数据处理，专门解决 API 开发中常见的「数据不规范」问题。

