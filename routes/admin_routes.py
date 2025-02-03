from flask import request, redirect, flash, render_template, url_for, make_response
from models import *
from utils import *
from app import app


@app.route('/admin', methods=['GET', 'POST'])
@admin_required
def admin():
    subjects = Subject.query.all()
    return render_template("admin.html", subjects=subjects)

@app.route('/admin/logout')
@admin_required
def adminLogout():
    response = make_response(redirect(url_for('login')))
    response.delete_cookie('admin_id')
    flash('LoggedOut successfully!!', 'success')
    return response

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
