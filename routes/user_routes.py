from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import *
from utils import *
from app import app
from datetime import datetime, timezone

@app.route('/')
def to_home():
    return redirect('home')

@app.route('/home')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        isAdmin = email == 'admin@admin.com'

        if not email or not password:
            flash('Please fill all fields!', 'danger')
            return redirect(url_for('login'))

        if isAdmin:
            admin = User.query.filter_by(email='admin@admin.com').first()
            if admin and check_password_hash(admin.password, password):
                session['admin_id'] = admin.id
                session.permanent = True
                flash('Welcome Admin!', 'success')
                return redirect(url_for('admin'))
            else:
                flash('Invalid admin credentials!', 'danger')
                return redirect(url_for('login'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session.permanent = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        
        flash('Invalid email or password!', 'danger')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        fullName = request.form.get('fullName')
        email = request.form.get('email')
        qualification = request.form.get('qualification')
        dob = request.form.get('dob')

        if not all([username, password, fullName, email]):
            flash('Please fill all required fields!', 'danger')
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('signup'))

        try:
            dob = datetime.strptime(dob, '%Y-%m-%d') if dob else None
        except ValueError:
            flash('Invalid date format!', 'danger')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        
        new_user = User(
            username=username,
            password=hashed_password,
            fullName=fullName,
            email=email,
            qualification=qualification,
            dob=dob if dob else None,
            created_at=datetime.now(timezone.utc)
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error during registration!', 'danger')
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    subjects = Subject.query.all()
    for subject in subjects:
        subject.chapters = Chapter.query.filter_by(subject_id=subject.id).all()
        for chapter in subject.chapters:
            chapter.quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
    
    stats = {
        'total_quizzes': QuizAttempt.query.filter_by(user_id=user_id).count(),
        'highest_score': db.session.query(db.func.max(Score.total_scored)).filter_by(user_id=user_id).scalar(),
        'average_score': db.session.query(db.func.avg(Score.total_scored)).filter_by(user_id=user_id).scalar()
    }
    
    return render_template('dash.html', subjects=subjects, user=user, stats=stats)

@app.route('/quiz/<int:quiz_id>/start', methods=['POST'])
@login_required
def start_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    user_id = session.get('user_id')
    
    existing_attempt = QuizAttempt.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id,
        end_time=None
    ).first()
    
    if existing_attempt:
        flash('You already have an ongoing attempt for this quiz!', 'warning')
        return redirect(url_for('take_quiz', quiz_id=quiz_id))
    
    new_attempt = QuizAttempt(
        user_id=user_id,
        quiz_id=quiz_id,
        start_time=datetime.now(timezone.utc)
    )
    
    try:
        db.session.add(new_attempt)
        db.session.commit()
        return redirect(url_for('take_quiz', quiz_id=quiz_id))
    except Exception as e:
        db.session.rollback()
        flash('Error starting quiz!', 'danger')
        return redirect(url_for('dashboard'))

@app.route('/quiz/<int:quiz_id>/take')
@login_required
def take_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    user_id = session.get('user_id')
    
    current_attempt = QuizAttempt.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id,
        end_time=None
    ).first()
    
    if not current_attempt:
        flash('Please start the quiz first!', 'warning')
        return redirect(url_for('dashboard'))
    
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    for question in questions:
        question.options = Option.query.filter_by(question_id=question.id).all()
        
        existing_response = UserResponse.query.filter_by(
            quiz_attempt_id=current_attempt.id,
            question_id=question.id
        ).first()
        
        if existing_response:
            question.selected_option = existing_response.selected_option_id
    
    time_remaining = quiz.time_duration * 60 - (datetime.now(timezone.utc) - current_attempt.start_time).seconds
    
    if time_remaining <= 0:
        submit_quiz(quiz_id)
        flash('Time\'s up! Quiz submitted automatically.', 'info')
        return redirect(url_for('dashboard'))
    
    return render_template(
        'quiz.html',
        quiz=quiz,
        questions=questions,
        time_remaining=time_remaining
    )

@app.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    user_id = session.get('user_id')
    
    current_attempt = QuizAttempt.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id,
        end_time=None
    ).first()
    
    if not current_attempt:
        flash('No active quiz attempt found!', 'danger')
        return redirect(url_for('dashboard'))
    
    total_score = 0
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    
    for question in questions:
        selected_option_id = request.form.get(f'question_{question.id}')
        
        if selected_option_id:
            response = UserResponse(
                quiz_attempt_id=current_attempt.id,
                question_id=question.id,
                selected_option_id=selected_option_id
            )
            db.session.add(response)
            
            selected_option = Option.query.get(selected_option_id)
            if selected_option and selected_option.is_correct:
                total_score += question.points
    
    current_attempt.end_time = datetime.now(timezone.utc)
    
    score = Score(
        user_id=user_id,
        quiz_id=quiz_id,
        score=total_score,
        date=datetime.now(timezone.utc)
    )
    
    try:
        db.session.add(score)
        db.session.commit()
        flash(f'Quiz submitted! Your score: {total_score}', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error submitting quiz!', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/answer/<int:quiz_id>', methods=['POST'])
@login_required
def save_answer(quiz_id):
    user_id = session.get('user_id')
    question_id = request.form.get('question_id')
    selected_option_id = request.form.get('selected_option')
    
    if not all([question_id, selected_option_id]):
        return {'status': 'error', 'message': 'Missing data'}
    
    current_attempt = QuizAttempt.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id,
        end_time=None
    ).first()
    
    if not current_attempt:
        return {'status': 'error', 'message': 'No active quiz attempt'}
    
    existing_response = UserResponse.query.filter_by(
        quiz_attempt_id=current_attempt.id,
        question_id=question_id
    ).first()
    
    try:
        if existing_response:
            existing_response.selected_option_id = selected_option_id
        else:
            new_response = UserResponse(
                quiz_attempt_id=current_attempt.id,
                question_id=question_id,
                selected_option_id=selected_option_id
            )
            db.session.add(new_response)
        
        db.session.commit()
        return {'status': 'success'}
    except Exception as e:
        db.session.rollback()
        return {'status': 'error', 'message': str(e)}

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))
