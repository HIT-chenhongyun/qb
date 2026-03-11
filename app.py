from flask import Flask,jsonify
from config import pd_config
from entity.exception import APIException
from extension import init_app
app = Flask(__name__)  # 创建一个Flask应用实例
app.config.from_mapping(pd_config.model_dump())  # 加载配置  .model_dump()将Pydantic模型实例转化为Python原生字典格式
init_app(app)  # 集中初始化Flask扩展
with app.app_context():
    app.extensions["sqlalchemy"].create_all()  # 会执行SQLAlchemy的create_all()方法，根据模型类生成数据库表（需确保模型已正确导入）

@app.errorhandler(APIException)  # 统一异常处理：将自定义异常APIException转换为标准JSON响应，确保API错误信息格式一致
def handler_api_exception(error):  # 出现APIException类型异常，就调用handler_api_exception()这个函数处理
    return jsonify(error.to_dict()), error.status_code

celery = app.extensions["celery"]
@app.route("/healthy", methods=['GET'])
def healthy():
    return jsonify({"state":"healthy"}), 200  # 验证服务是否正常运行

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001,debug=True)  # 启动开发服务器

