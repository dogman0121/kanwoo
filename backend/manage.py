from kanwoo import create_app
from config import config

app = create_app(config)
celery_app = app.extensions["celery"]

if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)
