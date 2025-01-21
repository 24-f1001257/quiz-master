from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(36), unique=True, nullable=False, index=True)
    password = db.Column(db.String(256), nullable=False)
    fullName = db.Column(db.String(50))
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    qualification = db.Column(db.String(50))
    dob = db.Column(db.Date)
    is_active = db.Column(db.Boolean, default=True)


class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.Text)

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False, index=True)

    subject = db.relationship('Subject', backref=db.backref('chapters', lazy=True))

class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    time_limit = db.Column(db.Integer, nullable=False)
    passing_score = db.Column(db.Integer, nullable=False)
    max_attempts = db.Column(db.Integer, default=1)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False, index=True)
    is_active = db.Column(db.Boolean, default=True)

    chapter = db.relationship('Chapter', backref=db.backref('quizzes', lazy=True))

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    statement = db.Column(db.Text, nullable=False)
    points = db.Column(db.Integer, nullable=False, default=1)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False, index=True)

    quiz = db.relationship('Quiz', backref=db.backref('questions', lazy=True))


class Option(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    option_text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False, index=True)

    question = db.relationship('Question', backref=db.backref('options', lazy=True))

class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    score = db.Column(db.Integer, nullable=False)
    is_completed = db.Column(db.Boolean, default=False)
    passed = db.Column(db.Boolean)
    timeStarted = db.Column(db.DateTime, nullable=False)
    timeEnded = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False, index=True)

    user = db.relationship('User', backref=db.backref('scores', lazy=True))
    quiz = db.relationship('Quiz', backref=db.backref('scores', lazy=True))