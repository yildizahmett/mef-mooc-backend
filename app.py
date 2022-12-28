from flask import Flask
from models import Database

app = Flask(__name__)
db = Database()

@app.route("/")
def index():
    return "Hello World!"


if __name__ == "__main__":
    app.run(debug=True)

