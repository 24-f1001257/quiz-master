from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(30), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    fullName = db.Column(db.String(50))
    qualification = db.Column(db.String(50))
    dob = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    
    quiz_attempts = db.relationship('QuizAttempt', backref='user', lazy=True)
    scores = db.relationship('Score', backref='user', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    chapters = db.relationship('Chapter', backref='subject', lazy=True)

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    quizzes = db.relationship('Quiz', backref='chapter', lazy=True)

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    start_date = db.Column(db.DateTime(timezone=True), nullable=False)
    end_date = db.Column(db.DateTime(timezone=True))
    time_duration = db.Column(db.Integer, nullable=False)
    passing_score = db.Column(db.Integer, nullable=False)
    max_attempts = db.Column(db.Integer, default=3)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=datetime.now(timezone.utc))
    
    questions = db.relationship('Question', backref='quiz', lazy=True)
    attempts = db.relationship('QuizAttempt', backref='quiz', lazy=True)
    scores = db.relationship('Score', backref='quiz', lazy=True)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    statement = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, nullable=False, default=1)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))

    options = db.relationship('Option', backref='question', lazy=True)
    user_responses = db.relationship('UserResponse', backref='question', lazy=True)

class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    user_responses = db.relationship('UserResponse', backref='selected_option', lazy=True)

class QuizAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    attempt_number = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime(timezone=True))
    status = db.Column(db.String(20), default='in_progress')

    user_responses = db.relationship('UserResponse', backref='quiz_attempt', lazy=True)

class UserResponse(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_attempt_id = db.Column(db.Integer, db.ForeignKey('quiz_attempt.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_option_id = db.Column(db.Integer, db.ForeignKey('option.id'), nullable=False)
    is_correct = db.Column(db.Boolean, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total_scored = db.Column(db.Integer, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    passed = db.Column(db.Boolean)
    start_time = db.Column(db.DateTime(timezone=True), nullable=False, default=datetime.now(timezone.utc))
    end_time = db.Column(db.DateTime(timezone=True))
    attempt_number = db.Column(db.Integer, nullable=False, default=1)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc))
