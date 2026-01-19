from datetime import datetime

from database import db


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    folder_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)  # Optional: quiz can be in a folder
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_song_quiz = db.Column(db.Boolean, default=False)  # True if created from song lyrics
    processing_status = db.Column(db.String(20), default='completed')  # 'pending', 'processing', 'completed', 'error'
    processing_message = db.Column(db.String(200))  # Status message like "Processing 5/20 words..."
    source_language = db.Column(db.String(50))  # e.g., "English"
    target_language = db.Column(db.String(50))  # e.g., "Polish"
    anki_tracking_enabled = db.Column(db.Boolean, default=True)  # Whether Anki tracking is enabled for this quiz
    is_public = db.Column(db.Boolean, default=False)  # Whether the quiz is public (visible to other users)
    original_quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=True)  # If set, this is a subscription copy
    words = db.relationship('Word', backref='quiz', lazy=True, cascade='all, delete-orphan')
    sentences = db.relationship('Sentence', backref='quiz', lazy=True, cascade='all, delete-orphan')
