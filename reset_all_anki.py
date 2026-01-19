#!/usr/bin/env python3
"""Reset all Anki tracking for all quizzes, words, and sentences."""

from app import app, db, Quiz, Word, Sentence
from datetime import datetime

def reset_all_anki():
    """Reset all Anki progress for all quizzes."""
    with app.app_context():
        now = datetime.utcnow()
        
        # Get all quizzes
        quizzes = Quiz.query.all()
        total_quizzes = len(quizzes)
        
        print(f"Found {total_quizzes} quiz(es)")
        
        word_count = 0
        sentence_count = 0
        
        for quiz in quizzes:
            # Reset words (both directions)
            words = Word.query.filter_by(quiz_id=quiz.id).all()
            for word in words:
                # Forward direction
                word.ease_factor = 2.5
                word.interval = 0
                word.repetitions = 1  # Set to 1 so it's "due" not "new"
                word.due_date = now
                
                # Reverse direction
                word.ease_factor_reverse = 2.5
                word.interval_reverse = 0
                word.repetitions_reverse = 1  # Set to 1 so it's "due" not "new"
                word.due_date_reverse = now
                
                word_count += 1
            
            # Reset sentences (both directions)
            sentences = Sentence.query.filter_by(quiz_id=quiz.id).all()
            for sentence in sentences:
                # Forward direction
                sentence.ease_factor = 2.5
                sentence.interval = 0
                sentence.repetitions = 1  # Set to 1 so it's "due" not "new"
                sentence.due_date = now
                
                # Reverse direction
                sentence.ease_factor_reverse = 2.5
                sentence.interval_reverse = 0
                sentence.repetitions_reverse = 1  # Set to 1 so it's "due" not "new"
                sentence.due_date_reverse = now
                
                sentence_count += 1
        
        # Commit all changes
        db.session.commit()
        
        print(f"\n✓ Successfully reset Anki tracking!")
        print(f"  - {word_count} word(s) reset (both directions)")
        print(f"  - {sentence_count} sentence(s) reset (both directions)")
        print(f"  - All cards are now due")

if __name__ == '__main__':
    print("Resetting all Anki tracking...")
    print("=" * 50)
    reset_all_anki()
    print("=" * 50)
    print("Done!")
