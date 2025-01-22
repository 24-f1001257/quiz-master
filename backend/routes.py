from flask import request, redirect, flash, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from backend.models import db, User
from datetime import date


def init_route(app):

    @app.route('/')
    def to_home():
        return redirect('home')
    
    @app.route('/home')
    def home():
        return render_template('home.html')

    @app.route('/login', methods=["GET","POST"])
    def login():
        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            if not email or not password:
                flash("Email and password are required to Login!!", 'danger')
                return render_template('login.html')
            
            existingUser = User.query.filter(User.email == email).first()

            if not check_password_hash(existingUser.password, password):
                flash('Wrong Password!')
                return render_template('login.html')
            
            flash('Login Successful!!', 'success')


        return render_template('login.html')

    @app.route('/signup', methods=["GET", "POST"])
    def signup():
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            fullName = request.form.get('fullName')
            email = request.form.get('email')
            qualification = request.form.get('qualification')
            dob = request.form.get('dob')

            if not username or not password or not email:
                flash("username, password and email are mandatory fields.", 'error')
                return render_template('signup.html')

            if len(password) < 8:
                flash("Password must be of at least 8 characters.", 'error')
                return render_template('signup.html')
            
            existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
            if existing_user:
                flash('Username or email already exists. Please try again.', 'danger')
                return render_template('signup.html')

            hashed_password = generate_password_hash(password)
            new_user = User(
                username=username,
                password=hashed_password,
                fullName=fullName,
                email=email,
                qualification=qualification,
                dob=dob,
            )
            db.session.add(new_user)
            db.session.commit()

            flash('Account created successfully!', 'success')
            return redirect('/login')
        return render_template('signup.html')

    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('404.html'), 404
