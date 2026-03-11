def init_app(app):
    from controllers.cluster import router  # 将 controllers 里定义的蓝图(Blueprint)注册到 Flask 主应用上
    app.register_blueprint(router)

