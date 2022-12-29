from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, create_access_token, get_jwt
from flask_bcrypt import Bcrypt
from flask_cors import CORS
from models import Database

app = Flask(__name__)
app.config.from_pyfile('config.py')
CORS(app)

jwt = JWTManager(app)
bcrypt = Bcrypt(app)

db = Database()
