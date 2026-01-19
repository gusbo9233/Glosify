#!/usr/bin/env python3
"""Test script: Create test users and public quizzes."""

from app import app, db, User, Quiz, Word, Sentence, Folder
from flask_bcrypt import Bcrypt
from datetime import datetime

bcrypt = Bcrypt(app)

def create_test_data():
    """Create test users and public quizzes."""
    with app.app_context():
        # Test users data
        test_users = [
            {'username': 'alice_language', 'password': 'test123'},
            {'username': 'bob_vocab', 'password': 'test123'},
            {'username': 'charlie_words', 'password': 'test123'},
        ]
        
        # Test quizzes data
        test_quizzes = [
            {
                'name': 'Spanish Basics',
                'source_language': 'English',
                'target_language': 'Spanish',
                'words': [
                    {'lemma': 'hello', 'translation': 'hola'},
                    {'lemma': 'goodbye', 'translation': 'adiós'},
                    {'lemma': 'please', 'translation': 'por favor'},
                    {'lemma': 'thank you', 'translation': 'gracias'},
                    {'lemma': 'yes', 'translation': 'sí'},
                ]
            },
            {
                'name': 'French Greetings',
                'source_language': 'English',
                'target_language': 'French',
                'words': [
                    {'lemma': 'hello', 'translation': 'bonjour'},
                    {'lemma': 'goodbye', 'translation': 'au revoir'},
                    {'lemma': 'good morning', 'translation': 'bonjour'},
                    {'lemma': 'good evening', 'translation': 'bonsoir'},
                ]
            },
            {
                'name': 'German Numbers',
                'source_language': 'English',
                'target_language': 'German',
                'words': [
                    {'lemma': 'one', 'translation': 'eins'},
                    {'lemma': 'two', 'translation': 'zwei'},
                    {'lemma': 'three', 'translation': 'drei'},
                    {'lemma': 'four', 'translation': 'vier'},
                    {'lemma': 'five', 'translation': 'fünf'},
                ]
            },
            {
                'name': 'Italian Food',
                'source_language': 'English',
                'target_language': 'Italian',
                'words': [
                    {'lemma': 'pizza', 'translation': 'pizza'},
                    {'lemma': 'pasta', 'translation': 'pasta'},
                    {'lemma': 'bread', 'translation': 'pane'},
                    {'lemma': 'cheese', 'translation': 'formaggio'},
                ]
            },
            {
                'name': 'Japanese Basics',
                'source_language': 'English',
                'target_language': 'Japanese',
                'words': [
                    {'lemma': 'hello', 'translation': 'こんにちは'},
                    {'lemma': 'thank you', 'translation': 'ありがとう'},
                    {'lemma': 'yes', 'translation': 'はい'},
                    {'lemma': 'no', 'translation': 'いいえ'},
                ]
            },
        ]
        
        created_users = []
        
        # Create users
        print("Creating test users...")
        for user_data in test_users:
            # Check if user already exists
            existing_user = User.query.filter_by(username=user_data['username']).first()
            if existing_user:
                print(f"  - User '{user_data['username']}' already exists, skipping...")
                created_users.append(existing_user)
            else:
                hashed_password = bcrypt.generate_password_hash(user_data['password']).decode('utf-8')
                new_user = User(
                    username=user_data['username'],
                    password=hashed_password
                )
                db.session.add(new_user)
                db.session.flush()  # Get the user ID
                created_users.append(new_user)
                print(f"  ✓ Created user: {user_data['username']}")
        
        db.session.commit()
        
        # Create subscriptions folders for new users
        print("\nEnsuring subscriptions folders exist...")
        for user in created_users:
            subscriptions_folder = Folder.query.filter_by(
                user_id=user.id,
                parent_id=None,
                name='subscriptions'
            ).first()
            
            if not subscriptions_folder:
                subscriptions_folder = Folder(
                    name='subscriptions',
                    user_id=user.id,
                    parent_id=None
                )
                db.session.add(subscriptions_folder)
                print(f"  ✓ Created 'subscriptions' folder for {user.username}")
        
        db.session.commit()
        
        # Create public quizzes
        print("\nCreating public quizzes...")
        quiz_count = 0
        word_count = 0
        
        for i, quiz_data in enumerate(test_quizzes):
            # Assign quiz to user in round-robin fashion
            user = created_users[i % len(created_users)]
            
            # Check if quiz already exists for this user
            existing_quiz = Quiz.query.filter_by(
                name=quiz_data['name'],
                user_id=user.id
            ).first()
            
            if existing_quiz:
                print(f"  - Quiz '{quiz_data['name']}' already exists for {user.username}, skipping...")
                continue
            
            # Create quiz
            new_quiz = Quiz(
                name=quiz_data['name'],
                user_id=user.id,
                source_language=quiz_data['source_language'],
                target_language=quiz_data['target_language'],
                is_public=True,  # Make it public
                processing_status='completed'
            )
            db.session.add(new_quiz)
            db.session.flush()  # Get the quiz ID
            
            # Add words to quiz
            for word_data in quiz_data['words']:
                new_word = Word(
                    lemma=word_data['lemma'],
                    translation=word_data['translation'],
                    quiz_id=new_quiz.id
                )
                db.session.add(new_word)
                word_count += 1
            
            quiz_count += 1
            print(f"  ✓ Created quiz '{quiz_data['name']}' for {user.username} ({len(quiz_data['words'])} words)")
        
        db.session.commit()
        
        print(f"\n✓ Test data creation complete!")
        print(f"  - Users: {len(created_users)}")
        print(f"  - Public quizzes: {quiz_count}")
        print(f"  - Words: {word_count}")
        print(f"\nTest user credentials:")
        for user_data in test_users:
            print(f"  - Username: {user_data['username']}, Password: {user_data['password']}")

if __name__ == '__main__':
    print("Creating test users and public quizzes...")
    print("=" * 50)
    create_test_data()
    print("=" * 50)
    print("Done!")
