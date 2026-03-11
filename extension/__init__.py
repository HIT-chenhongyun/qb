from extension import celery
from extension import database
from extension import migrate
from extension import redis
from extension import router

def init_app(app):
    database.init_app(app)
    redis.init_app(app)
    celery.init_app(app)
    migrate.init_app(app)
    router.init_app(app)

# 扩展初始化层

