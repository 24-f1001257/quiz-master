from flask import request, redirect, flash, render_template, url_for, session
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
        return render_template("admin.html", subjects=subjects)
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
    try:
        chapter = Chapter.query.get_or_404(chapter_id)
        quiz_name = request.form.get("quiz_name")
        description = request.form.get("quiz_description")
        date_of_quiz_str = request.form.get("date_of_quiz")
        time_limit = request.form.get("time_limit")
        passing_score = request.form.get("passing_score")

        if not all([quiz_name, date_of_quiz_str, time_limit, passing_score]):
            flash("All required fields must be filled!", 'danger')
            return redirect(url_for('subject_quizzes', subject_id=chapter.subject_id))

        try:
            date_of_quiz = datetime.strptime(date_of_quiz_str, "%Y-%m-%d")
            time_limit = int(time_limit)
            passing_score = int(passing_score)
        except (ValueError, TypeError):
            flash("Invalid date or number format!", 'danger')
            return redirect(url_for('subject_quizzes', subject_id=chapter.subject_id))

        quiz = Quiz(
            name=quiz_name,
            description=description,
            date_of_quiz=date_of_quiz,
            time_duration=time_limit,
            passing_score=passing_score,
            chapter_id=chapter_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        db.session.add(quiz)
        db.session.commit()
        flash(f"Quiz '{quiz_name}' added successfully!", 'success')
        return redirect(url_for('subject_quizzes', subject_id=chapter.subject_id))

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error adding quiz: {str(e)}")
        flash('An error occurred while adding the quiz', 'danger')
        return redirect(url_for('subject_quizzes', subject_id=chapter.subject_id))

@app.route('/admin/quizzes', methods=['GET'])
@admin_required
def allQuizzes():
    subject_id = request.args.get('subject_id', type=int)
    chapter_id = request.args.get('chapter_id', type=int)
    duration_range = request.args.get('duration')
    date_filter = request.args.get('date')
    sort_by = request.args.get('sort_by', 'date_desc')
    
    query = Quiz.query
    
    if subject_id:
        query = query.join(Chapter).join(Subject).filter(Subject.id == subject_id)
    
    if chapter_id:
        query = query.filter(Quiz.chapter_id == chapter_id)
    
    if duration_range:
        if duration_range == '0-15':
            query = query.filter(Quiz.time_duration < 15)
        elif duration_range == '15-30':
            query = query.filter(Quiz.time_duration >= 15, Quiz.time_duration <= 30)
        elif duration_range == '30+':
            query = query.filter(Quiz.time_duration > 30)
    
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, '%Y-%m-%d').date()
            query = query.filter(func.date(Quiz.date_of_quiz) == filter_date)
        except ValueError:
            flash('Invalid date format', 'danger')
    
    if sort_by == 'date_desc':
        query = query.order_by(Quiz.date_of_quiz.desc())
    elif sort_by == 'date_asc':
        query = query.order_by(Quiz.date_of_quiz.asc())
    elif sort_by == 'name_asc':
        query = query.order_by(Quiz.name.asc())
    elif sort_by == 'name_desc':
        query = query.order_by(Quiz.name.desc())
    elif sort_by == 'duration_asc':
        query = query.order_by(Quiz.time_duration.asc())
    elif sort_by == 'duration_desc':
        query = query.order_by(Quiz.time_duration.desc())
    
    quizzes = query.all()
    subjects = Subject.query.all()
    
    return render_template('adminQuiz.html', quizzes=quizzes, subjects=subjects)

@app.route('/admin/quiz/<int:chapter_id>/add', methods=['GET', 'POST'])
@admin_required
def add_quiz_form(chapter_id):
    chapter = Chapter.query.get_or_404(chapter_id)
    
    if request.method == 'POST':
        quiz_name = request.form.get("quiz_name")
        description = request.form.get("quiz_description", "")
        date_of_quiz = datetime.strptime(request.form.get("date_of_quiz"), "%Y-%m-%d")
        time_limit = int(request.form.get("time_limit"))
        passing_score = int(request.form.get("passing_score"))
        
        if not quiz_name:
            flash("Quiz name is required!", "danger")
            return redirect(url_for('add_quiz_form', chapter_id=chapter_id))
            
        new_quiz = Quiz(
            name=quiz_name,
            description=description,
            date_of_quiz=date_of_quiz,
            time_duration=time_limit,
            passing_score=passing_score,
            chapter_id=chapter_id
        )
        
        db.session.add(new_quiz)
        db.session.commit()
        
        flash(f"Quiz '{quiz_name}' created successfully!", "success")
        return redirect(url_for('add_quiz_questions', quiz_id=new_quiz.id))
    
    today = date.today().strftime("%Y-%m-%d")
    return render_template('add_quiz.html', chapter=chapter, today=today)

@app.route('/admin/quiz/<int:quiz_id>/edit', methods=['POST'])
@admin_required
def edit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    chapter = Chapter.query.get(quiz.chapter_id)
    
    quiz_name = request.form.get("quiz_name")
    description = request.form.get("quiz_description", "")
    date_of_quiz_str = request.form.get("date_of_quiz")
    time_duration = request.form.get("time_duration")
    passing_score = request.form.get("passing_score")
    
    if not quiz_name:
        flash("Quiz name is required!", "danger")
        return redirect(url_for('subject_quizzes', subject_id=chapter.subject_id))
        
    try:
        date_of_quiz = datetime.strptime(date_of_quiz_str, "%Y-%m-%d")
        time_duration = int(time_duration)
        passing_score = int(passing_score)
        
        quiz.name = quiz_name
        quiz.description = description
        quiz.date_of_quiz = date_of_quiz
        quiz.time_duration = time_duration
        quiz.passing_score = passing_score
        quiz.updated_at = datetime.now(timezone.utc)
        
        db.session.commit()
        flash(f"Quiz '{quiz_name}' updated successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error updating quiz: {str(e)}", "danger")
    
    return redirect(url_for('subject_quizzes', subject_id=chapter.subject_id))

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
    return render_template('quiz_questions.html', quiz=quiz, questions=questions)

@app.route('/admin/subject/<int:subject_id>/quizzes')
@admin_required
def subject_quizzes(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    subject.chapters = Chapter.query.filter_by(subject_id=subject_id)\
        .order_by(Chapter.name)\
        .all()
    
    for chapter in subject.chapters:
        chapter.quizzes = Quiz.query.filter_by(chapter_id=chapter.id)\
            .order_by(Quiz.date_of_quiz.desc())\
            .all()
    
    return render_template('subject_quizzes.html', subject=subject)

