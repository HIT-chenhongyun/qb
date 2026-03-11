from flask_migrate import Migrate
from base import db

migrate = Migrate()

def init_app(app):
    migrate.init_app(app,db)
    from base.cluster import Task, Quality