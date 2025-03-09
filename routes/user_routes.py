from flask import render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func
from models import *
from utils import *
from app import app
from datetime import datetime, timezone

@app.route('/')
def to_home():
    return redirect('home')

@app.route('/home')
def home():
    return render_template('user/home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        flash('You are already logged in!', 'danger')
        return redirect(url_for('dashboard'))
    
    if 'admin_id' in session:
        flash('You are already logged in as admin!', 'danger')
        return redirect(url_for('admin'))

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
    
    return render_template('user/login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        flash('You are already logged in!', 'danger')
        return redirect(url_for('dashboard'))
    
    if 'admin_id' in session:
        flash('You are already logged in as admin!', 'danger')
        return redirect(url_for('admin'))
    
    if request.method == 'POST':
        password = request.form.get('password')
        fullName = request.form.get('fullName')
        email = request.form.get('email')
        qualification = request.form.get('qualification')
        dob = request.form.get('dob')

        if not all([password, fullName, email]):
            flash('Please fill all required fields!', 'danger')
            return redirect(url_for('signup'))

        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('signup'))

        try:
            # Convert dob string to timezone-aware datetime if provided
            dob_datetime = None
            if dob:
                dob_datetime = datetime.strptime(dob, '%Y-%m-%d')
                dob_datetime = dob_datetime.replace(tzinfo=timezone.utc)
        except ValueError:
            flash('Invalid date format!', 'danger')
            return redirect(url_for('signup'))

        hashed_password = generate_password_hash(password)
        
        new_user = User(
            password=hashed_password,
            fullName=fullName,
            email=email,
            qualification=qualification,
            dob=dob_datetime,
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

    return render_template('user/signup.html', datetime=datetime, timezone=timezone)

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
            
            # Ensure all quiz dates are timezone-aware
            for quiz in chapter.quizzes:
                if quiz.start_date and quiz.start_date.tzinfo is None:
                    db.session.query(Quiz).filter_by(id=quiz.id).update({
                        'start_date': quiz.start_date.replace(tzinfo=timezone.utc)
                    })
                if quiz.end_date and quiz.end_date.tzinfo is None:
                    db.session.query(Quiz).filter_by(id=quiz.id).update({
                        'end_date': quiz.end_date.replace(tzinfo=timezone.utc)
                    })
            
            # Commit changes if any dates were updated
            if any(quiz.start_date.tzinfo is None for quiz in chapter.quizzes if quiz.start_date) or \
               any(quiz.end_date.tzinfo is None for quiz in chapter.quizzes if quiz.end_date):
                db.session.commit()
                # Refresh quizzes after committing changes
                chapter.quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
    
    stats = {
        'total_quizzes': QuizAttempt.query.filter_by(user_id=user_id).count(),
        'highest_score': db.session.query(db.func.max(Score.total_scored)).filter_by(user_id=user_id).scalar(),
        'average_score': db.session.query(db.func.avg(Score.total_scored)).filter_by(user_id=user_id).scalar()
    }
    
    # Pass datetime and timezone modules to the template
    now = datetime.now(timezone.utc)
    return render_template('user/dash.html', 
                          subjects=subjects, 
                          user=user, 
                          stats=stats, 
                          datetime=datetime, 
                          timezone=timezone,
                          now=now)

@app.route('/view-quiz/<int:quiz_id>')
@login_required
def view_quiz(quiz_id):
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    now = datetime.now(timezone.utc)
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Handle timezone for dates
    if quiz.start_date and quiz.start_date.tzinfo is None:
        db.session.query(Quiz).filter_by(id=quiz_id).update({
            'start_date': quiz.start_date.replace(tzinfo=timezone.utc)
        })
    if quiz.end_date and quiz.end_date.tzinfo is None:
        db.session.query(Quiz).filter_by(id=quiz_id).update({
            'end_date': quiz.end_date.replace(tzinfo=timezone.utc)
        })
    
    # Commit any timezone updates and refresh the quiz object
    if quiz.start_date.tzinfo is None or (quiz.end_date and quiz.end_date.tzinfo is None):
        db.session.commit()
        quiz = Quiz.query.get(quiz_id)  # Refresh the quiz object
    
    # Get quiz chapter and subject for breadcrumb navigation
    chapter = Chapter.query.get(quiz.chapter_id)
    subject = Subject.query.get(chapter.subject_id)
    
    # Get the number of questions in the quiz
    question_count = Question.query.filter_by(quiz_id=quiz_id).count()
    
    # Check if user has any attempts for this quiz
    attempts = QuizAttempt.query.filter_by(user_id=user_id, quiz_id=quiz_id).count()
    
    # Get user's best score for this quiz if they've taken it
    best_score = db.session.query(db.func.max(Score.total_scored))\
                .filter_by(user_id=user_id, quiz_id=quiz_id).scalar()
    
    # Convert dates to UTC for status comparison
    start_date_aware = quiz.start_date.astimezone(timezone.utc)
    end_date_aware = quiz.end_date.astimezone(timezone.utc) if quiz.end_date else None
    
    quiz_status = "upcoming"
    if now >= start_date_aware:
        if end_date_aware and now > end_date_aware:
            quiz_status = "expired"
        else:
            quiz_status = "available"
    
    return render_template('user/view_quiz.html', 
                          quiz=quiz,
                          chapter=chapter,
                          subject=subject,
                          question_count=question_count,
                          attempts=attempts,
                          best_score=best_score,
                          quiz_status=quiz_status,
                          user=user,
                          datetime=datetime,
                          timezone=timezone,
                          now=now)

@app.route('/start-quiz/<int:quiz_id>', methods=['POST'])
@login_required
def start_quiz(quiz_id):
    user_id = session.get('user_id')
    quiz = Quiz.query.get_or_404(quiz_id)
    now = datetime.now(timezone.utc)

    # Check if quiz is active and available
    if not quiz.is_active:
        flash('This quiz is not currently available.', 'error')
        return redirect(url_for('view_quiz', quiz_id=quiz_id))

    # Ensure dates are timezone-aware
    if quiz.start_date.tzinfo is None:
        db.session.query(Quiz).filter_by(id=quiz_id).update({
            'start_date': quiz.start_date.replace(tzinfo=timezone.utc)
        })
    
    if quiz.end_date and quiz.end_date.tzinfo is None:
        db.session.query(Quiz).filter_by(id=quiz_id).update({
            'end_date': quiz.end_date.replace(tzinfo=timezone.utc)
        })
    
    if any([quiz.start_date.tzinfo is None, quiz.end_date and quiz.end_date.tzinfo is None]):
        db.session.commit()
        quiz = Quiz.query.get(quiz_id)  # Refresh the quiz object

    # Now both dates should be timezone-aware for comparison
    if quiz.start_date > now:
        flash('This quiz has not started yet.', 'error')
        return redirect(url_for('view_quiz', quiz_id=quiz_id))
    
    if quiz.end_date and quiz.end_date < now:
        flash('This quiz has expired.', 'error')
        return redirect(url_for('view_quiz', quiz_id=quiz_id))
    
    # Check attempts
    attempts = QuizAttempt.query.filter_by(user_id=user_id, quiz_id=quiz_id).count()
    if attempts >= quiz.max_attempts:
        flash('You have used all your attempts for this quiz.', 'error')
        return redirect(url_for('view_quiz', quiz_id=quiz_id))
    
    # Check if user has any ongoing attempt
    ongoing_attempt = QuizAttempt.query.filter_by(
        user_id=user_id, 
        quiz_id=quiz_id, 
        status='in_progress'
    ).first()
    
    if ongoing_attempt:
        if ongoing_attempt.start_time.tzinfo is None:
            ongoing_attempt.start_time = ongoing_attempt.start_time.replace(tzinfo=timezone.utc)
            db.session.commit()
            
        start_time_aware = ongoing_attempt.start_time.astimezone(timezone.utc)
        
        elapsed_time = (now - start_time_aware).total_seconds() / 60
        if elapsed_time < quiz.time_duration:
            questions = Question.query.filter_by(quiz_id=quiz_id).order_by(func.random()).all()
            time_remaining = int((quiz.time_duration * 60) - (elapsed_time * 60))
            return render_template('user/quiz.html', 
                                quiz=quiz, 
                                questions=questions,
                                attempt_number=ongoing_attempt.attempt_number,
                                time_remaining=time_remaining)
        else:
            # Auto-submit expired attempt
            ongoing_attempt.status = 'expired'
            ongoing_attempt.end_time = now
            db.session.commit()
    
    # Create new attempt
    attempt_number = attempts + 1
    new_attempt = QuizAttempt(
        user_id=user_id,
        quiz_id=quiz_id,
        attempt_number=attempt_number,
        start_time=now,
        status='in_progress'
    )
    db.session.add(new_attempt)
    db.session.commit()
    
    # Get randomized questions
    questions = Question.query.filter_by(quiz_id=quiz_id).order_by(func.random()).all()
    
    # Start with full time duration for new attempt
    time_remaining = quiz.time_duration * 60  # Convert to seconds
    
    return render_template('user/quiz.html', 
                         quiz=quiz, 
                         questions=questions,
                         attempt_number=attempt_number,
                         time_remaining=time_remaining)

@app.route('/submit-quiz/<int:quiz_id>', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    user_id = session.get('user_id')
    now = datetime.now(timezone.utc)
    
    quiz = Quiz.query.get_or_404(quiz_id)
    
    # Get the ongoing attempt
    attempt = QuizAttempt.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id,
        status='in_progress'
    ).first()
    
    if not attempt:
        flash('No active quiz attempt found.', 'error')
        return redirect(url_for('view_quiz', quiz_id=quiz_id))
    
    # Ensure attempt start_time is timezone-aware and in UTC
    if attempt.start_time.tzinfo is None:
        attempt.start_time = attempt.start_time.replace(tzinfo=timezone.utc)
    
    start_time_aware = attempt.start_time.astimezone(timezone.utc)
    
    # Check if the quiz time has expired using timezone-aware comparison
    elapsed_time = (now - start_time_aware).total_seconds() / 60
    if elapsed_time > quiz.time_duration:
        attempt.status = 'expired'
        attempt.end_time = now
        db.session.commit()
        flash('Quiz time has expired!', 'error')
        return redirect(url_for('view_quiz', quiz_id=quiz_id))
    
    total_points = 0
    earned_points = 0
    
    # Process responses
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    for question in questions:
        selected_option_id = request.form.get(f'question_{question.id}')
        if not selected_option_id:
            continue
        
        selected_option = Option.query.get(selected_option_id)
        total_points += question.points
        
        user_response = UserResponse(
            quiz_attempt_id=attempt.id,
            question_id=question.id,
            selected_option_id=selected_option_id,
            is_correct=selected_option.is_correct,
            created_at=now  # Ensure created_at is timezone-aware
        )
        
        if selected_option.is_correct:
            earned_points += question.points
        
        db.session.add(user_response)
    
    # Calculate score percentage
    score_percentage = (earned_points / total_points * 100) if total_points > 0 else 0
    passed = score_percentage >= quiz.passing_score
    
    # Update attempt status with timezone-aware end time
    attempt.status = 'completed'
    attempt.end_time = now
    
    # Create score record with timezone-aware timestamps
    score = Score(
        total_scored=score_percentage,
        is_completed=True,
        passed=passed,
        start_time=attempt.start_time,  # Already made timezone-aware above
        end_time=now,
        attempt_number=attempt.attempt_number,
        user_id=user_id,
        quiz_id=quiz_id,
        created_at=now
    )
    
    db.session.add(score)
    db.session.commit()
    
    flash(f'Quiz submitted successfully! Your score: {score_percentage:.1f}%', 'success')
    return redirect(url_for('quiz_review', quiz_id=quiz_id, score_id=score.id))

@app.route('/quiz-review/<int:quiz_id>/<int:score_id>')
@login_required
def quiz_review(quiz_id, score_id):
    user_id = session.get('user_id')
    quiz = Quiz.query.get_or_404(quiz_id)
    score = Score.query.get_or_404(score_id)
    
    # Ensure the user can only view their own quiz results
    if score.user_id != user_id:
        flash('You are not authorized to view these results.', 'error')
        return redirect(url_for('dashboard'))
    
    # Get the quiz attempt associated with this score
    attempt = QuizAttempt.query.filter_by(
        user_id=user_id,
        quiz_id=quiz_id,
        attempt_number=score.attempt_number
    ).first_or_404()
    
    # Get all user responses for this attempt with related questions and options
    user_responses = UserResponse.query\
        .filter_by(quiz_attempt_id=attempt.id)\
        .join(Question)\
        .all()
    
    # Load all options for each question to show correct answers
    for response in user_responses:
        response.question.options = Option.query.filter_by(question_id=response.question_id).all()
    
    return render_template('user/quiz_review.html',
                         quiz=quiz,
                         score=score,
                         user_responses=user_responses)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))
