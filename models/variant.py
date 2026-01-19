import json

from database import db


class Variant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.String(200), nullable=False)  # The variant form (e.g., "столу")
    translation = db.Column(db.String(200), nullable=False)  # Translation for this variant
    tags = db.Column(db.Text)  # JSON string storing tags like {"case": "gen", "number": "sg"}
    word_id = db.Column(db.Integer, db.ForeignKey('word.id'), nullable=False)

    def get_tags(self):
        """Parse tags from JSON string to dict."""
        if self.tags:
            return json.loads(self.tags)
        return {}

    def set_tags(self, tags_dict):
        """Store tags dict as JSON string."""
        self.tags = json.dumps(tags_dict) if tags_dict else None
