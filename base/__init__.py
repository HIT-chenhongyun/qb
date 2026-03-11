from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy() # 创造了一个SQLAlchemy 的全局实例db 避免循环导入(Circular Import)的问题

