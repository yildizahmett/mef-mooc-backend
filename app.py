from mef_mooc import create_app
from mef_mooc.config import FLASK_HOST, FLASK_PORT

app = create_app()

if __name__ == '__main__':
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=True)