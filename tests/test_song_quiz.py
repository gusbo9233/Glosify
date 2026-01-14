#!/usr/bin/env python3
"""
Test script for song quiz creation (backend only).
Tests the logic without the web interface to identify bottlenecks.
"""

import sys
import os
import time
import re
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, Quiz, Word, Sentence, Variant, User
from gptcaller import get_gpt_caller, convert_to_word_class


def extract_unique_words(lyrics):
    """Extract unique words from lyrics."""
    all_words = re.findall(r'\b\w+\b', lyrics.lower())
    unique_words = list(dict.fromkeys(all_words))
    return unique_words


def extract_unique_lines(lyrics):
    """Extract unique lines from lyrics."""
    lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
    unique_lines = list(dict.fromkeys(lines))
    return unique_lines


def test_song_quiz_creation(lyrics, language="Ukrainian", user_id=1, limit_words=None, limit_sentences=None):
    """
    Test song quiz creation with timing information.
    
    Args:
        lyrics: Song lyrics text
        language: Language of the lyrics
        user_id: User ID to create quiz for
        limit_words: Limit number of words to process (for testing)
        limit_sentences: Limit number of sentences to process (for testing)
    """
    print("=" * 60)
    print("Testing Song Quiz Creation (Backend Only)")
    print("=" * 60)
    
    start_time = time.time()
    
    # Extract words and sentences
    print("\n1. Extracting words and sentences...")
    extract_start = time.time()
    unique_words = extract_unique_words(lyrics)
    unique_lines = extract_unique_lines(lyrics)
    extract_time = time.time() - extract_start
    
    print(f"   Found {len(unique_words)} unique words")
    print(f"   Found {len(unique_lines)} unique lines")
    print(f"   Extraction took: {extract_time:.2f}s")
    
    # Limit for testing
    if limit_words:
        unique_words = unique_words[:limit_words]
        print(f"   Limited to {len(unique_words)} words for testing")
    if limit_sentences:
        unique_lines = unique_lines[:limit_sentences]
        print(f"   Limited to {len(unique_lines)} sentences for testing")
    
    # Create quiz
    print("\n2. Creating quiz in database...")
    db_start = time.time()
    with app.app_context():
        new_quiz = Quiz(
            name=f"Test Song Quiz - {datetime.now().strftime('%H:%M:%S')}",
            user_id=user_id,
            is_song_quiz=True
        )
        db.session.add(new_quiz)
        db.session.flush()
        quiz_id = new_quiz.id
        db.session.commit()
    db_time = time.time() - db_start
    print(f"   Quiz created with ID: {quiz_id}")
    print(f"   Database operation took: {db_time:.2f}s")
    
    # Initialize GPT caller
    print("\n3. Initializing GPT caller...")
    gpt_start = time.time()
    try:
        caller = get_gpt_caller()
        gpt_init_time = time.time() - gpt_start
        print(f"   GPT caller initialized in: {gpt_init_time:.2f}s")
    except Exception as e:
        print(f"   ✗ Error initializing GPT caller: {e}")
        return
    
    # Process sentences
    print(f"\n4. Processing {len(unique_lines)} sentences...")
    sentence_times = []
    sentences_created = 0
    
    for i, line in enumerate(unique_lines, 1):
        line_start = time.time()
        try:
            with app.app_context():
                sentence_analysis = caller.generate_sentence_translation(
                    sentence=line,
                    language=language
                )
                translation = sentence_analysis.translation if hasattr(sentence_analysis, 'translation') else ""
                
                new_sentence = Sentence(
                    text=line,
                    translation=translation,
                    quiz_id=quiz_id
                )
                db.session.add(new_sentence)
                db.session.commit()
                sentences_created += 1
                
                line_time = time.time() - line_start
                sentence_times.append(line_time)
                print(f"   [{i}/{len(unique_lines)}] '{line[:50]}...' → {translation[:50] if translation else 'N/A'}... ({line_time:.2f}s)")
        except Exception as e:
            line_time = time.time() - line_start
            print(f"   [{i}/{len(unique_lines)}] ✗ Error: {str(e)[:100]} ({line_time:.2f}s)")
            with app.app_context():
                new_sentence = Sentence(
                    text=line,
                    translation="",
                    quiz_id=quiz_id
                )
                db.session.add(new_sentence)
                db.session.commit()
    
    if sentence_times:
        avg_sentence_time = sum(sentence_times) / len(sentence_times)
        total_sentence_time = sum(sentence_times)
        print(f"\n   Sentences: {sentences_created}/{len(unique_lines)} created")
        print(f"   Average time per sentence: {avg_sentence_time:.2f}s")
        print(f"   Total sentence processing time: {total_sentence_time:.2f}s")
    
    # Process words
    print(f"\n5. Processing {len(unique_words)} words...")
    word_times = []
    words_created = 0
    
    for i, word_text in enumerate(unique_words, 1):
        word_start = time.time()
        try:
            with app.app_context():
                analysis = caller.generate_word_analysis(
                    lemma=word_text,
                    translation="",
                    language=language
                )
                
                translation = analysis.translations[0] if analysis.translations else ""
                
                new_word = Word(
                    lemma=word_text,
                    translation=translation,
                    quiz_id=quiz_id
                )
                
                word_data = convert_to_word_class(analysis, word_text)
                
                if word_data['properties']:
                    new_word.set_properties(word_data['properties'])
                
                if word_data.get('example_sentence'):
                    new_word.example_sentence = word_data['example_sentence']
                
                db.session.add(new_word)
                db.session.flush()
                word_id = new_word.id
                
                # Add variants
                variants_added = 0
                for variant_data in word_data['variants']:
                    new_variant = Variant(
                        value=variant_data['value'],
                        translation=variant_data['translation'],
                        word_id=word_id
                    )
                    if variant_data.get('tags'):
                        new_variant.set_tags(variant_data['tags'])
                    db.session.add(new_variant)
                    variants_added += 1
                
                db.session.commit()
                words_created += 1
                
                word_time = time.time() - word_start
                word_times.append(word_time)
                print(f"   [{i}/{len(unique_words)}] '{word_text}' → '{translation}' ({variants_added} variants) ({word_time:.2f}s)")
        except Exception as e:
            word_time = time.time() - word_start
            print(f"   [{i}/{len(unique_words)}] ✗ Error: {str(e)[:100]} ({word_time:.2f}s)")
            with app.app_context():
                new_word = Word(
                    lemma=word_text,
                    translation="",
                    quiz_id=quiz_id
                )
                db.session.add(new_word)
                db.session.commit()
    
    if word_times:
        avg_word_time = sum(word_times) / len(word_times)
        total_word_time = sum(word_times)
        print(f"\n   Words: {words_created}/{len(unique_words)} created")
        print(f"   Average time per word: {avg_word_time:.2f}s")
        print(f"   Total word processing time: {total_word_time:.2f}s")
    
    # Summary
    total_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total time: {total_time:.2f}s ({total_time/60:.2f} minutes)")
    print(f"Sentences processed: {sentences_created}/{len(unique_lines)}")
    print(f"Words processed: {words_created}/{len(unique_words)}")
    if sentence_times:
        print(f"Average sentence time: {avg_sentence_time:.2f}s")
    if word_times:
        print(f"Average word time: {avg_word_time:.2f}s")
    print(f"\nEstimated time for full song:")
    if sentence_times and word_times:
        est_sentences = len(unique_lines) * avg_sentence_time
        est_words = len(unique_words) * avg_word_time
        est_total = est_sentences + est_words
        print(f"  Sentences: {est_sentences:.2f}s ({est_sentences/60:.2f} min)")
        print(f"  Words: {est_words:.2f}s ({est_words/60:.2f} min)")
        print(f"  Total: {est_total:.2f}s ({est_total/60:.2f} min)")
    
    print("\n✓ Test complete!")
    return quiz_id


def ensure_test_user():
    """Ensure a test user exists, create if not."""
    with app.app_context():
        user = User.query.filter_by(username="test_user").first()
        if not user:
            from flask_bcrypt import Bcrypt
            bcrypt = Bcrypt(app)
            hashed_password = bcrypt.generate_password_hash("test123")
            user = User(username="test_user", password=hashed_password)
            db.session.add(user)
            db.session.commit()
            print(f"Created test user with ID: {user.id}")
        else:
            print(f"Using existing test user with ID: {user.id}")
        return user.id


def main():
    """Main test function."""
    # Ensure test user exists
    print("Checking for test user...")
    user_id = ensure_test_user()
    
    # Sample lyrics for testing
    sample_lyrics = """Стіл стоїть у кімнаті
Він дуже старий
На столі лежить книга
Книга дуже цікава
Я читаю книгу
Книга про Україну"""
    
    print("\nChoose test mode:")
    print("1. Quick test (2 words, 2 sentences)")
    print("2. Small test (5 words, 5 sentences)")
    print("3. Medium test (10 words, 10 sentences)")
    print("4. Full test (all words and sentences)")
    print("5. Custom test")
    
    choice = input("\nEnter choice (1-5): ").strip()
    
    if choice == "1":
        test_song_quiz_creation(sample_lyrics, "Ukrainian", user_id, limit_words=2, limit_sentences=2)
    elif choice == "2":
        test_song_quiz_creation(sample_lyrics, "Ukrainian", user_id, limit_words=5, limit_sentences=5)
    elif choice == "3":
        test_song_quiz_creation(sample_lyrics, "Ukrainian", user_id, limit_words=10, limit_sentences=10)
    elif choice == "4":
        test_song_quiz_creation(sample_lyrics, "Ukrainian", user_id)
    elif choice == "5":
        lyrics = input("Paste lyrics: ")
        lang = input("Language (default: Ukrainian): ").strip() or "Ukrainian"
        words_limit = input("Word limit (press Enter for all): ").strip()
        sentences_limit = input("Sentence limit (press Enter for all): ").strip()
        words_limit = int(words_limit) if words_limit else None
        sentences_limit = int(sentences_limit) if sentences_limit else None
        test_song_quiz_creation(lyrics, lang, user_id, limit_words=words_limit, limit_sentences=sentences_limit)
    else:
        print("Invalid choice. Running quick test...")
        test_song_quiz_creation(sample_lyrics, "Ukrainian", user_id, limit_words=2, limit_sentences=2)


if __name__ == "__main__":
    main()

