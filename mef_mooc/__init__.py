from flask import Flask
from flask_cors import CORS

from mef_mooc.student.students import student_app
from mef_mooc.general.general import general_app
from mef_mooc.admin.admin import admin_app
from mef_mooc.coordinator.coordinators import coordinator_app
from mef_mooc.scripts.extensions import jwt, bcrypt

def create_app():
    app = Flask(__name__)
    app.register_blueprint(student_app)
    app.register_blueprint(general_app)
    app.register_blueprint(admin_app)
    app.register_blueprint(coordinator_app)

    app.config.from_pyfile('config.py')
    CORS(app)

    jwt.init_app(app)
    bcrypt.init_app(app)

    return app
