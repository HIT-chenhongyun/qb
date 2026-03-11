from celery import Celery, Task

from config import pd_config

def init_app(app):  # 配置并初始化 Celery

    class FlaskTask(Task):  # 重写了 Celery 的基础任务类
    # 这个类确保每次执行任务前，先推入 app.app_context() ，让任务能够连接上数据库
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():  # <--- 关键点
                return self.run(*args, **kwargs)

    celery_app = Celery(
        app.name,
        task_cls=FlaskTask,
        broker=pd_config.CELERY_BROKER_URL,
        backend=pd_config.CELERY_BACKEND,
        task_ignore_result=True,
    )

    celery_app.conf.update(
        result_backend=pd_config.CELERY_RESULT_BACKEND,
        broker_connection_retry_on_startup=False,
        worker_hijack_root_logger=False
    )

    celery_app.set_default()
    app.extensions["celery"] = celery_app


