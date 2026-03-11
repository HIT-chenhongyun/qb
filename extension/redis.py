from flask_redis import FlaskRedis

redis_client = FlaskRedis()  # 初始化一个 Redis 客户端

def init_app(app):
    redis_client.init_app(app)

