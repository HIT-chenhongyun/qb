from app import celery

if __name__ == '__main__':
    args = ["worker","--loglevel=DEBUG","--max-tasks-per-child=50"]
    # "worker": 告诉 Celery 启动 worker 模式
    # "--loglevel=DEBUG": 设置日志级别为调试模式，打印详细信息
    # "--max-tasks-per-child=50":
    #    这是一个内存保护机制。意思是每个子进程处理完 50 个任务后就自动销毁重建。
    #    这通常用于防止 Python 任务中有内存泄漏导致服务器内存被吃光。
    celery.worker_main(args)