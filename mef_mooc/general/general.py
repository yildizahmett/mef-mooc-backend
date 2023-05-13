from flask import Blueprint
from mef_mooc.scripts.models import db

general_app = Blueprint('general_app', __name__, url_prefix='/general')

@general_app.route("/all-departments", methods=['GET'])
def all_departments():
    try:
        departments = db.fetch("SELECT * FROM department")
        return {"departments": departments}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500

@general_app.route("/all-coordinators", methods=['GET'])
def all_coordinators():
    try:
        coordinators = db.fetch("SELECT id, CONCAT(name, ' ', surname) as name FROM coordinator")
        return {"coordinators": coordinators}, 200
    except Exception as e:
        print(e)
        return {"message": "An error occured"}, 500
