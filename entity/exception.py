class APIException(Exception):  # 统一所有API错误的响应格式
    def __init__(self, message,status_code,payload=None):
        super(APIException, self).__init__()
        self.message = message  # 人类可读的错误描述（如"Task not found"）
        self.status_code = status_code  # HTTP状态码（如400、404）
        self.payload = payload  # 扩展数据（可选，用于携带额外错误信息）

    def to_dict(self):  # 将异常转换为字典格式，结构为：{"message": "错误描述","status_code": 400,// 其他通过payload传递的字段}
        rv = dict(self.payload or ())
        rv["message"] = self.message
        rv["status_code"] = self.status_code
        return rv

class TaskIndexError(APIException):  # 处理任务索引错误（如无效的任务ID格式）
    def __init__(self, message):
        super(TaskIndexError, self).__init__(message,status_code=400)

class TaskNotFoundError(APIException):  # 处理任务不存在的场景
    def __init__(self, message):
        super(TaskNotFoundError, self).__init__(message,status_code=400)
