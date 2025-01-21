from flask import Flask, render_template
from config import Config
from backend.models import db

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404



if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)