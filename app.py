from flask import Flask
from config import Config
from models import db


app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
from routes.user_routes import *
from routes.admin_routes import *

def create_admin():
    admin = User.query.filter_by(email='admin@admin.com').first()

    if not admin:
        admin = User(
            email='admin@admin.com',
            password=generate_password_hash('admin@123'),
            fullName='System Admin',
            qualification='System Administrator',
            dob='',
            created_at=datetime.now(timezone.utc)
        )
        try:
            db.session.add(admin)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print('Error creating admin', e)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        create_admin()
    app.run(debug=True)