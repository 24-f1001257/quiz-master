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
    return render_template('user/user_home.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('404.html', error_message="Internal Server Error"), 500

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
    
    return render_template('user/user_login.html')

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
            dob_datetime = None
            if (dob):
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

    return render_template('user/user_signup.html', datetime=datetime, timezone=timezone)

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    now = datetime.now(timezone.utc)
    
    subjects = Subject.query.all()
    subject_quiz_counts = {}  # Dictionary to store active quiz counts by subject
    
    for subject in subjects:
        subject.chapters = Chapter.query.filter_by(subject_id=subject.id).all()
        active_quiz_count = 0
        
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
                
                # Count active quizzes for this subject
                if quiz.is_active:
                    active_quiz_count += 1
            
            # Commit changes if any dates were updated
            if any(quiz.start_date.tzinfo is None for quiz in chapter.quizzes if quiz.start_date) or \
               any(quiz.end_date.tzinfo is None for quiz in chapter.quizzes if quiz.end_date):
                db.session.commit()
                # Refresh quizzes after committing changes
                chapter.quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
        
        # Store the active quiz count for this subject
        subject_quiz_counts[subject.id] = active_quiz_count
    
    # Get user quiz statistics
    highest_score = db.session.query(db.func.max(Score.total_scored)).filter_by(user_id=user_id).scalar()
    average_score = db.session.query(db.func.avg(Score.total_scored)).filter_by(user_id=user_id).scalar()
    total_quizzes = QuizAttempt.query.filter_by(user_id=user_id).count()
    
    # Get recent quiz attempts for the charts
    recent_scores = Score.query.filter_by(user_id=user_id)\
        .order_by(Score.created_at.desc())\
        .limit(5)\
        .all()
    
    # Format the data for the chart
    recent_attempts = []
    for score in recent_scores:
        quiz = Quiz.query.get(score.quiz_id)
        if quiz:
            recent_attempts.append({
                'quiz_name': quiz.name,
                'score': float(score.total_scored),
                'passed': score.passed,
                'attempt_number': score.attempt_number,
                'date': score.created_at.strftime('%Y-%m-%d')
            })
    
    stats = {
        'total_quizzes': total_quizzes,
        'highest_score': highest_score,
        'average_score': average_score,
        'recent_attempts': recent_attempts
    }
    
    # Convert to JSON-safe data for the template
    import json
    stats['recent_attempts'] = json.dumps(recent_attempts)
    
    # Pass datetime and timezone modules to the template
    return render_template('user/user_dashboard.html', 
                          subjects=subjects, 
                          user=user, 
                          stats=stats, 
                          subject_quiz_counts=subject_quiz_counts,
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
    
    return render_template('user/user_quiz_view.html', 
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
            return render_template('user/user_quiz_take.html', 
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
    
    return render_template('user/user_quiz_take.html', 
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
    
    return render_template('user/user_quiz_review.html',
                         quiz=quiz,
                         score=score,
                         user_responses=user_responses)


@app.route('/search')
@login_required
def user_search():
    query = request.args.get('q', '')
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not query:
        return render_template('user/user_search.html', 
                              results=None, 
                              query='',
                              user=user)
    
    # Use a percentage wildcard for LIKE queries
    search_term = f"%{query}%"
    
    results = {
        'subjects': [],
        'chapters': [],
        'quizzes': []
    }
    
    # Search for subjects
    subjects = Subject.query.filter(
        db.or_(
            Subject.name.ilike(search_term),
            Subject.description.ilike(search_term)
        )
    ).all()
    results['subjects'] = subjects
    
    # Search for chapters
    chapters = Chapter.query.filter(
        db.or_(
            Chapter.name.ilike(search_term),
            Chapter.description.ilike(search_term)
        )
    ).join(Subject).all()
    
    # Load the subject for each chapter
    for chapter in chapters:
        chapter.subject = Subject.query.get(chapter.subject_id)
    
    results['chapters'] = chapters
    
    # Search for quizzes, but only active ones
    quizzes = Quiz.query.filter(
        db.and_(
            Quiz.is_active == True,
            db.or_(
                Quiz.name.ilike(search_term),
                Quiz.description.ilike(search_term)
            )
        )
    ).all()
    
    # Load the chapter and subject for each quiz
    for quiz in quizzes:
        quiz.chapter = Chapter.query.get(quiz.chapter_id)
        if quiz.chapter:
            quiz.chapter.subject = Subject.query.get(quiz.chapter.subject_id)
    
    results['quizzes'] = quizzes
    
    return render_template('user/user_search.html', 
                          results=results, 
                          query=query,
                          user=user)

@app.route('/profile')
@login_required
def user_profile():
    user_id = session.get('user_id')
    user = User.query.get_or_404(user_id)
    
    # Get additional user statistics for profile
    total_quizzes_completed = db.session.query(db.func.count(Score.id)).filter_by(user_id=user_id, is_completed=True).scalar() or 0
    total_quizzes_passed = db.session.query(db.func.count(Score.id)).filter_by(user_id=user_id, passed=True).scalar() or 0
    passing_rate = (total_quizzes_passed / total_quizzes_completed * 100) if total_quizzes_completed > 0 else 0
    
    # Get recent activity (last 5 quiz attempts)
    recent_activity = QuizAttempt.query.filter_by(user_id=user_id).order_by(QuizAttempt.start_time.desc()).limit(5).all()
    
    # Enrich recent activity with quiz details
    for activity in recent_activity:
        activity.quiz = Quiz.query.get(activity.quiz_id)
        if activity.status == 'completed':
            activity.score = Score.query.filter_by(
                user_id=user_id, 
                quiz_id=activity.quiz_id, 
                attempt_number=activity.attempt_number
            ).first()
    
    return render_template('user/user_profile.html', 
                          user=user, 
                          total_quizzes_completed=total_quizzes_completed,
                          total_quizzes_passed=total_quizzes_passed,
                          passing_rate=passing_rate,
                          recent_activity=recent_activity,
                          datetime=datetime,
                          timezone=timezone)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user_id = session.get('user_id')
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        fullName = request.form.get('fullName')
        email = request.form.get('email')
        qualification = request.form.get('qualification')
        dob = request.form.get('dob')
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate required fields
        if not fullName or not email:
            flash('Name and email are required fields.', 'danger')
            return redirect(url_for('edit_profile'))
        
        # Check if email is being changed and if it already exists for another user
        if email != user.email and User.query.filter_by(email=email).first():
            flash('Email already registered to another account.', 'danger')
            return redirect(url_for('edit_profile'))
        
        # Process date of birth if provided
        dob_datetime = user.dob
        if dob:
            try:
                dob_datetime = datetime.strptime(dob, '%Y-%m-%d')
                dob_datetime = dob_datetime.replace(tzinfo=timezone.utc)
            except ValueError:
                flash('Invalid date format.', 'danger')
                return redirect(url_for('edit_profile'))
        
        # Update user details
        user.fullName = fullName
        user.email = email
        user.qualification = qualification
        user.dob = dob_datetime
        
        # Handle password change if requested
        if new_password:
            # Verify current password before allowing change
            if not check_password_hash(user.password, current_password):
                flash('Current password is incorrect.', 'danger')
                return redirect(url_for('edit_profile'))
            
            # Validate new password
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return redirect(url_for('edit_profile'))
            
            # Update password
            user.password = generate_password_hash(new_password)
            flash('Password updated successfully.', 'success')
        
        try:
            db.session.commit()
            flash('Profile updated successfully.', 'success')
            return redirect(url_for('user_profile'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating profile.', 'danger')
            return redirect(url_for('edit_profile'))
    
    # Format date for the HTML date input
    formatted_dob = user.dob.strftime('%Y-%m-%d') if user.dob else None
    
    return render_template('user/user_edit_profile.html', 
                          user=user,
                          formatted_dob=formatted_dob)

@app.route('/summary')
@login_required
def user_summary():
    user_id = session.get('user_id')
    user = User.query.get_or_404(user_id)
    
    # Get user quiz statistics
    highest_score = db.session.query(db.func.max(Score.total_scored)).filter_by(user_id=user_id).scalar()
    average_score = db.session.query(db.func.avg(Score.total_scored)).filter_by(user_id=user_id).scalar()
    total_quizzes = QuizAttempt.query.filter_by(user_id=user_id).count()
    total_quizzes_completed = db.session.query(db.func.count(Score.id)).filter_by(user_id=user_id, is_completed=True).scalar() or 0
    total_quizzes_passed = db.session.query(db.func.count(Score.id)).filter_by(user_id=user_id, passed=True).scalar() or 0
    passing_rate = (total_quizzes_passed / total_quizzes_completed * 100) if total_quizzes_completed > 0 else 0
    
    # Get quiz attempts by subject
    subject_stats = db.session.query(
        Subject.name, 
        db.func.count(Score.id).label('attempts'),
        db.func.avg(Score.total_scored).label('avg_score')
    ).join(
        Chapter, Subject.id == Chapter.subject_id
    ).join(
        Quiz, Chapter.id == Quiz.chapter_id
    ).join(
        Score, Quiz.id == Score.quiz_id
    ).filter(
        Score.user_id == user_id
    ).group_by(
        Subject.name
    ).all()
    
    # Format subject stats for chart
    subject_names = [s.name for s in subject_stats]
    subject_attempts = [s.attempts for s in subject_stats]
    subject_avg_scores = [float(s.avg_score) if s.avg_score else 0 for s in subject_stats]
    
    # Get recent quiz attempts for the charts
    recent_scores = Score.query.filter_by(user_id=user_id)\
        .order_by(Score.created_at.desc())\
        .limit(10)\
        .all()
    
    # Format the data for the chart
    recent_attempts = []
    for score in recent_scores:
        quiz = Quiz.query.get(score.quiz_id)
        if quiz:
            recent_attempts.append({
                'quiz_name': quiz.name,
                'score': float(score.total_scored),
                'passed': score.passed,
                'attempt_number': score.attempt_number,
                'date': score.created_at.strftime('%Y-%m-%d')
            })
    
    # Get performance over time (monthly)
    monthly_performance = db.session.query(
        db.func.strftime('%Y-%m', Score.created_at).label('month'),
        db.func.avg(Score.total_scored).label('avg_score'),
        db.func.count(Score.id).label('count')
    ).filter(
        Score.user_id == user_id
    ).group_by(
        'month'
    ).order_by(
        'month'
    ).all()
    
    # Format monthly performance data
    months = [p.month for p in monthly_performance]
    monthly_avg_scores = [float(p.avg_score) if p.avg_score else 0 for p in monthly_performance]
    monthly_counts = [p.count for p in monthly_performance]
    
    stats = {
        'total_quizzes': total_quizzes,
        'highest_score': highest_score,
        'average_score': average_score,
        'total_completed': total_quizzes_completed,
        'total_passed': total_quizzes_passed,
        'passing_rate': passing_rate,
        'recent_attempts': recent_attempts,
        'subject_names': subject_names,
        'subject_attempts': subject_attempts,
        'subject_avg_scores': subject_avg_scores,
        'months': months,
        'monthly_avg_scores': monthly_avg_scores,
        'monthly_counts': monthly_counts
    }
    
    # Convert to JSON-safe data for the template
    import json
    stats['recent_attempts_json'] = json.dumps(recent_attempts)
    stats['subject_names_json'] = json.dumps(subject_names)
    stats['subject_attempts_json'] = json.dumps(subject_attempts)
    stats['subject_avg_scores_json'] = json.dumps(subject_avg_scores)
    stats['months_json'] = json.dumps(months)
    stats['monthly_avg_scores_json'] = json.dumps(monthly_avg_scores)
    stats['monthly_counts_json'] = json.dumps(monthly_counts)
    
    return render_template('user/user_summary.html', 
                          user=user, 
                          stats=stats)

@app.route('/quizzes')
@login_required
def user_quizzes():
    # Get filter parameters
    subject_id = request.args.get('subject_id')
    chapter_id = request.args.get('chapter_id')
    date_filter = request.args.get('date')
    duration_filter = request.args.get('duration')
    sort_by = request.args.get('sort_by', 'date_desc')
    
    now = datetime.now(timezone.utc)
    
    query = Quiz.query.filter(Quiz.is_active == True)
    
    # Apply filters - explicitly convert to integers and handle potential errors
    if subject_id and subject_id != '':
        try:
            subject_id = int(subject_id)
            chapters = Chapter.query.filter_by(subject_id=subject_id).all()
            chapter_ids = [chapter.id for chapter in chapters]
            if chapter_ids:  # Only apply filter if there are chapters
                query = query.filter(Quiz.chapter_id.in_(chapter_ids))
                # Get the subject for breadcrumb navigation
                selected_subject = Subject.query.get(subject_id)
                app.logger.info(f"Filtering by subject_id {subject_id}, chapter_ids: {chapter_ids}")
            else:
                # No chapters found for this subject, so there won't be any quizzes
                selected_subject = Subject.query.get(subject_id)
                quizzes = []
                return render_template('user/user_quiz_list.html', 
                                    quizzes=[],
                                    subjects=Subject.query.all(),
                                    chapters=[],
                                    selected_subject=selected_subject,
                                    selected_chapter=None,
                                    datetime=datetime,
                                    timezone=timezone,
                                    now=now)
        except (ValueError, TypeError):
            app.logger.warning(f"Invalid subject_id: {subject_id}")
            selected_subject = None
    else:
        selected_subject = None
    
    # Direct filter by chapter if specified
    if chapter_id and chapter_id != '':
        try:
            chapter_id = int(chapter_id)
            chapter = Chapter.query.get(chapter_id)
            if chapter:
                query = query.filter(Quiz.chapter_id == chapter_id)
                selected_chapter = chapter
                app.logger.info(f"Filtering by chapter_id {chapter_id}")
                
                # Check if there are any quizzes for this chapter
                if Quiz.query.filter_by(chapter_id=chapter_id).count() == 0:
                    # Early return if no quizzes for this chapter
                    selected_subject = Subject.query.get(chapter.subject_id) if chapter else None
                    subjects = Subject.query.all()
                    chapters = Chapter.query.filter_by(subject_id=selected_subject.id).all() if selected_subject else []
                    
                    return render_template('user/user_quiz_list.html', 
                                        quizzes=[],
                                        subjects=subjects,
                                        chapters=chapters,
                                        selected_subject=selected_subject,
                                        selected_chapter=selected_chapter,
                                        datetime=datetime,
                                        timezone=timezone,
                                        now=now)
            else:
                selected_chapter = None
        except (ValueError, TypeError):
            app.logger.warning(f"Invalid chapter_id: {chapter_id}")
            selected_chapter = None
    else:
        selected_chapter = None
    
    if date_filter and date_filter != '':
        try:
            # Convert the filter date to a timezone-aware datetime at the start of the day
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
            filter_date = filter_date.replace(tzinfo=timezone.utc)
            filter_date_end = filter_date.replace(hour=23, minute=59, second=59)
            
            # Filter quizzes that start on the selected date
            query = query.filter(Quiz.start_date >= filter_date, Quiz.start_date <= filter_date_end)
            app.logger.info(f"Filtering by date: {date_filter}")
        except ValueError:
            flash('Invalid date format', 'danger')
            app.logger.warning(f"Invalid date format: {date_filter}")
    
    if duration_filter and duration_filter != '':
        if duration_filter == '0-15':
            query = query.filter(Quiz.time_duration <= 15)
            app.logger.info("Filtering: duration <= 15 minutes")
        elif duration_filter == '15-30':
            query = query.filter(Quiz.time_duration > 15, Quiz.time_duration <= 30)
            app.logger.info("Filtering: 15 < duration <= 30 minutes")
        elif duration_filter == '30+':
            query = query.filter(Quiz.time_duration > 30)
            app.logger.info("Filtering: duration > 30 minutes")
    
    # Apply sorting
    if sort_by == 'date_desc':
        query = query.order_by(Quiz.start_date.desc())
    elif sort_by == 'date_asc':
        query = query.order_by(Quiz.start_date.asc())
    elif sort_by == 'name_asc':
        query = query.order_by(Quiz.name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Quiz.name.desc())
    elif sort_by == 'duration_asc':
        query = query.order_by(Quiz.time_duration.asc())
    elif sort_by == 'duration_desc':
        query = query.order_by(Quiz.time_duration.desc())
    
    quizzes = query.all()
    app.logger.info(f"Query returned {len(quizzes)} quizzes")
    
    # Ensure all quiz dates are timezone-aware
    for quiz in quizzes:
        if quiz.start_date and quiz.start_date.tzinfo is None:
            db.session.query(Quiz).filter_by(id=quiz.id).update({
                'start_date': quiz.start_date.replace(tzinfo=timezone.utc)
            })
        if quiz.end_date and quiz.end_date.tzinfo is None:
            db.session.query(Quiz).filter_by(id=quiz.id).update({
                'end_date': quiz.end_date.replace(tzinfo=timezone.utc)
            })
    
    # Commit any timezone updates and refresh quizzes
    if quizzes and (any(quiz.start_date.tzinfo is None for quiz in quizzes if quiz.start_date) or 
       any(quiz.end_date.tzinfo is None for quiz in quizzes if quiz.end_date)):
        db.session.commit()
        quizzes = query.all()  # Refresh the quiz objects
    
    # Get all subjects for the filter dropdown
    subjects = Subject.query.all()
    
    # If filtering by subject, get chapters of that subject for the chapter filter dropdown
    if selected_subject:
        chapters = Chapter.query.filter_by(subject_id=selected_subject.id).all()
    else:
        chapters = []
    
    # Get user's attempts for these quizzes
    user_id = session.get('user_id')
    user_attempts = {}
    
    for quiz in quizzes:
        attempts = QuizAttempt.query.filter_by(user_id=user_id, quiz_id=quiz.id).count()
        best_score = db.session.query(db.func.max(Score.total_scored))\
                    .filter_by(user_id=user_id, quiz_id=quiz.id).scalar()
                    
        user_attempts[quiz.id] = {
            'count': attempts,
            'best_score': best_score
        }
    
    return render_template('user/user_quiz_list.html', 
                         quizzes=quizzes,
                         subjects=subjects,
                         chapters=chapters,
                         selected_subject=selected_subject,
                         selected_chapter=selected_chapter,
                         datetime=datetime,
                         timezone=timezone,
                         user_attempts=user_attempts,
                         now=now)
