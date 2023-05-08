from flask import Flask
from flask_jwt_extended import JWTManager
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from scripts.models import Database

app = Flask(__name__)

app.config.from_pyfile('../config.py')
CORS(app)

jwt = JWTManager(app)
bcrypt = Bcrypt(app)

db = Database()
