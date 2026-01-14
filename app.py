from flask import Flask, render_template, url_for, redirect, request, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from flask_cors import CORS
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length, ValidationError
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from gptcaller import get_gpt_caller, convert_to_word_class
from gptcaller_polish import get_gpt_caller_polish, convert_to_word_class as convert_to_word_class_polish
from gptcaller_prompt import get_gpt_caller_prompt
from utils import parse_tags_from_string, words_to_dict_list, sentences_to_dict_list

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SECRET_KEY"] = "thisisasecretkey"
bcrypt = Bcrypt(app)
db = SQLAlchemy(app)
# Enable CORS for mobile app
CORS(app, supports_credentials=True, origins=["*"])

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    quiz_form = QuizForm()

    if quiz_form.validate_on_submit():
        new_quiz = Quiz(name=quiz_form.name.data, user_id=current_user.id)
        db.session.add(new_quiz)
        db.session.commit()
        flash('Quiz created successfully!', 'success')
        return redirect(url_for('dashboard'))

    # Get all quizzes for the current user
    quizzes = Quiz.query.filter_by(user_id=current_user.id).order_by(Quiz.created_at.desc()).all()
    return render_template("dashboard.html", quizzes=quizzes, quiz_form=quiz_form)




def process_text_import_background(quiz_id, content, language, context=""):
    """Background function to process any text and extract vocabulary using GPT."""
    with app.app_context():
        quiz = db.session.get(Quiz, quiz_id)
        if not quiz:
            return
        
        try:
            # Update status to processing
            quiz.processing_status = 'processing'
            quiz.processing_message = 'Extracting vocabulary with AI...'
            db.session.commit()
            
            # Quiz languages:
            # source_language = what user knows (English/Swedish)
            # target_language = what user is learning/practicing (ALWAYS Ukrainian/Polish)
            
            # Get learning direction from quiz
            user_knows = quiz.source_language or "English"  # What user knows
            user_learning = quiz.target_language or "Ukrainian"  # What user is learning (ALWAYS Ukrainian/Polish)
            
            # Use appropriate GPT caller based on target language
            # Polish uses a specialized caller tailored for Polish textbook content
            is_polish = user_learning == "Polish"
            if is_polish:
                caller = get_gpt_caller_polish()
                word_converter = convert_to_word_class_polish
            else:
                # Ukrainian and other languages use the standard caller
                caller = get_gpt_caller()
                word_converter = convert_to_word_class
            
            # Determine word pair direction based on text language
            slavic_languages = ["Polish", "Ukrainian", "Russian", "Czech", "Slovak", "Bulgarian", "Serbian", "Croatian", "Slovenian"]
            text_is_slavic = language in slavic_languages
            
            # ALWAYS extract word pairs in the learning direction:
            # - If text is Ukrainian/Polish → extract: Ukrainian/Polish words → English/Swedish translations
            # - If text is English/Swedish → extract: English/Swedish words → Ukrainian/Polish translations
            # The target_language (Ukrainian/Polish) is ALWAYS what we're practicing
            if text_is_slavic:
                # Text is in the language being learned (Ukrainian/Polish)
                # Extract: target_language words → source_language translations
                gpt_source_lang = user_learning  # Ukrainian/Polish word (lemma) - ALWAYS generate variants for this
                gpt_target_lang = user_knows  # English/Swedish translation
            else:
                # Text is in the language user knows (English/Swedish)
                # Extract: source_language words → target_language translations
                gpt_source_lang = user_knows  # English/Swedish word (lemma) - no variants
                gpt_target_lang = user_learning  # Ukrainian/Polish translation - but variants generated for target language words
            
            # Use GPT to extract vocabulary from the text
            extracted = caller.extract_vocabulary_from_text(
                content, 
                language, 
                context,
                source_language=gpt_source_lang,
                target_language=gpt_target_lang
            )
            
            quiz.processing_message = f'Found {len(extracted.words)} words, {len(extracted.sentences)} sentences. Processing...'
            db.session.commit()
            
            # Check for cancellation after extraction
            db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return
            
            # Save sentences and create word-to-sentence mapping
            saved_sentences = []
            for sent in extracted.sentences:
                new_sentence = Sentence(
                    text=sent.text,
                    translation=sent.translation,
                    quiz_id=quiz_id
                )
                db.session.add(new_sentence)
                saved_sentences.append({
                    'text': sent.text,
                    'translation': sent.translation
                })
            db.session.commit()
            
            # Create mapping of words to sentences they appear in
            # This will be used to assign example sentences from the text
            word_to_sentence_map = {}
            for word_item in extracted.words:
                lemma = word_item.lemma.lower()
                # Check if this word appears in any sentence
                for sent in saved_sentences:
                    sent_text_lower = sent['text'].lower()
                    # For phrases (multi-word), check if the phrase appears in the sentence
                    if ' ' in lemma or len(lemma.split()) > 1:
                        # It's a phrase - check if the phrase appears in the sentence
                        if lemma in sent_text_lower:
                            # Format: "sentence" — "translation"
                            example = f'"{sent["text"]}" — "{sent["translation"]}"'
                            if lemma not in word_to_sentence_map:
                                word_to_sentence_map[lemma] = example
                            break  # Use first matching sentence
                    else:
                        # Single word - use word boundary matching
                        # Also check for the word in different forms (as substring for flexibility)
                        word_pattern = r'\b' + re.escape(lemma) + r'\b'
                        if re.search(word_pattern, sent_text_lower):
                            # Format: "sentence" — "translation"
                            example = f'"{sent["text"]}" — "{sent["translation"]}"'
                            if lemma not in word_to_sentence_map:
                                word_to_sentence_map[lemma] = example
                            break  # Use first matching sentence
            
            # Process words - get detailed analysis for each in parallel
            max_workers = 5
            words_added = 0
            
            def analyze_word(word_item):
                """Get detailed analysis for a single word."""
                try:
                    # Find sentences from the text where this word appears
                    lemma_lower = word_item.lemma.lower()
                    word_sentences = []
                    for sent in saved_sentences:
                        if lemma_lower in sent['text'].lower():
                            word_sentences.append(f'"{sent["text"]}" — "{sent["translation"]}"')
                    
                    # Use the same language detection logic as extraction
                    analysis = caller.generate_word_analysis(
                        lemma=word_item.lemma,
                        translation=word_item.translation,
                        language=language,
                        context=context,
                        sentence_context=word_sentences[:3] if word_sentences else None,  # Pass up to 3 sentences
                        source_language=gpt_source_lang,
                        target_language=gpt_target_lang
                    )
                    
                    if analysis.is_irrelevant:
                        return {'skip': True}
                    
                    word_data = word_converter(analysis, word_item.lemma)
                    return {
                        'skip': False,
                        'lemma': word_item.lemma,
                        'translation': word_item.translation,
                        'notes': word_item.notes,
                        'word_data': word_data
                    }
                except Exception as e:
                    print(f"Error analyzing word {word_item.lemma}: {e}")
                    # Return basic data without detailed analysis
                    return {
                        'skip': False,
                        'lemma': word_item.lemma,
                        'translation': word_item.translation,
                        'notes': word_item.notes,
                        'word_data': None
                    }
            
            quiz.processing_message = f'Analyzing {len(extracted.words)} words in detail...'
            db.session.commit()
            
            # Check for cancellation before starting word analysis
            db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return
            
            word_results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_word = {
                    executor.submit(analyze_word, word_item): word_item
                    for word_item in extracted.words
                }
                
                completed = 0
                for future in as_completed(future_to_word):
                    # Check for cancellation periodically
                    db.session.refresh(quiz)
                    if quiz.processing_status == 'cancelled':
                        # Cancel remaining futures
                        for f in future_to_word:
                            f.cancel()
                        return
                    
                    result = future.result()
                    word_results.append(result)
                    completed += 1
                    quiz.processing_message = f'Analyzing words ({completed}/{len(extracted.words)})...'
                    db.session.commit()
            
            # Check for cancellation before saving words
            db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return
            
            # Save word results
            for result in word_results:
                if result.get('skip'):
                    continue
                
                new_word = Word(
                    lemma=result['lemma'],
                    translation=result['translation'],
                    quiz_id=quiz_id
                )
                
                word_data = result.get('word_data')
                if word_data and word_data.get('properties'):
                    new_word.set_properties(word_data['properties'])
                else:
                    new_word.set_properties({})
                
                # Priority for example sentence:
                # 1. Sentence from the text (if word appears in any extracted sentence)
                # 2. Notes from extraction
                # 3. Example sentence from GPT analysis
                lemma_lower = result['lemma'].lower()
                if lemma_lower in word_to_sentence_map:
                    new_word.example_sentence = word_to_sentence_map[lemma_lower]
                elif result.get('notes'):
                    new_word.example_sentence = result['notes']
                elif word_data and word_data.get('example_sentence'):
                    new_word.example_sentence = word_data['example_sentence']
                
                # Set explanation from GPT analysis
                if word_data and word_data.get('explanation'):
                    new_word.explanation = word_data['explanation']
                
                db.session.add(new_word)
                db.session.flush()
                
                # Add variants if available
                if word_data and word_data.get('variants'):
                    for variant_data in word_data['variants']:
                        new_variant = Variant(
                            value=variant_data['value'],
                            translation=variant_data['translation'],
                            word_id=new_word.id
                        )
                        if variant_data.get('tags'):
                            new_variant.set_tags(variant_data['tags'])
                        db.session.add(new_variant)
                
                words_added += 1
            
            db.session.commit()
            
            # Mark as completed
            quiz.processing_status = 'completed'
            quiz.processing_message = f'Completed! {words_added} words and {len(extracted.sentences)} sentences.'
            db.session.commit()
            
        except Exception as e:
            print(f"Error processing quiz {quiz_id}: {e}")
            import traceback
            traceback.print_exc()
            quiz.processing_status = 'error'
            quiz.processing_message = f'Error: {str(e)[:100]}'
            db.session.commit()


def process_prompt_import_background(quiz_id, prompt, source_language, target_language, context=""):
    """Background function to generate vocabulary from a prompt and process it."""
    with app.app_context():
        quiz = db.session.get(Quiz, quiz_id)
        if not quiz:
            return
        
        try:
            # Update status
            quiz.processing_status = 'processing'
            quiz.processing_message = 'Generating vocabulary from prompt...'
            db.session.commit()
            
            # Stage 1: Generate word pairs from prompt
            prompt_caller = get_gpt_caller_prompt()
            prompt_vocab = prompt_caller.generate_vocabulary_from_prompt(
                prompt=prompt,
                source_language=target_language,  # The language being learned (Polish/Ukrainian)
                target_language=source_language   # The language user knows (English/Swedish)
            )
            
            quiz.processing_message = f'Generated {len(prompt_vocab.words)} words. Analyzing in detail...'
            db.session.commit()
            
            # Check for cancellation after prompt generation
            db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return
            
            # Stage 2: Use appropriate caller for full analysis
            is_polish = target_language == "Polish"
            if is_polish:
                analysis_caller = get_gpt_caller_polish()
                word_converter = convert_to_word_class_polish
            else:
                analysis_caller = get_gpt_caller()
                word_converter = convert_to_word_class
            
            # Process each word pair through full analysis
            max_workers = 5
            word_results = []
            
            def analyze_word(word_pair):
                """Get detailed analysis for a word pair."""
                try:
                    analysis = analysis_caller.generate_word_analysis(
                        lemma=word_pair.lemma,
                        translation=word_pair.translation,
                        language=target_language,
                        context=context,
                        source_language=target_language,
                        target_language=source_language
                    )
                    
                    if analysis.is_irrelevant:
                        return {'skip': True}
                    
                    word_data = word_converter(analysis, word_pair.lemma)
                    return {
                        'skip': False,
                        'lemma': word_pair.lemma,
                        'translation': word_pair.translation,
                        'notes': word_pair.notes,
                        'word_data': word_data
                    }
                except Exception as e:
                    print(f"Error analyzing word {word_pair.lemma}: {e}")
                    return {
                        'skip': False,
                        'lemma': word_pair.lemma,
                        'translation': word_pair.translation,
                        'notes': word_pair.notes,
                        'word_data': None
                    }
            
            quiz.processing_message = f'Analyzing {len(prompt_vocab.words)} words in detail...'
            db.session.commit()
            
            # Process words in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_word = {
                    executor.submit(analyze_word, word_pair): word_pair
                    for word_pair in prompt_vocab.words
                }
                
                completed = 0
                for future in as_completed(future_to_word):
                    # Check for cancellation periodically
                    db.session.refresh(quiz)
                    if quiz.processing_status == 'cancelled':
                        for f in future_to_word:
                            f.cancel()
                        return
                    
                    result = future.result()
                    word_results.append(result)
                    completed += 1
                    quiz.processing_message = f'Analyzing words ({completed}/{len(prompt_vocab.words)})...'
                    db.session.commit()
            
            # Check for cancellation before saving words
            db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return
            
            # Save words to database (similar to text import)
            words_added = 0
            for result in word_results:
                if result.get('skip'):
                    continue
                
                new_word = Word(
                    lemma=result['lemma'],
                    translation=result['translation'],
                    quiz_id=quiz_id
                )
                
                word_data = result.get('word_data')
                if word_data and word_data.get('properties'):
                    new_word.set_properties(word_data['properties'])
                else:
                    new_word.set_properties({})
                
                # Use notes from prompt generation if available
                if result.get('notes'):
                    new_word.example_sentence = result['notes']
                elif word_data and word_data.get('example_sentence'):
                    new_word.example_sentence = word_data['example_sentence']
                
                # Set explanation from GPT analysis
                if word_data and word_data.get('explanation'):
                    new_word.explanation = word_data['explanation']
                
                db.session.add(new_word)
                db.session.flush()
                
                # Add variants if available
                if word_data and word_data.get('variants'):
                    for variant_data in word_data['variants']:
                        new_variant = Variant(
                            value=variant_data['value'],
                            translation=variant_data['translation'],
                            word_id=new_word.id
                        )
                        if variant_data.get('tags'):
                            new_variant.set_tags(variant_data['tags'])
                        db.session.add(new_variant)
                
                words_added += 1
            
            db.session.commit()
            
            # Mark as completed
            quiz.processing_status = 'completed'
            quiz.processing_message = f'Completed! {words_added} words generated.'
            db.session.commit()
            
        except Exception as e:
            print(f"Error processing prompt for quiz {quiz_id}: {e}")
            quiz.processing_status = 'error'
            quiz.processing_message = f'Error: {str(e)[:100]}'
            db.session.commit()


# Backward compatibility alias
def process_song_quiz_background(quiz_id, lyrics, language, context=""):
    """Legacy function - calls the new generalized version."""
    process_text_import_background(quiz_id, lyrics, language, context)


@app.route("/create-song-quiz", methods=["GET", "POST"])
@app.route("/import-text", methods=["GET", "POST"])
@login_required
def create_song_quiz():
    form = TextImportForm()
    
    if form.validate_on_submit():
        # Create the quiz immediately with pending status
        new_quiz = Quiz(
            name=form.name.data,
            user_id=current_user.id,
            is_song_quiz=True,  # All imported quizzes can have sentences
            processing_status='pending',
            processing_message='Queued for processing...'
        )
        db.session.add(new_quiz)
        db.session.commit()
        
        # Start background processing
        content = form.content.data
        language = form.language.data
        context = form.context.data.strip() if form.context.data else ""
        thread = threading.Thread(
            target=process_text_import_background,
            args=(new_quiz.id, content, language, context),
            daemon=True
        )
        thread.start()
        
        flash('Quiz created! Processing in the background. You can check the dashboard for progress.', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template("create_song_quiz.html", form=form)


@app.route("/quiz/<int:quiz_id>", methods=["GET", "POST"])
@login_required
def quiz_detail(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)

    # Check if quiz exists and belongs to current user
    if not quiz or quiz.user_id != current_user.id:
        flash('Quiz not found or access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    # If quiz is still processing, show processing page
    if quiz.processing_status and quiz.processing_status != 'completed':
        from flask_wtf import FlaskForm
        word_form = WordForm()
        variant_form = VariantForm()
        return render_template("quiz_detail.html", quiz=quiz, words=[], word_form=word_form, variant_form=variant_form)

    word_form = WordForm()

    if word_form.validate_on_submit():
        # Get lemma and translation (at least one must be provided)
        lemma = word_form.lemma.data.strip() if word_form.lemma.data else ""
        translation = word_form.translation.data.strip() if word_form.translation.data else ""
        
        # Use GPT to automatically determine properties and other fields
        try:
            caller = get_gpt_caller()
            # Get word analysis from GPT (will determine pos, properties, etc.)
            # GPT can handle cases where only lemma or only translation is provided
            
            analysis = caller.generate_word_analysis(
                lemma=lemma,
                translation=translation,
                language="unknown"  # Could be made configurable per quiz
            )
            
            # Get the actual lemma from GPT analysis if it wasn't provided
            # GPT should provide the lemma in the translations list when only translation is given
            if not lemma:
                # If only translation was provided, GPT should determine the lemma
                # We'll use the first translation as a fallback, but GPT should provide the actual lemma
                lemma = analysis.translations[0] if analysis.translations else translation
            
            # Get the actual translation if it wasn't provided
            if not translation and analysis.translations:
                translation = analysis.translations[0]
            
            # Create word with determined lemma and translation
            new_word = Word(
                lemma=lemma,
                translation=translation,
                quiz_id=quiz_id
            )
            
            # Convert to Word class format
            word_data = convert_to_word_class(analysis, lemma)
            
            # Set properties from GPT analysis
            if word_data['properties']:
                new_word.set_properties(word_data['properties'])
            
            # Set example sentence if available
            if word_data.get('example_sentence'):
                new_word.example_sentence = word_data['example_sentence']
            
            # Set explanation if available
            if word_data.get('explanation'):
                new_word.explanation = word_data['explanation']
            
            db.session.add(new_word)
            db.session.flush()  # Get the word ID

            # Add variants from GPT analysis
            for variant_data in word_data['variants']:
                new_variant = Variant(
                    value=variant_data['value'],
                    translation=variant_data['translation'],
                    word_id=new_word.id
                )
                # Set tags if available
                if variant_data.get('tags'):
                    new_variant.set_tags(variant_data['tags'])
                db.session.add(new_variant)

            db.session.commit()
            flash('Word added successfully with GPT-generated properties and variants!', 'success')

        except Exception as e:
            # If GPT fails, we need at least lemma and translation to create the word
            # If both were provided, create the word without GPT analysis
            if lemma and translation:
                new_word = Word(
                    lemma=lemma,
                    translation=translation,
                    quiz_id=quiz_id
                )
                new_word.set_properties({})  # Empty properties as fallback
                db.session.add(new_word)
                db.session.commit()
                flash('Word added successfully. (GPT analysis unavailable - properties not set)', 'warning')
            else:
                # If only one was provided and GPT fails, we can't create the word
                flash(f'Error: Could not analyze word. GPT analysis required when only one field is provided. {str(e)}', 'error')
                return redirect(url_for('quiz_detail', quiz_id=quiz_id))

        return redirect(url_for('quiz_detail', quiz_id=quiz_id))

    words = Word.query.filter_by(quiz_id=quiz_id).all()
    # Load variants for each word
    for word in words:
        word.variants_list = Variant.query.filter_by(word_id=word.id).all()

    variant_form = VariantForm()
    return render_template("quiz_detail.html", quiz=quiz, words=words, word_form=word_form, variant_form=variant_form)


@app.route("/quiz/<int:quiz_id>/delete", methods=["POST"])
@login_required
def delete_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)

    if quiz and quiz.user_id == current_user.id:
        db.session.delete(quiz)
        db.session.commit()
        flash('Quiz deleted successfully!', 'success')
    else:
        flash('Quiz not found or access denied.', 'error')

    return redirect(url_for('dashboard'))


@app.route("/word/<int:word_id>/delete", methods=["POST"])
@login_required
def delete_word(word_id):
    word = db.session.get(Word, word_id)

    if word:
        quiz = word.quiz
        if quiz and quiz.user_id == current_user.id:
            db.session.delete(word)
            db.session.commit()
            flash('Word deleted successfully!', 'success')
            return redirect(url_for('quiz_detail', quiz_id=quiz.id))

    flash('Word not found or access denied.', 'error')
    return redirect(url_for('dashboard'))


@app.route("/word/<int:word_id>/variant", methods=["POST"])
@login_required
def add_variant(word_id):
    word = db.session.get(Word, word_id)

    if not word:
        flash('Word not found.', 'error')
        return redirect(url_for('dashboard'))

    quiz = word.quiz
    if quiz.user_id != current_user.id:
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))

    variant_form = VariantForm()

    if variant_form.validate_on_submit():
        # Parse tags from string format "key1=value1,key2=value2"
        tags_dict = parse_tags_from_string(variant_form.tags.data or "")

        new_variant = Variant(
            value=variant_form.value.data,
            translation=variant_form.translation.data,
            word_id=word_id
        )
        new_variant.set_tags(tags_dict)
        db.session.add(new_variant)
        db.session.commit()
        flash('Variant added successfully!', 'success')
        return redirect(url_for('quiz_detail', quiz_id=quiz.id))

    flash('Invalid variant data.', 'error')
    return redirect(url_for('quiz_detail', quiz_id=quiz.id))


@app.route("/variant/<int:variant_id>/delete", methods=["POST"])
@login_required
def delete_variant(variant_id):
    variant = db.session.get(Variant, variant_id)

    if variant:
        word = variant.word
        quiz = word.quiz
        if quiz and quiz.user_id == current_user.id:
            db.session.delete(variant)
            db.session.commit()
            flash('Variant deleted successfully!', 'success')
            return redirect(url_for('quiz_detail', quiz_id=quiz.id))

    flash('Variant not found or access denied.', 'error')
    return redirect(url_for('dashboard'))


@app.route("/sentence/<int:sentence_id>/delete", methods=["POST"])
@login_required
def delete_sentence(sentence_id):
    sentence = db.session.get(Sentence, sentence_id)

    if sentence:
        quiz = sentence.quiz
        if quiz and quiz.user_id == current_user.id:
            db.session.delete(sentence)
            db.session.commit()
            flash('Sentence deleted successfully!', 'success')
            return redirect(url_for('quiz_detail', quiz_id=quiz.id))

    flash('Sentence not found or access denied.', 'error')
    return redirect(url_for('dashboard'))


@app.route("/quiz/<int:quiz_id>/status")
@login_required
def quiz_status(quiz_id):
    """Get the processing status of a quiz (for AJAX polling)."""
    quiz = db.session.get(Quiz, quiz_id)
    
    if not quiz or quiz.user_id != current_user.id:
        return jsonify({'error': 'Quiz not found'}), 404
    
    return jsonify({
        'status': quiz.processing_status,
        'message': quiz.processing_message or ''
    })


@app.route("/quiz/<int:quiz_id>/practice")
@login_required
def practice_quiz(quiz_id):
    quiz = db.session.get(Quiz, quiz_id)
    
    if not quiz or quiz.user_id != current_user.id:
        flash('Quiz not found or access denied.', 'error')
        return redirect(url_for('dashboard'))
    
    mode = request.args.get('mode', 'words')  # 'words' or 'sentences'
    
    if mode == 'sentences':
        sentences = Sentence.query.filter_by(quiz_id=quiz_id).all()
        # Convert sentences to dicts for JSON serialization
        sentences_data = sentences_to_dict_list(sentences)
        return render_template("practice_sentences.html", quiz=quiz, sentences=sentences_data)
    else:
        words = Word.query.filter_by(quiz_id=quiz_id).all()
        # Convert words to dicts for JSON serialization
        words_data = words_to_dict_list(words)
        return render_template("practice_words.html", quiz=quiz, words=words_data)


@app.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(80), nullable=False)
    quizzes = db.relationship('Quiz', backref='user', lazy=True, cascade='all, delete-orphan')
    folders = db.relationship('Folder', backref='user', lazy=True, cascade='all, delete-orphan')


class Folder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('folder.id'), nullable=True)  # For nested folders
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    quizzes = db.relationship('Quiz', backref='folder', lazy=True, cascade='all, delete-orphan')
    subfolders = db.relationship('Folder', backref=db.backref('parent', remote_side=[id]), lazy=True, cascade='all, delete-orphan')


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
    words = db.relationship('Word', backref='quiz', lazy=True, cascade='all, delete-orphan')
    sentences = db.relationship('Sentence', backref='quiz', lazy=True, cascade='all, delete-orphan')


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


class RegisterForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Register")

    def validate_username(self, username):
        existing_user_username = User.query.filter_by(
            username=username.data).first()
        if existing_user_username:
            raise ValidationError(
                "User already exists"
            )


class LoginForm(FlaskForm):
    username = StringField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Username"})
    password = PasswordField(validators=[InputRequired(), Length(min=4, max=20)], render_kw={"placeholder": "Password"})
    submit = SubmitField("Login")


class QuizForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=1, max=100)], render_kw={"placeholder": "Quiz Name"})
    submit = SubmitField("Create Quiz")


class TextImportForm(FlaskForm):
    name = StringField(validators=[InputRequired(), Length(min=1, max=100)], render_kw={"placeholder": "Quiz Name"})
    language = StringField(validators=[InputRequired(), Length(min=1, max=50)], render_kw={"placeholder": "Language (e.g., Ukrainian, Polish)"})
    content = TextAreaField(validators=[InputRequired()], render_kw={"placeholder": "Paste any text here - song lyrics, word lists, textbook excerpts, articles...", "rows": 15})
    context = TextAreaField(validators=[], render_kw={"placeholder": "Optional: Additional context to help with accurate translations...", "rows": 3})
    submit = SubmitField("Create Quiz")


# Keep old form name for backward compatibility
SongQuizForm = TextImportForm


class WordForm(FlaskForm):
    lemma = StringField(validators=[Length(min=0, max=200)], render_kw={"placeholder": "Word (lemma) - optional"})
    translation = StringField(validators=[Length(min=0, max=200)], render_kw={"placeholder": "Translation - optional"})
    submit = SubmitField("Add Word")
    
    def validate(self, extra_validators=None):
        """Ensure at least one of lemma or translation is provided."""
        if not super().validate(extra_validators):
            return False
        
        if not self.lemma.data.strip() and not self.translation.data.strip():
            self.lemma.errors.append("At least one of lemma or translation must be provided.")
            return False
        
        return True


class VariantForm(FlaskForm):
    value = StringField(validators=[InputRequired(), Length(min=1, max=200)], render_kw={"placeholder": "Variant form"})
    translation = StringField(validators=[InputRequired(), Length(min=1, max=200)],
                              render_kw={"placeholder": "Translation"})
    tags = StringField(render_kw={"placeholder": "Tags (e.g., case=gen,number=sg)"})
    submit = SubmitField("Add Variant")


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        new_user = User(username=form.username.data, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            if bcrypt.check_password_hash(user.password, form.password.data):
                login_user(user)
                return redirect(url_for('dashboard'))

    return render_template("login.html", form=form)


# =============================================================================
# JSON API ENDPOINTS FOR MOBILE APP
# =============================================================================

@app.route("/api/login", methods=["POST"])
def api_login():
    """JSON API endpoint for login."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400
    
    user = User.query.filter_by(username=username).first()
    if user and bcrypt.check_password_hash(user.password, password):
        login_user(user)
        return jsonify({
            'success': True,
            'user': {'id': user.id, 'username': user.username}
        })
    
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@app.route("/api/register", methods=["POST"])
def api_register():
    """JSON API endpoint for registration."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400
    
    if len(username) < 4 or len(password) < 4:
        return jsonify({'success': False, 'message': 'Username and password must be at least 4 characters'}), 400
    
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({'success': False, 'message': 'Username already exists'}), 400
    
    hashed_password = bcrypt.generate_password_hash(password)
    new_user = User(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Registration successful'})


@app.route("/api/logout", methods=["POST"])
@login_required
def api_logout():
    """JSON API endpoint for logout."""
    logout_user()
    return jsonify({'success': True})


@app.route("/api/me", methods=["GET"])
def api_me():
    """Get current authenticated user."""
    if current_user.is_authenticated:
        return jsonify({
            'success': True,
            'user': {'id': current_user.id, 'username': current_user.username}
        })
    return jsonify({'success': False}), 401


@app.route("/api/quizzes", methods=["GET", "POST"])
@login_required
def api_quizzes():
    """Get all quizzes or create a new quiz."""
    if request.method == "GET":
        # Only return quizzes that are NOT in folders (root level quizzes)
        quizzes = Quiz.query.filter_by(user_id=current_user.id, folder_id=None).order_by(Quiz.created_at.desc()).all()
        return jsonify({
            'quizzes': [
                {
                    'id': q.id,
                    'name': q.name,
                    'user_id': q.user_id,
                    'created_at': q.created_at.isoformat(),
                    'is_song_quiz': True,  # All quizzes support sentences now
                    'processing_status': q.processing_status,
                    'processing_message': q.processing_message,
                    'source_language': q.source_language,
                    'target_language': q.target_language,
                    'words': [{'id': w.id, 'lemma': w.lemma, 'translation': w.translation} for w in q.words]
                }
                for q in quizzes
            ]
        })
    
    # POST - create new quiz
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Quiz name required'}), 400
    
    source_language = data.get('source_language', '').strip() or None
    target_language = data.get('target_language', '').strip() or None
    prompt = data.get('prompt', '').strip() or None
    
    new_quiz = Quiz(
        name=data['name'],
        user_id=current_user.id,
        source_language=source_language,
        target_language=target_language
    )
    db.session.add(new_quiz)
    db.session.commit()
    
    # If prompt provided, start background processing
    if prompt and source_language and target_language:
        new_quiz.processing_status = 'pending'
        new_quiz.processing_message = 'Queued for processing...'
        db.session.commit()
        
        context = data.get('context', '').strip() or ""
        thread = threading.Thread(
            target=process_prompt_import_background,
            args=(new_quiz.id, prompt, source_language, target_language, context),
            daemon=True
        )
        thread.start()
    
    return jsonify({
        'quiz': {
            'id': new_quiz.id,
            'name': new_quiz.name,
            'user_id': new_quiz.user_id,
            'created_at': new_quiz.created_at.isoformat(),
            'is_song_quiz': True,  # All quizzes support sentences
            'processing_status': new_quiz.processing_status,
            'processing_message': new_quiz.processing_message,
            'source_language': new_quiz.source_language,
            'target_language': new_quiz.target_language,
            'words': []
        }
    }), 201


@app.route("/api/quiz/<int:quiz_id>", methods=["GET", "DELETE"])
@login_required
def api_quiz_detail(quiz_id):
    """Get quiz details or delete a quiz."""
    quiz = db.session.get(Quiz, quiz_id)
    
    if not quiz or quiz.user_id != current_user.id:
        return jsonify({'error': 'Quiz not found'}), 404
    
    if request.method == "DELETE":
        db.session.delete(quiz)
        db.session.commit()
        return jsonify({'success': True})
    
    # GET
    words = Word.query.filter_by(quiz_id=quiz_id).all()
    words_data = []
    for word in words:
        variants = Variant.query.filter_by(word_id=word.id).all()
        words_data.append({
            'id': word.id,
            'lemma': word.lemma,
            'translation': word.translation,
            'properties': word.get_properties(),
            'example_sentence': word.example_sentence,
            'explanation': word.explanation,
            'quiz_id': word.quiz_id,
            'variants': [
                {
                    'id': v.id,
                    'value': v.value,
                    'translation': v.translation,
                    'tags': v.get_tags(),
                    'word_id': v.word_id
                }
                for v in variants
            ],
            # Anki spaced repetition fields
            'ease_factor': word.ease_factor or 2.5,
            'interval': word.interval or 0,
            'repetitions': word.repetitions or 0,
            'due_date': word.due_date.isoformat() if word.due_date else datetime.utcnow().isoformat()
        })
    
    sentences = Sentence.query.filter_by(quiz_id=quiz_id).all()
    
    return jsonify({
        'quiz': {
            'id': quiz.id,
            'name': quiz.name,
            'user_id': quiz.user_id,
            'created_at': quiz.created_at.isoformat(),
            'is_song_quiz': True,  # All quizzes support sentences
            'processing_status': quiz.processing_status,
            'processing_message': quiz.processing_message,
            'source_language': quiz.source_language,
            'target_language': quiz.target_language,
        },
        'words': words_data,
        'sentences': [
            {
                'id': s.id,
                'text': s.text,
                'translation': s.translation,
                'quiz_id': s.quiz_id
            }
            for s in sentences
        ]
    })


@app.route("/api/quiz/<int:quiz_id>/words", methods=["POST"])
@login_required
def api_add_word(quiz_id):
    """Add a word to a quiz."""
    quiz = db.session.get(Quiz, quiz_id)
    
    if not quiz or quiz.user_id != current_user.id:
        return jsonify({'error': 'Quiz not found'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    lemma = data.get('lemma', '').strip()
    translation = data.get('translation', '').strip()
    
    if not lemma and not translation:
        return jsonify({'error': 'At least lemma or translation required'}), 400
    
    # Use GPT to analyze the word
    try:
        caller = get_gpt_caller()
        # Get source and target languages from quiz
        source_lang = quiz.source_language or "unknown"
        target_lang = quiz.target_language or "English"
        
        analysis = caller.generate_word_analysis(
            lemma=lemma,
            translation=translation,
            language=source_lang,
            source_language=source_lang,
            target_language=target_lang
        )
        
        if not lemma:
            lemma = analysis.translations[0] if analysis.translations else translation
        if not translation and analysis.translations:
            translation = analysis.translations[0]
        
        new_word = Word(
            lemma=lemma,
            translation=translation,
            quiz_id=quiz_id
        )
        
        word_data = convert_to_word_class(analysis, lemma)
        if word_data['properties']:
            new_word.set_properties(word_data['properties'])
        if word_data.get('example_sentence'):
            new_word.example_sentence = word_data['example_sentence']
        
        db.session.add(new_word)
        db.session.flush()
        
        # Add variants
        for variant_data in word_data['variants']:
            new_variant = Variant(
                value=variant_data['value'],
                translation=variant_data['translation'],
                word_id=new_word.id
            )
            if variant_data.get('tags'):
                new_variant.set_tags(variant_data['tags'])
            db.session.add(new_variant)
        
        db.session.commit()
        
        # Return the created word with variants
        variants = Variant.query.filter_by(word_id=new_word.id).all()
        return jsonify({
            'word': {
                'id': new_word.id,
                'lemma': new_word.lemma,
                'translation': new_word.translation,
                'properties': new_word.get_properties(),
                'example_sentence': new_word.example_sentence,
                'explanation': new_word.explanation,
                'quiz_id': new_word.quiz_id,
                'variants': [
                    {
                        'id': v.id,
                        'value': v.value,
                        'translation': v.translation,
                        'tags': v.get_tags(),
                        'word_id': v.word_id
                    }
                    for v in variants
                ]
            }
        }), 201
        
    except Exception as e:
        if lemma and translation:
            new_word = Word(
                lemma=lemma,
                translation=translation,
                quiz_id=quiz_id
            )
            new_word.set_properties({})
            db.session.add(new_word)
            db.session.commit()
            
            return jsonify({
                'word': {
                    'id': new_word.id,
                    'lemma': new_word.lemma,
                    'translation': new_word.translation,
                    'properties': {},
                    'example_sentence': None,
                    'quiz_id': new_word.quiz_id,
                    'variants': []
                },
                'warning': 'GPT analysis unavailable'
            }), 201
        
        return jsonify({'error': f'Failed to analyze word: {str(e)}'}), 500


@app.route("/api/word/<int:word_id>", methods=["GET", "DELETE", "PUT"])
@login_required
def api_word_detail(word_id):
    """Get, update, or delete a word."""
    word = db.session.get(Word, word_id)
    
    if not word:
        return jsonify({'error': 'Word not found'}), 404
    
    quiz = word.quiz
    if quiz.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    if request.method == "DELETE":
        db.session.delete(word)
        db.session.commit()
        return jsonify({'success': True})
    
    if request.method == "PUT":
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        lemma = data.get('lemma')
        translation = data.get('translation')
        example_sentence = data.get('example_sentence')
        explanation = data.get('explanation')
        # Properties are read-only - ignore if provided
        variants_payload = data.get('variants')
        
        if lemma is not None:
            word.lemma = lemma.strip()
        if translation is not None:
            word.translation = translation.strip()
        if example_sentence is not None:
            word.example_sentence = example_sentence.strip() if example_sentence else None
        if explanation is not None:
            word.explanation = explanation.strip() if explanation else None
        # Properties are read-only - don't update them
        
        db.session.commit()
        
        # Replace variants if provided
        if variants_payload is not None and isinstance(variants_payload, list):
            # Get existing variants to preserve their tags
            existing_variants = {v.id: v for v in Variant.query.filter_by(word_id=word.id).all()}
            
            # Delete existing variants
            Variant.query.filter_by(word_id=word.id).delete()
            db.session.flush()
            
            for variant in variants_payload:
                value = variant.get('value')
                translation_val = variant.get('translation')
                variant_id = variant.get('id')
                
                if not value or not translation_val:
                    continue
                
                new_variant = Variant(
                    value=value,
                    translation=translation_val,
                    word_id=word.id
                )
                
                # Preserve tags from existing variant if it exists, otherwise use empty tags
                # Tags are read-only - don't accept them from the request
                if variant_id and variant_id in existing_variants:
                    existing_variant = existing_variants[variant_id]
                    existing_tags = existing_variant.get_tags()
                    if existing_tags:
                        new_variant.set_tags(existing_tags)
                
                db.session.add(new_variant)
            
            db.session.commit()
    
    # GET
    variants = Variant.query.filter_by(word_id=word.id).all()
    return jsonify({
        'word': {
            'id': word.id,
            'lemma': word.lemma,
            'translation': word.translation,
            'properties': word.get_properties(),
            'example_sentence': word.example_sentence,
            'explanation': word.explanation,
            'quiz_id': word.quiz_id,
            # Anki spaced repetition fields
            'ease_factor': word.ease_factor or 2.5,
            'interval': word.interval or 0,
            'repetitions': word.repetitions or 0,
            'due_date': word.due_date.isoformat() if word.due_date else datetime.utcnow().isoformat(),
            'variants': [
                {
                    'id': v.id,
                    'value': v.value,
                    'translation': v.translation,
                    'tags': v.get_tags(),
                    'word_id': v.word_id
                }
                for v in variants
            ]
        }
    })


@app.route("/api/word/<int:word_id>/copy", methods=["POST"])
@login_required
def api_copy_word(word_id):
    """Copy a word (and its variants) to another quiz."""
    word = db.session.get(Word, word_id)
    if not word:
        return jsonify({'error': 'Word not found'}), 404
    
    source_quiz = word.quiz
    if source_quiz.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    if not data or not data.get('target_quiz_id'):
        return jsonify({'error': 'target_quiz_id required'}), 400
    
    target_quiz = db.session.get(Quiz, data['target_quiz_id'])
    if not target_quiz or target_quiz.user_id != current_user.id:
        return jsonify({'error': 'Target quiz not found or access denied'}), 404
    
    # Create new word copy
    new_word = Word(
        lemma=word.lemma,
        translation=word.translation,
        quiz_id=target_quiz.id
    )
    new_word.set_properties(word.get_properties())
    new_word.example_sentence = word.example_sentence
    new_word.explanation = word.explanation
    
    db.session.add(new_word)
    db.session.flush()
    
    # Copy variants
    variants = Variant.query.filter_by(word_id=word.id).all()
    for variant in variants:
        new_variant = Variant(
            value=variant.value,
            translation=variant.translation,
            word_id=new_word.id
        )
        new_variant.set_tags(variant.get_tags())
        db.session.add(new_variant)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'word_id': new_word.id,
        'quiz_id': target_quiz.id
    }), 201


# Anki-style Spaced Repetition Endpoints
@app.route("/api/quiz/<int:quiz_id>/anki-cards", methods=["GET"])
@login_required
def api_get_anki_cards(quiz_id):
    """Get due cards for Anki-style review.
    
    Query params:
        mode: 'words' (default) or 'sentences'
        direction: 'forward' (default) or 'reverse'
    """
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz or quiz.user_id != current_user.id:
        return jsonify({'error': 'Quiz not found'}), 404
    
    mode = request.args.get('mode', 'words')
    direction = request.args.get('direction', 'forward')
    now = datetime.utcnow()
    
    due_cards = []
    new_cards = []
    
    # Helper to get direction-specific fields
    def get_anki_fields(item, is_reverse):
        if is_reverse:
            return {
                'ease_factor': item.ease_factor_reverse or 2.5,
                'interval': item.interval_reverse or 0,
                'repetitions': item.repetitions_reverse or 0,
                'due_date': item.due_date_reverse or now
            }
        else:
            return {
                'ease_factor': item.ease_factor or 2.5,
                'interval': item.interval or 0,
                'repetitions': item.repetitions or 0,
                'due_date': item.due_date or now
            }
    
    is_reverse = direction == 'reverse'
    
    if mode == 'sentences':
        # Get all sentences
        sentences = Sentence.query.filter_by(quiz_id=quiz_id).all()
        
        for sentence in sentences:
            fields = get_anki_fields(sentence, is_reverse)
            is_new = fields['repetitions'] == 0
            is_due = fields['due_date'] <= now
            
            sentence_data = {
                'id': sentence.id,
                'type': 'sentence',
                'text': sentence.text,
                'translation': sentence.translation,
                'quiz_id': sentence.quiz_id,
                'ease_factor': fields['ease_factor'],
                'interval': fields['interval'],
                'repetitions': fields['repetitions'],
                'due_date': fields['due_date'].isoformat(),
                'is_new': is_new,
                'is_due': is_due
            }
            
            if is_new:
                new_cards.append(sentence_data)
            elif is_due:
                due_cards.append(sentence_data)
        
        return jsonify({
            'due_cards': due_cards,
            'new_cards': new_cards,
            'total_due': len(due_cards),
            'total_new': len(new_cards),
            'total_sentences': len(sentences),
            'mode': 'sentences',
            'direction': direction
        })
    else:
        # Get all words (default mode)
        words = Word.query.filter_by(quiz_id=quiz_id).all()
        
        for word in words:
            fields = get_anki_fields(word, is_reverse)
            is_new = fields['repetitions'] == 0
            is_due = fields['due_date'] <= now
            
            word_data = {
                'id': word.id,
                'type': 'word',
                'lemma': word.lemma,
                'translation': word.translation,
                'properties': word.get_properties(),
                'example_sentence': word.example_sentence,
                'explanation': word.explanation,
                'quiz_id': word.quiz_id,
                'ease_factor': fields['ease_factor'],
                'interval': fields['interval'],
                'repetitions': fields['repetitions'],
                'due_date': fields['due_date'].isoformat(),
                'is_new': is_new,
                'is_due': is_due
            }
            
            if is_new:
                new_cards.append(word_data)
            elif is_due:
                due_cards.append(word_data)
        
        return jsonify({
            'due_cards': due_cards,
            'new_cards': new_cards,
            'total_due': len(due_cards),
            'total_new': len(new_cards),
            'total_words': len(words),
            'mode': 'words',
            'direction': direction
        })


@app.route("/api/anki-stats", methods=["GET"])
@login_required
def api_get_anki_stats():
    """Get Anki statistics across all quizzes for the current user."""
    now = datetime.utcnow()
    
    # Get all quizzes for the user
    quizzes = Quiz.query.filter_by(user_id=current_user.id).all()
    
    total_due_words = 0
    total_new_words = 0
    total_due_sentences = 0
    total_new_sentences = 0
    quizzes_with_due = []
    
    for quiz in quizzes:
        # Count due/new words (forward direction)
        words = Word.query.filter_by(quiz_id=quiz.id).all()
        quiz_due_words = 0
        quiz_new_words = 0
        
        for word in words:
            is_new = (word.repetitions or 0) == 0
            is_due = (word.due_date or now) <= now
            
            if is_new:
                quiz_new_words += 1
            elif is_due:
                quiz_due_words += 1
        
        # Count due/new sentences (forward direction)
        sentences = Sentence.query.filter_by(quiz_id=quiz.id).all()
        quiz_due_sentences = 0
        quiz_new_sentences = 0
        
        for sentence in sentences:
            is_new = (sentence.repetitions or 0) == 0
            is_due = (sentence.due_date or now) <= now
            
            if is_new:
                quiz_new_sentences += 1
            elif is_due:
                quiz_due_sentences += 1
        
        total_due_words += quiz_due_words
        total_new_words += quiz_new_words
        total_due_sentences += quiz_due_sentences
        total_new_sentences += quiz_new_sentences
        
        # Track quizzes with due cards
        if quiz_due_words > 0 or quiz_due_sentences > 0:
            quizzes_with_due.append({
                'id': quiz.id,
                'name': quiz.name,
                'due_words': quiz_due_words,
                'due_sentences': quiz_due_sentences,
                'new_words': quiz_new_words,
                'new_sentences': quiz_new_sentences
            })
    
    return jsonify({
        'total_due_words': total_due_words,
        'total_new_words': total_new_words,
        'total_due_sentences': total_due_sentences,
        'total_new_sentences': total_new_sentences,
        'total_due': total_due_words + total_due_sentences,
        'total_new': total_new_words + total_new_sentences,
        'quizzes_with_due': quizzes_with_due
    })


def calculate_sm2(rating, ease_factor, interval, repetitions):
    """SM-2 Algorithm implementation.
    Returns (new_ease_factor, new_interval, new_repetitions)
    """
    if rating == 1:  # Again - complete failure
        repetitions = 0
        interval = 0
        ease_factor = max(1.3, ease_factor - 0.2)
    elif rating == 2:  # Hard
        if repetitions == 0:
            interval = 1
        else:
            interval = max(1, int(interval * 1.2))
        ease_factor = max(1.3, ease_factor - 0.15)
        repetitions += 1
    elif rating == 3:  # Good
        if repetitions == 0:
            interval = 1
        elif repetitions == 1:
            interval = 6
        else:
            interval = int(interval * ease_factor)
        repetitions += 1
    elif rating == 4:  # Easy
        if repetitions == 0:
            interval = 4
        elif repetitions == 1:
            interval = 10
        else:
            interval = int(interval * ease_factor * 1.3)
        ease_factor = min(3.0, ease_factor + 0.15)
        repetitions += 1
    
    return ease_factor, interval, repetitions


@app.route("/api/word/<int:word_id>/review", methods=["POST"])
@login_required
def api_review_word(word_id):
    """Update a word after Anki-style review.
    
    Body params:
        rating: 1-4 (required)
        direction: 'forward' (default) or 'reverse'
    
    Rating scale:
    1 = Again (complete failure, reset to beginning)
    2 = Hard (correct but difficult)
    3 = Good (correct with some effort)
    4 = Easy (correct with no effort)
    """
    word = db.session.get(Word, word_id)
    if not word:
        return jsonify({'error': 'Word not found'}), 404
    
    quiz = word.quiz
    if quiz.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    if not data or 'rating' not in data:
        return jsonify({'error': 'Rating required (1-4)'}), 400
    
    rating = data.get('rating')
    direction = data.get('direction', 'forward')
    
    if rating not in [1, 2, 3, 4]:
        return jsonify({'error': 'Rating must be 1, 2, 3, or 4'}), 400
    
    # Get direction-specific fields
    if direction == 'reverse':
        ease_factor = word.ease_factor_reverse or 2.5
        interval = word.interval_reverse or 0
        repetitions = word.repetitions_reverse or 0
    else:
        ease_factor = word.ease_factor or 2.5
        interval = word.interval or 0
        repetitions = word.repetitions or 0
    
    # Apply SM-2 algorithm
    ease_factor, interval, repetitions = calculate_sm2(rating, ease_factor, interval, repetitions)
    due_date = datetime.utcnow() + timedelta(days=interval)
    
    # Update direction-specific fields
    if direction == 'reverse':
        word.ease_factor_reverse = ease_factor
        word.interval_reverse = interval
        word.repetitions_reverse = repetitions
        word.due_date_reverse = due_date
    else:
        word.ease_factor = ease_factor
        word.interval = interval
        word.repetitions = repetitions
        word.due_date = due_date
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'word_id': word.id,
        'direction': direction,
        'ease_factor': ease_factor,
        'interval': interval,
        'repetitions': repetitions,
        'due_date': due_date.isoformat()
    })


@app.route("/api/sentence/<int:sentence_id>/review", methods=["POST"])
@login_required
def api_review_sentence(sentence_id):
    """Update a sentence after Anki-style review.
    
    Body params:
        rating: 1-4 (required)
        direction: 'forward' (default) or 'reverse'
    
    Rating scale:
    1 = Again (complete failure, reset to beginning)
    2 = Hard (correct but difficult)
    3 = Good (correct with some effort)
    4 = Easy (correct with no effort)
    """
    sentence = db.session.get(Sentence, sentence_id)
    if not sentence:
        return jsonify({'error': 'Sentence not found'}), 404
    
    quiz = db.session.get(Quiz, sentence.quiz_id)
    if not quiz or quiz.user_id != current_user.id:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.get_json()
    if not data or 'rating' not in data:
        return jsonify({'error': 'Rating required (1-4)'}), 400
    
    rating = data.get('rating')
    direction = data.get('direction', 'forward')
    
    if rating not in [1, 2, 3, 4]:
        return jsonify({'error': 'Rating must be 1, 2, 3, or 4'}), 400
    
    # Get direction-specific fields
    if direction == 'reverse':
        ease_factor = sentence.ease_factor_reverse or 2.5
        interval = sentence.interval_reverse or 0
        repetitions = sentence.repetitions_reverse or 0
    else:
        ease_factor = sentence.ease_factor or 2.5
        interval = sentence.interval or 0
        repetitions = sentence.repetitions or 0
    
    # Apply SM-2 algorithm
    ease_factor, interval, repetitions = calculate_sm2(rating, ease_factor, interval, repetitions)
    due_date = datetime.utcnow() + timedelta(days=interval)
    
    # Update direction-specific fields
    if direction == 'reverse':
        sentence.ease_factor_reverse = ease_factor
        sentence.interval_reverse = interval
        sentence.repetitions_reverse = repetitions
        sentence.due_date_reverse = due_date
    else:
        sentence.ease_factor = ease_factor
        sentence.interval = interval
        sentence.repetitions = repetitions
        sentence.due_date = due_date
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'sentence_id': sentence.id,
        'direction': direction,
        'ease_factor': ease_factor,
        'interval': interval,
        'repetitions': repetitions,
        'due_date': due_date.isoformat()
    })


@app.route("/api/song-quiz", methods=["POST"])
@app.route("/api/import-text", methods=["POST"])
@login_required
def api_create_song_quiz():
    """Create a quiz from any text content - GPT will extract vocabulary."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    name = data.get('name')
    language = data.get('language')
    # Support both 'lyrics' (legacy) and 'content' field names
    content = data.get('content') or data.get('lyrics')
    context = data.get('context', '')
    
    if not name or not language or not content:
        return jsonify({'error': 'Name, language, and content/lyrics required'}), 400
    
    new_quiz = Quiz(
        name=name,
        user_id=current_user.id,
        is_song_quiz=True,  # All quizzes support sentences
        processing_status='pending',
        processing_message='Queued for processing...'
    )
    db.session.add(new_quiz)
    db.session.commit()
    
    # Start background processing
    thread = threading.Thread(
        target=process_text_import_background,
        args=(new_quiz.id, content, language, context),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        'quiz': {
            'id': new_quiz.id,
            'name': new_quiz.name,
            'user_id': new_quiz.user_id,
            'created_at': new_quiz.created_at.isoformat(),
            'is_song_quiz': True,  # All quizzes support sentences
            'processing_status': new_quiz.processing_status,
            'processing_message': new_quiz.processing_message,
            'words': []
        }
    }), 201


@app.route("/api/quiz/<int:quiz_id>/import-text", methods=["POST"])
@login_required
def api_import_text_to_quiz(quiz_id):
    """Add words from text to an existing quiz - GPT will extract vocabulary."""
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz or quiz.user_id != current_user.id:
        return jsonify({'error': 'Quiz not found or access denied'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    content = data.get('content')
    context = data.get('context', '')
    
    if not content:
        return jsonify({'error': 'Content required.'}), 400
    
    # Auto-detect language from text content
    # Ukrainian/Polish is ALWAYS the language being practiced (target_language)
    def has_cyrillic(text):
        """Check if text contains Cyrillic characters."""
        return any('\u0400' <= char <= '\u04FF' for char in text)
    
    if has_cyrillic(content):
        # Text is in the practice language (Ukrainian/Polish)
        language = quiz.target_language or "Ukrainian"  # Always Ukrainian/Polish
    else:
        # Text is in the known language (English/Swedish)
        language = quiz.source_language or "English"  # Always English/Swedish
    
    # Mark quiz as processing
    quiz.processing_status = 'processing'
    quiz.processing_message = 'Adding words from text...'
    db.session.commit()
    
    # Start background processing
    thread = threading.Thread(
        target=process_text_import_background,
        args=(quiz_id, content, language, context),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        'message': 'Processing text and adding words to quiz...',
        'quiz_id': quiz_id
    }), 200


@app.route("/api/quiz/<int:quiz_id>/import-image", methods=["POST"])
@login_required
def api_import_image_to_quiz(quiz_id):
    """Extract text from an image using OCR (GPT-4 Vision) and import vocabulary."""
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz or quiz.user_id != current_user.id:
        return jsonify({'error': 'Quiz not found or access denied'}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    image_base64 = data.get('image')
    context = data.get('context', '')
    
    if not image_base64:
        return jsonify({'error': 'Image required.'}), 400
    
    # Mark quiz as processing
    quiz.processing_status = 'processing'
    quiz.processing_message = 'Extracting text from image...'
    db.session.commit()
    
    # Start background processing
    thread = threading.Thread(
        target=process_image_import_background,
        args=(quiz_id, image_base64, context),
        daemon=True
    )
    thread.start()
    
    return jsonify({
        'message': 'Processing image and extracting vocabulary...',
        'quiz_id': quiz_id
    }), 200


def process_image_import_background(quiz_id, image_base64, context=""):
    """Background function to extract text from image and then process vocabulary."""
    with app.app_context():
        quiz = db.session.get(Quiz, quiz_id)
        if not quiz:
            return
        
        try:
            # Update status
            quiz.processing_status = 'processing'
            quiz.processing_message = 'Extracting text from image using AI...'
            db.session.commit()
            
            # Use GPT-4 Vision to extract text
            from openai import OpenAI
            import os
            
            api_key = None
            if os.path.exists("apikey.txt"):
                with open("apikey.txt", 'r') as f:
                    api_key = f.read().strip()
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
            
            client = OpenAI(api_key=api_key)
            
            # Determine expected language for OCR
            target_lang = quiz.target_language or "Ukrainian"
            source_lang = quiz.source_language or "English"
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": f"""You are an OCR expert. Extract ALL text from the image exactly as it appears.
The image likely contains text in {target_lang} and/or {source_lang} for language learning purposes.

Important:
- Preserve the original text formatting as much as possible
- Include ALL text visible in the image
- If there are translations or explanations in parentheses, include them
- Maintain line breaks where they appear meaningful
- Do not translate or modify the text, just transcribe it exactly"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image:"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000
            )
            
            extracted_text = response.choices[0].message.content
            
            if not extracted_text or len(extracted_text.strip()) < 5:
                quiz.processing_status = 'error'
                quiz.processing_message = 'Could not extract text from image'
                db.session.commit()
                return
            
            quiz.processing_message = f'Text extracted. Processing vocabulary...'
            db.session.commit()
            
            # Check for cancellation after OCR
            db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return
            
            # Now process the extracted text using the same flow as text import
            # Auto-detect language from extracted text
            def has_cyrillic(text):
                return any('\u0400' <= char <= '\u04FF' for char in text)
            
            if has_cyrillic(extracted_text):
                language = quiz.target_language or "Ukrainian"
            else:
                language = quiz.source_language or "English"
            
            # Use the existing text import function
            process_text_import_background(quiz_id, extracted_text, language, context)
            
        except Exception as e:
            print(f"Error processing image: {e}")
            quiz.processing_status = 'error'
            quiz.processing_status = 'error'
            quiz.processing_message = f'Error: {str(e)}'
            db.session.commit()


@app.route("/api/quiz/<int:quiz_id>/cancel-processing", methods=["POST"])
@login_required
def api_cancel_processing(quiz_id):
    """Cancel ongoing text/image processing for a quiz."""
    quiz = db.session.get(Quiz, quiz_id)
    if not quiz or quiz.user_id != current_user.id:
        return jsonify({'error': 'Quiz not found or access denied'}), 404
    
    # Only allow cancellation if currently processing
    if quiz.processing_status not in ['pending', 'processing']:
        return jsonify({'error': 'No active processing to cancel'}), 400
    
    # Set status to cancelled
    quiz.processing_status = 'cancelled'
    quiz.processing_message = 'Processing cancelled by user'
    db.session.commit()
    
    return jsonify({
        'message': 'Processing cancelled',
        'quiz_id': quiz_id
    }), 200


# Folder API endpoints
@app.route("/api/folders", methods=["GET", "POST"])
@login_required
def api_folders():
    """Get all folders or create a new folder."""
    if request.method == "GET":
        # Get all folders for the user, build tree structure
        folders = Folder.query.filter_by(user_id=current_user.id, parent_id=None).all()
        
        def build_folder_tree(folder):
            """Recursively build folder tree with quizzes."""
            subfolders = Folder.query.filter_by(parent_id=folder.id).all()
            quizzes = Quiz.query.filter_by(folder_id=folder.id, user_id=current_user.id).all()
            
            return {
                'id': folder.id,
                'name': folder.name,
                'user_id': folder.user_id,
                'parent_id': folder.parent_id,
                'created_at': folder.created_at.isoformat(),
                'quizzes': [
                    {
                        'id': q.id,
                        'name': q.name,
                        'is_song_quiz': True,  # All quizzes support sentences
                        'processing_status': q.processing_status,
                        'words': [{'id': w.id, 'lemma': w.lemma, 'translation': w.translation} for w in q.words]
                    }
                    for q in quizzes
                ],
                'subfolders': [build_folder_tree(sf) for sf in subfolders]
            }
        
        folders_data = [build_folder_tree(f) for f in folders]
        
        return jsonify({
            'folders': folders_data
        })
    
    # POST - create new folder
    data = request.get_json()
    if not data or not data.get('name'):
        return jsonify({'error': 'Folder name required'}), 400
    
    parent_id = data.get('parent_id')  # Optional parent folder ID
    
    # Validate parent folder belongs to user if provided
    if parent_id:
        parent = db.session.get(Folder, parent_id)
        if not parent or parent.user_id != current_user.id:
            return jsonify({'error': 'Invalid parent folder'}), 400
    
    new_folder = Folder(
        name=data['name'],
        user_id=current_user.id,
        parent_id=parent_id
    )
    db.session.add(new_folder)
    db.session.commit()
    
    return jsonify({
        'folder': {
            'id': new_folder.id,
            'name': new_folder.name,
            'user_id': new_folder.user_id,
            'parent_id': new_folder.parent_id,
            'created_at': new_folder.created_at.isoformat(),
            'quizzes': [],
            'subfolders': []
        }
    }), 201


@app.route("/api/folder/<int:folder_id>", methods=["GET", "DELETE", "PUT"])
@login_required
def api_folder_detail(folder_id):
    """Get, update, or delete a folder."""
    folder = db.session.get(Folder, folder_id)
    
    if not folder or folder.user_id != current_user.id:
        return jsonify({'error': 'Folder not found'}), 404
    
    if request.method == "DELETE":
        # Check if folder has quizzes or subfolders
        quizzes_count = Quiz.query.filter_by(folder_id=folder_id).count()
        subfolders_count = Folder.query.filter_by(parent_id=folder_id).count()
        
        if quizzes_count > 0 or subfolders_count > 0:
            return jsonify({'error': 'Cannot delete folder with quizzes or subfolders. Move them first.'}), 400
        
        db.session.delete(folder)
        db.session.commit()
        return jsonify({'success': True})
    
    if request.method == "PUT":
        data = request.get_json()
        if data.get('name'):
            folder.name = data['name']
        if 'parent_id' in data:
            new_parent_id = data['parent_id']
            # Validate parent folder if provided
            if new_parent_id:
                parent = db.session.get(Folder, new_parent_id)
                if not parent or parent.user_id != current_user.id:
                    return jsonify({'error': 'Invalid parent folder'}), 400
                # Prevent circular references
                if new_parent_id == folder_id:
                    return jsonify({'error': 'Cannot set folder as its own parent'}), 400
                # Check if new parent is a descendant of this folder
                def is_descendant(check_id, ancestor_id):
                    if check_id == ancestor_id:
                        return True
                    parent_folder = db.session.get(Folder, check_id)
                    if parent_folder and parent_folder.parent_id:
                        return is_descendant(parent_folder.parent_id, ancestor_id)
                    return False
                
                if is_descendant(new_parent_id, folder_id):
                    return jsonify({'error': 'Cannot create circular reference'}), 400
            
            folder.parent_id = new_parent_id
        
        db.session.commit()
        
        return jsonify({
            'folder': {
                'id': folder.id,
                'name': folder.name,
                'user_id': folder.user_id,
                'parent_id': folder.parent_id,
                'created_at': folder.created_at.isoformat(),
            }
        })
    
    # GET
    quizzes = Quiz.query.filter_by(folder_id=folder_id).all()
    subfolders = Folder.query.filter_by(parent_id=folder_id).all()
    
    return jsonify({
        'folder': {
            'id': folder.id,
            'name': folder.name,
            'user_id': folder.user_id,
            'parent_id': folder.parent_id,
            'created_at': folder.created_at.isoformat(),
            'quizzes': [
                {
                    'id': q.id,
                    'name': q.name,
                    'is_song_quiz': q.is_song_quiz,
                    'processing_status': q.processing_status,
                    'words': [{'id': w.id, 'lemma': w.lemma, 'translation': w.translation} for w in q.words]
                }
                for q in quizzes
            ],
            'subfolders': [
                {
                    'id': sf.id,
                    'name': sf.name,
                    'parent_id': sf.parent_id,
                }
                for sf in subfolders
            ]
        }
    })


@app.route("/api/quiz/<int:quiz_id>/move", methods=["POST"])
@login_required
def api_move_quiz(quiz_id):
    """Move a quiz to a folder."""
    quiz = db.session.get(Quiz, quiz_id)
    
    if not quiz or quiz.user_id != current_user.id:
        return jsonify({'error': 'Quiz not found'}), 404
    
    data = request.get_json()
    folder_id = data.get('folder_id')  # None means move to root
    
    if folder_id:
        folder = db.session.get(Folder, folder_id)
        if not folder or folder.user_id != current_user.id:
            return jsonify({'error': 'Folder not found'}), 404
    
    quiz.folder_id = folder_id
    db.session.commit()
    
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
