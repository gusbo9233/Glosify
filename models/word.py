import json
from datetime import datetime

from database import db


class Word(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lemma = db.Column(db.String(200), nullable=False)
    translation = db.Column(db.String(200), nullable=False)
    properties = db.Column(db.Text)  # JSON string storing properties like {"gender": "masc", "aspect": "impf"}
    example_sentence = db.Column(db.String(500))  # Example sentence using the word
    explanation = db.Column(db.Text)  # Detailed explanation of the word (can be several sentences)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id'), nullable=False)
    variants = db.relationship('Variant', backref='word', lazy=True, cascade='all, delete-orphan')

    # Anki-style spaced repetition fields - Forward direction (show lemma, guess translation)
    ease_factor = db.Column(db.Float, default=2.5)
    interval = db.Column(db.Integer, default=0)
    repetitions = db.Column(db.Integer, default=0)
    due_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Anki-style spaced repetition fields - Reverse direction (show translation, guess lemma)
    ease_factor_reverse = db.Column(db.Float, default=2.5)
    interval_reverse = db.Column(db.Integer, default=0)
    repetitions_reverse = db.Column(db.Integer, default=0)
    due_date_reverse = db.Column(db.DateTime, default=datetime.utcnow)

    def get_properties(self):
        """Parse properties from JSON string to dict."""
        if self.properties:
            return json.loads(self.properties)
        return {}

    def set_properties(self, properties_dict):
        """Store properties dict as JSON string."""
        self.properties = json.dumps(properties_dict) if properties_dict else None
