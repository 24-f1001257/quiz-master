from flask import request, redirect, flash, render_template, url_for, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from datetime import timedelta
from utils import *
from app import app

@app.route('/')
def to_home():
    return redirect('home')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/login', methods=["GET","POST"])
def login():

    userID = request.cookies.get('user_id')

    if userID is not None:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':

        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash("Email and password are required to Login!!", 'danger')
            return render_template('login.html')
        
        existingUser = User.query.filter(User.email == email).first()

        if not check_password_hash(existingUser.password, password):
            flash('Wrong Password!', 'danger')
            return redirect(url_for('login'))
        
        response = make_response(redirect(url_for('dashboard')))
        
        response.set_cookie(
            'user_id', 
            str(existingUser.id),
            max_age=timedelta(days=30),  
            httponly=True,
            secure=True,
            samesite='Strict'
        )
        
        flash('Login Successful!!', 'success')
        return response

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

        response = make_response(redirect(url_for('dashboard')))
        response.set_cookie(
            'user_id',
            str(new_user.id),
            max_age = timedelta(days=30),
            httponly=True,
            secure=True,
            samesite='Strict'
        )

        flash('Account created successfully!', 'success')
        return response
    return render_template('signup.html')


quizzes = [
    {"id": 1, "no_of_questions": 10, "date": "2025-02-01", "duration": "00:30"},
    {"id": 2, "no_of_questions": 15, "date": "2025-02-05", "duration": "00:45"},
    {"id": 3, "no_of_questions": 20, "date": "2025-02-10", "duration": "01:00"},
]

stats = {
    "total_quizzes": 12,
    "highest_score": 95,
    "average_score": 78,
}

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = request.cookies.get('user_id')
    user = User.query.get(user_id)
    return render_template('dash.html', user=user, quizzes=quizzes, stats=stats)

@app.route('/logout')
@login_required
def logout():
    response = make_response(redirect(url_for('login')))
    response.delete_cookie('user_id')
    return response


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
