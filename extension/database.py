from base import db
# 将 base/__init__.py 中创建的空的 db = SQLAlchemy() 实例，与 Flask 应用实例绑定

def init_app(app):
    db.init_app(app)
    # 这里调用 db.init_app(app) 后，SQLAlchemy 知道连接哪个数据库
    # 使 service/cluster.py 里使用的 db.session 能够正常工作

