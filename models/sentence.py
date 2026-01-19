from datetime import datetime

from database import db


class Sentence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)  # Original sentence/line from the song
    translation = db.Column(db.String(500))  # Translation of the sentence
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)

    # Anki-style spaced repetition fields - Forward direction (show text, guess translation)
    ease_factor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=0)
    repetitions = db.Column(db.Integer, default=0)
    due_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Anki-style spaced repetition fields - Reverse direction (show translation, guess text)
    ease_factor_reverse = db.Column(db.Float, default=2.5)
    interval_reverse = db.Column(db.Integer, default=0)
    repetitions_reverse = db.Column(db.Integer, default=0)
    due_date_reverse = db.Column(db.DateTime, default=datetime.utcnow)
