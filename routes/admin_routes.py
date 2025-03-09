from flask import request, redirect, flash, render_template, url_for, session, jsonify
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
        return render_template("admin/admin.html", subjects=subjects)
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

@app.route('/admin/add/subject', methods=['POST'])
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
    return redirect(url_for('admin'))

@app.route('/admin/edit/subject/<int:subject_id>', methods=['POST'])
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

@app.route('/admin/delete/subject/<int:subject_id>', methods=['POST'])
@admin_required
def delete_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    
    try:
        Chapter.query.filter_by(subject_id=subject_id).delete()
        db.session.delete(subject)
        db.session.commit()
        flash(f'{subject.name} deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting subject: {str(e)}', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/add/chapter', methods=['POST'])
@admin_required
def add_chapter():
    chapName = request.form.get('chapter_name')
    chapDescription = request.form.get('chapter_description', '')
    subject_id = request.form.get('subject_id')

    if not subject_id:
        flash('Invalid subject selected!', 'danger')
        return redirect(url_for('admin'))
    
    try:
        subject_id = int(subject_id)
    except ValueError:
        flash('Invalid subject ID!', 'danger')
        return redirect(url_for('admin'))

    subject = Subject.query.get(subject_id)
    if not subject:
        flash('Subject not found!', 'danger')
        return redirect(url_for('admin'))

    if not chapName:
        flash('Chapter name is required!', 'danger')
        return redirect(url_for('admin'))
    
    existingChapter = Chapter.query.filter(
        Chapter.name.ilike(chapName),
        Chapter.subject_id == subject_id
    ).first()
    
    if existingChapter:
        flash(f'A chapter with name : {chapName} already exists in this subject!', 'danger')
        return redirect(url_for('admin'))
    
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
    return redirect(url_for('admin'))

@app.route('/admin/delete/chapter/<int:chapter_id>', methods=['POST'])
@admin_required
def delete_chapter(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    
    try:
        db.session.delete(chapter)
        db.session.commit()
        flash('Chapter deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting chapter: {str(e)}', 'danger')
    
    return redirect(url_for('admin'))

@app.route('/admin/edit/chapter/<int:chapter_id>', methods=['POST'])
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

@app.route('/admin/add/quiz/<int:chapter_id>', methods=['POST'])
@admin_required
def add_quiz(chapter_id):
    if request.method == 'POST':
        quiz_name = request.form.get('quiz_name')
        description = request.form.get('quiz_description')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        time_limit = request.form.get('time_limit')
        passing_score = request.form.get('passing_score')
        max_attempts = request.form.get('max_attempts', 3)  # Default to 3 if not specified
        is_active = bool(request.form.get('is_active'))

        chapter = Chapter.query.get_or_404(chapter_id)
        
        try:
            # Convert date strings to timezone-aware datetime objects
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            start_date = start_date.replace(tzinfo=timezone.utc)
            
            end_date = None
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
                end_date = end_date.replace(tzinfo=timezone.utc)
            
            time_limit = int(time_limit)
            passing_score = int(passing_score)
            max_attempts = int(max_attempts)
            
            quiz = Quiz(
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
            
            db.session.add(quiz)
            db.session.commit()
            
            flash(f"Quiz '{quiz_name}' added successfully!", "success")
            return redirect(url_for('subject_quizzes', subject_id=chapter.subject_id))
            
        except (ValueError, TypeError) as e:
            flash("Invalid date or number format!", 'danger')
            return redirect(url_for('subject_quizzes', subject_id=chapter.subject_id))

@app.route('/admin/quizzes', methods=['GET'])
@admin_required
def allQuizzes():
    # Get filter parameters
    subject_id = request.args.get('subject')
    date_filter = request.args.get('date')
    duration_filter = request.args.get('duration')
    sort_by = request.args.get('sort_by', 'date_desc')
    
    now = datetime.now(timezone.utc)
    
    # Base query
    query = Quiz.query
    
    # Apply filters
    if subject_id:
        chapters = Chapter.query.filter_by(subject_id=subject_id).all()
        chapter_ids = [chapter.id for chapter in chapters]
        query = query.filter(Quiz.chapter_id.in_(chapter_ids))
    
    if date_filter:
        try:
            # Convert the filter date to a timezone-aware datetime at the start of the day
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d')
            filter_date = filter_date.replace(tzinfo=timezone.utc)
            filter_date_end = filter_date.replace(hour=23, minute=59, second=59)
            
            # Filter quizzes that start on the selected date
            query = query.filter(Quiz.start_date >= filter_date, Quiz.start_date <= filter_date_end)
        except ValueError:
            flash('Invalid date format', 'danger')
    
    if duration_filter:
        if duration_filter == '0-15':
            query = query.filter(Quiz.time_duration <= 15)
        elif duration_filter == '15-30':
            query = query.filter(Quiz.time_duration > 15, Quiz.time_duration <= 30)
        elif duration_filter == '30+':
            query = query.filter(Quiz.time_duration > 30)
    
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
    if any(quiz.start_date.tzinfo is None for quiz in quizzes if quiz.start_date) or \
       any(quiz.end_date.tzinfo is None for quiz in quizzes if quiz.end_date):
        db.session.commit()
        quizzes = query.all()  # Refresh the quiz objects
    
    subjects = Subject.query.all()
    return render_template('admin/adminQuiz.html', 
                         quizzes=quizzes,
                         subjects=subjects,
                         datetime=datetime,
                         timezone=timezone,
                         now=now)

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
        max_attempts = int(request.form.get("max_attempts", 3))  # Default to 3 if not provided
        
        if not quiz_name or not start_date_str:
            flash("Quiz name and start date are required!", "danger")
            return redirect(url_for('add_quiz_form', chapter_id=chapter_id))
        
        try:
            # Convert date strings to timezone-aware datetime objects
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
    return render_template('admin/add_quiz.html', chapter=chapter, today=today)

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
            # Convert date strings to timezone-aware datetime objects
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
    chapter = Chapter.query.get(quiz.chapter_id)
    
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
    
    return redirect(url_for('subject_quizzes', subject_id=chapter.subject_id))

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
    chapter = Chapter.query.get(quiz.chapter_id)
    
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
    return render_template('admin/quiz_questions.html', quiz=quiz, questions=questions)

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
            chapter.quizzes = Quiz.query.filter_by(chapter_id=chapter.id)\
                .order_by(Quiz.start_date.desc())\
                .all()
    
    return render_template('admin/subject_quizzes.html', subject=subject)

@app.route('/admin/quiz/<int:quiz_id>/toggle-visibility', methods=['POST'])
@admin_required
def toggle_quiz_visibility(quiz_id):
    try:
        quiz = Quiz.query.get_or_404(quiz_id)
        
        # Parse request data
        data = request.get_json()
        is_active = data.get('is_active', False) if data else False
        
        # Update quiz visibility
        quiz.is_active = is_active
        db.session.commit()
        
        return jsonify({'success': True, 'is_active': quiz.is_active})
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error toggling quiz visibility: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

