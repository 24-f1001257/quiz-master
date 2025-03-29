from flask import request, redirect, flash, render_template, url_for, session, jsonify
from werkzeug.security import generate_password_hash
from models import *
from utils import *
from app import app
from datetime import date, datetime, timezone
from sqlalchemy import func

@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    try:
        subjects = Subject.query.all()
        for subject in subjects:
            subject.chapters = Chapter.query.filter_by(subject_id=subject.id).all()
        
        recent_subjects = Subject.query.order_by(Subject.created_at.desc()).limit(5).all()
        for subject in recent_subjects:
            subject.chapters = Chapter.query.filter_by(subject_id=subject.id).all()
        
        all_quizzes = Quiz.query.all()
        total_quizzes = len(all_quizzes)
        
        recent_quizzes_query = Quiz.query.join(Chapter).join(Subject)
        recent_quizzes = recent_quizzes_query.order_by(Quiz.created_at.desc()).limit(5).all()
        
        users = User.query.filter(User.email != 'admin@admin.com').all()
        
        now = datetime.now(timezone.utc)
        
        for quiz in all_quizzes:
            if quiz.start_date and quiz.start_date.tzinfo is None:
                quiz.start_date = quiz.start_date.replace(tzinfo=timezone.utc)
            if quiz.end_date and quiz.end_date.tzinfo is None:
                quiz.end_date = quiz.end_date.replace(tzinfo=timezone.utc)
        
        active_quizzes = sum(1 for q in all_quizzes if q.is_active and 
                            q.start_date <= now and 
                            (q.end_date is None or q.end_date >= now))
        
        upcoming_quizzes = sum(1 for q in all_quizzes if q.start_date > now)
        
        expired_quizzes = sum(1 for q in all_quizzes if q.end_date and q.end_date < now)
        
        if total_quizzes > 0:
            avg_quiz_duration = sum(q.time_duration for q in all_quizzes) / total_quizzes
        else:
            avg_quiz_duration = 0
        
        total_attempts = QuizAttempt.query.count()
        completed_attempts = QuizAttempt.query.filter_by(status='completed').count()
        
        if completed_attempts > 0:
            passed_scores = Score.query.filter_by(passed=True).count()
            pass_rate = (passed_scores / completed_attempts) * 100
        else:
            pass_rate = 0
        
        avg_score_result = db.session.query(func.avg(Score.total_scored)).scalar()
        avg_score = avg_score_result if avg_score_result else 0
        
        return render_template("admin/admin_dashboard.html", 
                               subjects=subjects,
                               recent_subjects=recent_subjects,
                               total_quizzes=total_quizzes,
                               recent_quizzes=recent_quizzes,
                               users=users,
                               active_quizzes_number=active_quizzes,
                               upcoming_quizzes=upcoming_quizzes,
                               expired_quizzes=expired_quizzes,
                               avg_quiz_duration=avg_quiz_duration,
                               total_attempts=total_attempts,
                               completed_attempts=completed_attempts,
                               pass_rate=pass_rate,
                               avg_score=avg_score)
    except Exception as e:
        app.logger.error(f"Admin dashboard error: {str(e)}")
        flash('Error loading admin dashboard', 'danger')
        return redirect(url_for('login'))

@app.route('/admin/logout')
@admin_required
def adminLogout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/admin/subject/add', methods=['POST'])
@admin_required
def add_subject():
    subName = request.form.get('subject_name')
    subDescription = request.form.get('subject_description', '')

    if not subName:
        flash('Subject name is mandatory!', 'danger')
        return redirect(url_for('admin'))

    existing_subject = Subject.query.filter(Subject.name.ilike(subName)).first()
    if existing_subject:
        flash('Subject with this name already exists!', 'danger')
        return redirect(url_for('admin'))

    newSubject = Subject(
        name=subName.strip(),
        description=subDescription.strip(),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    db.session.add(newSubject)
    db.session.commit()
    
    flash(f'{subName} added successfully!', 'success')
    return redirect(url_for('admin_subjects'))

@app.route('/admin/subject/<int:subject_id>/edit', methods=['POST'])
@admin_required
def edit_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    subName = request.form.get('subject_name')
    subDescription = request.form.get('subject_description', '')

    if not subName:
        flash('Subject name is required!', 'danger')
        return redirect(url_for('admin'))
    
    existing_subject = Subject.query.filter(
        Subject.name.ilike(subName),
        Subject.id != subject_id
    ).first()
    
    if existing_subject:
        flash('Another subject with this name already exists!', 'danger')
        return redirect(url_for('admin'))
    
    try:
        subject.name = subName.strip()
        subject.description = subDescription.strip()
        subject.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f'{subName} updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating subject: {str(e)}', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/subject/<int:subject_id>/delete', methods=['POST'])
@admin_required
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    try:
        chapters = Chapter.query.filter_by(subject_id=subject_id).all()
        
        for chapter in chapters:
            quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
            
            for quiz in quizzes:
                for question in quiz.questions:
                    Option.query.filter_by(question_id=question.id).delete()
                
                Question.query.filter_by(quiz_id=quiz.id).delete()
                
                for attempt in quiz.attempts:
                    UserResponse.query.filter_by(quiz_attempt_id=attempt.id).delete()
                
                QuizAttempt.query.filter_by(quiz_id=quiz.id).delete()
                Score.query.filter_by(quiz_id=quiz.id).delete()
                
                db.session.delete(quiz)
            
        Chapter.query.filter_by(subject_id=subject_id).delete()
        db.session.delete(subject)
        db.session.commit()
        
        flash(f'{subject.name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting subject: {str(e)}', 'danger')
    
    return redirect(url_for('admin_subjects'))

@app.route('/admin/chapter/add', methods=['POST'])
@admin_required
def add_chapter():
    chapName = request.form.get('chapter_name')
    chapDescription = request.form.get('chapter_description', '')
    subject_id = request.form.get('subject_id')

    if not subject_id:
        flash('Invalid subject selected!', 'danger')
        return redirect(url_for('admin_subjects'))
    
    try:
        subject_id = int(subject_id)
    except ValueError:
        flash('Invalid subject ID!', 'danger')
        return redirect(url_for('admin_subjects'))

    subject = Subject.query.get(subject_id)
    if not subject:
        flash('Subject not found!', 'danger')
        return redirect(url_for('admin_subjects'))

    if not chapName:
        flash('Chapter name is required!', 'danger')
        return redirect(url_for('admin_subjects'))
    
    existingChapter = Chapter.query.filter(
        Chapter.name.ilike(chapName),
        Chapter.subject_id == subject_id
    ).first()
    
    if existingChapter:
        flash(f'A chapter with name : {chapName} already exists in this subject!', 'danger')
        return redirect(url_for('admin_subjects'))
    
    newChapter = Chapter(
        name=chapName.strip(),
        description=chapDescription.strip(),
        subject_id=subject_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    db.session.add(newChapter)
    db.session.commit()

    flash(f'{chapName} added successfully to {subject.name}!', 'success')
    return redirect(url_for('subject_quizzes', subject_id=subject_id))

@app.route('/admin/chapter/<int:chapter_id>/delete', methods=['POST'])
@admin_required
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    subject_id = chapter.subject_id
    
    try:
        quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
        
        for quiz in quizzes:
            for question in quiz.questions:
                Option.query.filter_by(question_id=question.id).delete()
            
            Question.query.filter_by(quiz_id=quiz.id).delete()
            
            for attempt in quiz.attempts:
                UserResponse.query.filter_by(quiz_attempt_id=attempt.id).delete()
            
            QuizAttempt.query.filter_by(quiz_id=quiz.id).delete()
            Score.query.filter_by(quiz_id=quiz.id).delete()
            
            db.session.delete(quiz)
        
        db.session.delete(chapter)
        db.session.commit()
        
        flash('Chapter deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting chapter: {str(e)}', 'danger')
    
    return redirect(url_for('admin_subjects'))

@app.route('/admin/chapter/<int:chapter_id>/edit', methods=['POST'])
@admin_required
def edit_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    
    chapName = request.form.get('chapter_name')
    chapDescription = request.form.get('chapter_description', '')

    if not chapName:
        flash('Chapter name is required!', 'danger')
        return redirect(url_for('admin'))
    
    try:
        chapter.name = chapName.strip()
        chapter.description = chapDescription.strip()
        chapter.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        flash(f'{chapName} updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating chapter: {str(e)}', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/quiz/<int:chapter_id>/add', methods=['GET', 'POST'])
@admin_required
def add_quiz_form(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    
    if request.method == 'POST':
        quiz_name = request.form.get("quiz_name")
        description = request.form.get("quiz_description", "")
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        time_limit = int(request.form.get("time_limit"))
        passing_score = int(request.form.get("passing_score"))
        max_attempts = int(request.form.get("max_attempts", 3))
        is_active = request.form.get("is_active") == 'on'
        
        if not quiz_name or not start_date_str:
            flash("Quiz name and start date are required!", "danger")
            return redirect(url_for('add_quiz_form', chapter_id=chapter_id))
        
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            start_date = start_date.replace(tzinfo=timezone.utc)
            
            end_date = None
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            new_quiz = Quiz(
                name=quiz_name,
                description=description,
                start_date=start_date,
                end_date=end_date,
                time_duration=time_limit,
                passing_score=passing_score,
                max_attempts=max_attempts,
                chapter_id=chapter_id,
                is_active=is_active,
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(new_quiz)
            db.session.commit()
            
            flash(f"Quiz '{quiz_name}' created successfully!", "success")
            return redirect(url_for('add_quiz_questions', quiz_id=new_quiz.id))
        except Exception as e:
            flash(f"Error creating quiz: {str(e)}", "danger")
            return redirect(url_for('add_quiz_form', chapter_id=chapter_id))

    today = date.today().strftime("%Y-%m-%d")
    return render_template('admin/admin_quiz_add.html', chapter=chapter, today=today)

@app.route('/admin/quiz/<int:quiz_id>/edit', methods=['POST'])
@admin_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if request.method == 'POST':
        quiz_name = request.form.get('quiz_name')
        description = request.form.get('quiz_description')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        time_duration = request.form.get('time_duration')
        passing_score = request.form.get('passing_score')
        max_attempts = request.form.get('max_attempts', 3)
        is_active = bool(request.form.get('is_active'))
        
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            start_date = start_date.replace(tzinfo=timezone.utc)
            
            end_date = None
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            time_duration = int(time_duration)
            passing_score = int(passing_score)
            max_attempts = int(max_attempts)
            
            quiz.name = quiz_name
            quiz.description = description
            quiz.start_date = start_date
            quiz.end_date = end_date
            quiz.time_duration = time_duration
            quiz.passing_score = passing_score
            quiz.max_attempts = max_attempts
            quiz.is_active = is_active
            quiz.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            flash(f"Quiz '{quiz_name}' updated successfully!", "success")
            return redirect(url_for('subject_quizzes', subject_id=quiz.chapter.subject_id))
            
        except (ValueError, TypeError) as e:
            flash("Invalid date or number format!", 'danger')
            return redirect(url_for('subject_quizzes', subject_id=quiz.chapter.subject_id))
    
    flash("Invalid request method!", 'danger')
    return redirect(url_for('subject_quizzes', subject_id=quiz.chapter.subject_id))

@app.route('/admin/quiz/<int:quiz_id>/delete', methods=['POST'])
@admin_required
def delete_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    quiz_name = quiz.name
    
    try:
        for question in quiz.questions:
            Option.query.filter_by(question_id=question.id).delete()
        
        Question.query.filter_by(quiz_id=quiz_id).delete()
        
        for attempt in quiz.attempts:
            UserResponse.query.filter_by(quiz_attempt_id=attempt.id).delete()
        
        QuizAttempt.query.filter_by(quiz_id=quiz_id).delete()
        Score.query.filter_by(quiz_id=quiz_id).delete()
        
        db.session.delete(quiz)
        db.session.commit()
        
        flash(f"Quiz '{quiz_name}' deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting quiz: {str(e)}", "danger")
    
    return redirect(url_for('allQuizzes'))

@app.route('/admin/quizzes', methods=['GET'])
@admin_required
def allQuizzes():
    subject_id = request.args.get('subject_id')
    chapter_id = request.args.get('chapter_id')
    date_filter = request.args.get('date')
    duration_filter = request.args.get('duration')
    sort_by = request.args.get('sort_by', 'date_desc')
    
    now = datetime.now(timezone.utc)
    
    query = Quiz.query
    
    if subject_id and subject_id != '':
        try:
            subject_id = int(subject_id)
            chapters = Chapter.query.filter_by(subject_id=subject_id).all()
            chapter_ids = [chapter.id for chapter in chapters]
            if chapter_ids:
                query = query.filter(Quiz.chapter_id.in_(chapter_ids))
                app.logger.info(f"Filtering by subject_id {subject_id}, chapter_ids: {chapter_ids}")
        except (ValueError, TypeError):
            app.logger.warning(f"Invalid subject_id: {subject_id}")
    
    if chapter_id and chapter_id != '':
        try:
            chapter_id = int(chapter_id)
            query = query.filter(Quiz.chapter_id == chapter_id)
            app.logger.info(f"Filtering by chapter_id {chapter_id}")
        except (ValueError, TypeError):
            app.logger.warning(f"Invalid chapter_id: {chapter_id}")
    
    if date_filter and date_filter != '':
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
            filter_date = filter_date.replace(tzinfo=timezone.utc)
            filter_date_end = filter_date.replace(hour=23, minute=59, second=59)
            
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
    
    for quiz in quizzes:
        if quiz.start_date and quiz.start_date.tzinfo is None:
            db.session.query(Quiz).filter_by(id=quiz.id).update({
                'start_date': quiz.start_date.replace(tzinfo=timezone.utc)
            })
        if quiz.end_date and quiz.end_date.tzinfo is None:
            db.session.query(Quiz).filter_by(id=quiz.id).update({
                'end_date': quiz.end_date.replace(tzinfo=timezone.utc)
            })
    
    if any(quiz.start_date.tzinfo is None for quiz in quizzes if quiz.start_date) or \
       any(quiz.end_date.tzinfo is None for quiz in quizzes if quiz.end_date):
        db.session.commit()
        quizzes = query.all()
    
    subjects = Subject.query.all()
    return render_template('admin/admin_quiz_list.html', 
                         quizzes=quizzes,
                         subjects=subjects,
                         datetime=datetime,
                         timezone=timezone,
                         now=now)
    
@app.route('/admin/quiz/<int:quiz_id>/toggle-visibility', methods=['POST'])
@admin_required
def toggle_quiz_visibility(quiz_id):
    try:
        quiz = Quiz.query.get_or_404(quiz_id)
        
        data = request.get_json()
        is_active = data.get('is_active', False) if data else False
        
        quiz.is_active = is_active
        db.session.commit()
        
        return jsonify({'success': True, 'is_active': quiz.is_active})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error toggling quiz visibility: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/question/<int:question_id>/delete', methods=['POST'])
@admin_required
def delete_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz = Quiz.query.get(question.quiz_id)
    chapter = Chapter.query.get(quiz.chapter_id)
    
    try:
        Option.query.filter_by(question_id=question_id).delete()
        db.session.delete(question)
        db.session.commit()
        flash("Question deleted successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error deleting question: {str(e)}", 'danger')
    
    return redirect(url_for('subject_quizzes', subject_id=chapter.subject_id))

@app.route('/admin/quiz/<int:quiz_id>/questions', methods=['GET', 'POST'])
@admin_required
def add_quiz_questions(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    
    if request.method == 'POST':
        question_text = request.form.get('question_text')
        points = request.form.get('points', 1)
        
        if not question_text:
            flash('Question text is required!', 'danger')
            return redirect(url_for('add_quiz_questions', quiz_id=quiz_id))
        
        question = Question(
            statement=question_text,
            points=points,
            quiz_id=quiz_id,
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(question)
        db.session.commit()
        
        options_valid = True
        for i in range(4):
            option_text = request.form.get(f'option_{i}')
            if not option_text:
                options_valid = False
                break
                
            is_correct = request.form.get('correct_option') == str(i)
            option = Option(
                option_text=option_text,
                is_correct=is_correct,
                question_id=question.id
            )
            db.session.add(option)
        
        if not options_valid:
            db.session.rollback()
            flash('All options are required!', 'danger')
            return redirect(url_for('add_quiz_questions', quiz_id=quiz_id))
        
        db.session.commit()
        flash('Question added successfully!', 'success')
        return redirect(url_for('add_quiz_questions', quiz_id=quiz_id))
    
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    return render_template('admin/admin_quiz_questions.html', quiz=quiz, questions=questions)

@app.route('/admin/question/<int:question_id>/edit', methods=['POST'])
@admin_required
def edit_question(question_id):
    question = Question.query.get_or_404(question_id)
    quiz = Quiz.query.get(question.quiz_id)
    
    try:
        question_text = request.form.get('question_text')
        points = request.form.get('points', 1)
        
        if not question_text:
            flash('Question text is required!', 'danger')
            return redirect(url_for('add_quiz_questions', quiz_id=quiz.id))
        
        question.statement = question_text
        question.points = points
        
        correct_option_index = int(request.form.get('correct_option', 0))
        options = question.options
        
        for i, option in enumerate(options):
            option_text = request.form.get(f'option_{i}')
            option_id = request.form.get(f'option_id_{i}')
            
            if option_text and option.id == int(option_id):
                option.option_text = option_text
                option.is_correct = (i == correct_option_index)
        
        db.session.commit()
        flash('Question updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating question: {str(e)}', 'danger')
    
    return redirect(url_for('add_quiz_questions', quiz_id=quiz.id))

@app.route('/admin/subject/<int:subject_id>/quizzes')
@admin_required
def subject_quizzes(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    subject.chapters = Chapter.query.filter_by(subject_id=subject_id)\
        .order_by(Chapter.name)\
        .all()
    
    for chapter in subject.chapters:
        chapter.quizzes = Quiz.query.filter_by(chapter_id=chapter.id)\
            .order_by(Quiz.start_date.desc())\
            .all()
        
        for quiz in chapter.quizzes:
            if quiz.start_date and quiz.start_date.tzinfo is None:
                db.session.query(Quiz).filter_by(id=quiz.id).update({
                    'start_date': quiz.start_date.replace(tzinfo=timezone.utc)
                })
            if quiz.end_date and quiz.end_date.tzinfo is None:
                db.session.query(Quiz).filter_by(id=quiz.id).update({
                    'end_date': quiz.end_date.replace(tzinfo=timezone.utc)
                })
        
        if any(quiz.start_date.tzinfo is None for quiz in chapter.quizzes if quiz.start_date) or \
           any(quiz.end_date.tzinfo is None for quiz in chapter.quizzes if quiz.end_date):
            db.session.commit()
            chapter.quizzes = Quiz.query.filter_by(chapter_id=chapter.id)\
                .order_by(Quiz.start_date.desc())\
                .all()
    
    return render_template('admin/admin_subject_quizzes.html', subject=subject)

@app.route('/admin/subjects')
@admin_required
def admin_subjects():
    subjects = Subject.query.all()
    for subject in subjects:
        subject.chapters = Chapter.query.filter_by(subject_id=subject.id).all()
        for chapter in subject.chapters:
            chapter.quizzes = Quiz.query.filter_by(chapter_id=chapter.id).all()
    
    return render_template('admin/admin_subject_list.html', subjects=subjects)

@app.route('/admin/users')
@admin_required
def admin_users():
    search = request.args.get('search', '')
    sort_by = request.args.get('sort_by', 'recent')
    
    query = User.query.filter(User.email != 'admin@admin.com')
    
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            db.or_(
                User.fullName.ilike(search_term),
                User.email.ilike(search_term)
            )
        )
    
    if sort_by == 'recent':
        query = query.order_by(User.created_at.desc())
    elif sort_by == 'name_asc':
        query = query.order_by(User.fullName.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(User.fullName.desc())
    elif sort_by == 'email_asc':
        query = query.order_by(User.email.asc())
    
    users = query.all()
    
    for user in users:
        user.quiz_attempts = QuizAttempt.query.filter_by(user_id=user.id).all()
        user.scores = Score.query.filter_by(user_id=user.id).all()
        
        for score in user.scores:
            score.quiz = Quiz.query.get(score.quiz_id)
    
    return render_template('admin/admin_user_list.html', users=users)

@app.route('/admin/users/add', methods=['POST'])
@admin_required
def add_user():
    if request.method == 'POST':
        fullName = request.form.get('fullName')
        email = request.form.get('email')
        password = request.form.get('password')
        qualification = request.form.get('qualification')
        dob = request.form.get('dob')
        
        if not all([fullName, email, password]):
            flash('Name, email and password are required!', 'danger')
            return redirect(url_for('admin_users'))
        
        if User.query.filter_by(email=email).first():
            flash('A user with this email already exists!', 'danger')
            return redirect(url_for('admin_users'))
        
        try:
            dob_datetime = None
            if dob:
                dob_datetime = datetime.strptime(dob, '%Y-%m-%d')
                dob_datetime = dob_datetime.replace(tzinfo=timezone.utc)
            
            new_user = User(
                fullName=fullName,
                email=email,
                password=generate_password_hash(password),
                qualification=qualification,
                dob=dob_datetime,
                created_at=datetime.now(timezone.utc)
            )
            
            db.session.add(new_user)
            db.session.commit()
            
            flash(f'User {fullName} added successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding user: {str(e)}', 'danger')
        
        return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        fullName = request.form.get('fullName')
        email = request.form.get('email')
        qualification = request.form.get('qualification')
        dob = request.form.get('dob')
        
        if not all([fullName, email]):
            flash('Name and email are required!', 'danger')
            return redirect(url_for('admin_users'))
        
        existing_user = User.query.filter(User.email == email, User.id != user_id).first()
        if existing_user:
            flash('Another user with this email already exists!', 'danger')
            return redirect(url_for('admin_users'))
        
        try:
            user.fullName = fullName
            user.email = email            
            user.qualification = qualification
            
            if dob:
                dob_datetime = datetime.strptime(dob, '%Y-%m-%d')
                dob_datetime = dob_datetime.replace(tzinfo=timezone.utc)
                user.dob = dob_datetime
            
            db.session.commit()
            flash(f'User {fullName} updated successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating user: {str(e)}', 'danger')
        
        return redirect(url_for('admin_users'))

@app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    user_name = user.fullName
    
    try:
        attempts = QuizAttempt.query.filter_by(user_id=user_id).all()
        for attempt in attempts:
            UserResponse.query.filter_by(quiz_attempt_id=attempt.id).delete()
        
        QuizAttempt.query.filter_by(user_id=user_id).delete()
        
        Score.query.filter_by(user_id=user_id).delete()
        
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User {user_name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'danger')
    
    return redirect(url_for('admin_users'))

@app.route('/admin/search')
@admin_required
def admin_search():
    query = request.args.get('q', '')
    search_type = request.args.get('type', 'all')
    
    if not query:
        return render_template('admin/admin_search.html', 
                              results=None, 
                              query='',
                              search_type='all')
    
    search_term = f"%{query}%"
    
    results = {
        'users': [],
        'subjects': [],
        'chapters': [],
        'quizzes': []
    }
    
    if search_type == 'all' or search_type == 'users':
        users = User.query.filter(
            db.or_(
                User.fullName.ilike(search_term),
                User.email.ilike(search_term)
            )
        ).all()
        results['users'] = users
    
    if search_type == 'all' or search_type == 'subjects':
        subjects = Subject.query.filter(
            db.or_(
                Subject.name.ilike(search_term),
                Subject.description.ilike(search_term)
            )
        ).all()
        results['subjects'] = subjects
    
    if search_type == 'all' or search_type == 'chapters':
        chapters = Chapter.query.filter(
            db.or_(
                Chapter.name.ilike(search_term),
                Chapter.description.ilike(search_term)
            )
        ).join(Subject).all()
        
        for chapter in chapters:
            chapter.subject = Subject.query.get(chapter.subject_id)
        
        results['chapters'] = chapters
    
    if search_type == 'all' or search_type == 'quizzes':
        quizzes = Quiz.query.filter(
            db.or_(
                Quiz.name.ilike(search_term),
                Quiz.description.ilike(search_term)
            )
        ).all()
        
        for quiz in quizzes:
            quiz.chapter = Chapter.query.get(quiz.chapter_id)
            if quiz.chapter:
                quiz.chapter.subject = Subject.query.get(quiz.chapter.subject_id)
        
        results['quizzes'] = quizzes
    
    return render_template('admin/admin_search.html', 
                          results=results, 
                          query=query,
                          search_type=search_type)

@app.route('/admin/summary')
@admin_required
def admin_summary():
    if 'admin_id' not in session:
        flash('Unauthorized access!', 'danger')
        return redirect(url_for('admin'))

    admin_id = session.get('admin_id')
    admin = User.query.get_or_404(admin_id)

    subject_top_scores = db.session.query(
        Subject.name,
        db.func.max(Score.total_scored).label('top_score')
    ).join(
        Chapter, Subject.id == Chapter.subject_id
    ).join(
        Quiz, Chapter.id == Quiz.chapter_id
    ).join(
        Score, Quiz.id == Score.quiz_id
    ).group_by(
        Subject.name
    ).all()

    subject_names = [s.name for s in subject_top_scores]
    subject_top_scores_data = [float(s.top_score) if s.top_score else 0 for s in subject_top_scores]

    subject_user_attempts = db.session.query(
        Subject.name,
        db.func.count(QuizAttempt.id).label('attempts')
    ).join(
        Chapter, Subject.id == Chapter.subject_id
    ).join(
        Quiz, Chapter.id == Quiz.chapter_id
    ).join(
        QuizAttempt, Quiz.id == QuizAttempt.quiz_id
    ).group_by(
        Subject.name
    ).all()

    subject_attempts_names = [s.name for s in subject_user_attempts]
    subject_attempts_data = [s.attempts for s in subject_user_attempts]

    quiz_top_scores = db.session.query(
        Quiz.name,
        db.func.max(Score.total_scored).label('top_score')
    ).join(
        Score, Quiz.id == Score.quiz_id
    ).group_by(
        Quiz.name
    ).all()

    quiz_names = [q.name for q in quiz_top_scores]
    quiz_top_scores_data = [float(q.top_score) if q.top_score else 0 for q in quiz_top_scores]

    stats = {
        'subject_names': subject_names,
        'subject_top_scores': subject_top_scores_data,
        'subject_attempts_names': subject_attempts_names,
        'subject_attempts_data': subject_attempts_data,
        'quiz_names': quiz_names,
        'quiz_top_scores': quiz_top_scores_data
    }

    import json
    stats['subject_names_json'] = json.dumps(subject_names)
    stats['subject_top_scores_json'] = json.dumps(subject_top_scores_data)
    stats['subject_attempts_names_json'] = json.dumps(subject_attempts_names)
    stats['subject_attempts_data_json'] = json.dumps(subject_attempts_data)
    stats['quiz_names_json'] = json.dumps(quiz_names)
    stats['quiz_top_scores_json'] = json.dumps(quiz_top_scores_data)

    return render_template('admin/admin_summary.html', admin=admin, stats=stats)

