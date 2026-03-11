from sqlalchemy import func
from base import db
# 定义模型
class Quality(db.Model):
    id = db.Column(db.String(255), primary_key=True, server_default=db.text("gen_random_uuid()"))
    business_id = db.Column(db.String(255), nullable=False)
    task_id = db.Column(db.String(255), nullable=False)
    quality = db.Column(db.String(255), nullable=False)
    subject = db.Column(db.String(255))
    status = db.Column(db.String(255))
    classify = db.Column(db.Integer)
    classify_name = db.Column(db.String(255))
    total = db.Column(db.Integer)
    current = db.Column(db.Integer)
    used_time = db.Column(db.Double)
    total_time = db.Column(db.Double)
    remain_time = db.Column(db.Double)
    created_at = db.Column(db.DateTime, server_default=func.current_timestamp())
    updated_at = db.Column(db.DateTime, server_default=func.current_timestamp(),onupdate=func.current_timestamp())

class Task(db.Model):
    id = db.Column(db.String(255), primary_key=True, server_default=db.text("gen_random_uuid()"))
    celery_id = db.Column(db.String(255), unique=True, nullable=False)
    error = db.Column(db.String(255))
    state = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, server_default=func.current_timestamp())
    updated_at = db.Column(db.DateTime, server_default=func.current_timestamp(),onupdate=func.current_timestamp())

# 字段名 = db.Column(
#     数据类型,
#     primary_key=布尔值,   # 是否为主键
#     nullable=布尔值,      # 是否允许为空（默认True）
#     default=默认值,       # Python 层面的默认值
#     server_default=默认值, # 数据库层面的默认值
#     unique=布尔值,        # 是否唯一
#     onupdate=更新时操作   # 更新时触发的动作
# )

# UUID（通用唯一标识符）一种 128 位全局唯一标识符，形如 550e8400-e29b-41d4-a716-446655440000。
# 无需中央分配，可在分布式系统中生成唯一ID。

# 主键（Primary Key）
# 数据库表中唯一标识每一行数据的列（或列组合）。
# 类似身份证号，确保每条记录的唯一性。
# 特点
# 唯一性：不允许重复值。
# 非空性：值不能为 NULL。
# 不可变性：创建后不应修改。

# 外键（Foreign Key）
# 用于建立表与表之间关系的字段。
# 外键指向另一张表的主键，确保数据的引用完整性。
# 特点
# 关联性：外键值必须存在于被引用表的主键中（或为 NULL）。
# 级联操作：可定义删除/更新时的行为（如级联删除）。