from flask import Flask
from config import Config
from backend.models import db
from backend.routes import init_route


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
init_route(app)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)