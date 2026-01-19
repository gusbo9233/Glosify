import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from gptcaller import get_gpt_caller, convert_to_word_class
from gptcaller_polish import get_gpt_caller_polish, convert_to_word_class as convert_to_word_class_polish
from gptcaller_prompt import get_gpt_caller_prompt


@dataclass(frozen=True)
class QuizProcessingDeps:
    app: object
    db: object
    Quiz: object
    Word: object
    Sentence: object
    Variant: object


def process_text_import_background(deps, quiz_id, content, language, context=""):
    """Background function to process any text and extract vocabulary using GPT."""
    with deps.app.app_context():
        quiz = deps.db.session.get(deps.Quiz, quiz_id)
        if not quiz:
            return

        try:
            # Update status to processing
            quiz.processing_status = 'processing'
            quiz.processing_message = 'Extracting vocabulary with AI...'
            deps.db.session.commit()

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
            deps.db.session.commit()

            # Check for cancellation after extraction
            deps.db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return

            # Save sentences and create word-to-sentence mapping
            saved_sentences = []
            for sent in extracted.sentences:
                new_sentence = deps.Sentence(
                    text=sent.text,
                    translation=sent.translation,
                    quiz_id=quiz_id
                )
                deps.db.session.add(new_sentence)
                saved_sentences.append({
                    'text': sent.text,
                    'translation': sent.translation
                })
            deps.db.session.commit()

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
            deps.db.session.commit()

            # Check for cancellation before starting word analysis
            deps.db.session.refresh(quiz)
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
                    deps.db.session.refresh(quiz)
                    if quiz.processing_status == 'cancelled':
                        # Cancel remaining futures
                        for f in future_to_word:
                            f.cancel()
                        return

                    result = future.result()
                    word_results.append(result)
                    completed += 1
                    quiz.processing_message = f'Analyzing words ({completed}/{len(extracted.words)})...'
                    deps.db.session.commit()

            # Check for cancellation before saving words
            deps.db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return

            # Save word results
            for result in word_results:
                if result.get('skip'):
                    continue

                new_word = deps.Word(
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

                deps.db.session.add(new_word)
                deps.db.session.flush()

                # Add variants if available
                if word_data and word_data.get('variants'):
                    for variant_data in word_data['variants']:
                        new_variant = deps.Variant(
                            value=variant_data['value'],
                            translation=variant_data['translation'],
                            word_id=new_word.id
                        )
                        if variant_data.get('tags'):
                            new_variant.set_tags(variant_data['tags'])
                        deps.db.session.add(new_variant)

                words_added += 1

            deps.db.session.commit()

            # Mark as completed
            quiz.processing_status = 'completed'
            quiz.processing_message = f'Completed! {words_added} words and {len(extracted.sentences)} sentences.'
            deps.db.session.commit()

        except Exception as e:
            print(f"Error processing quiz {quiz_id}: {e}")
            import traceback
            traceback.print_exc()
            quiz.processing_status = 'error'
            quiz.processing_message = f'Error: {str(e)[:100]}'
            deps.db.session.commit()


def process_prompt_import_background(deps, quiz_id, prompt, source_language, target_language, context=""):
    """Background function to generate vocabulary from a prompt and process it."""
    with deps.app.app_context():
        quiz = deps.db.session.get(deps.Quiz, quiz_id)
        if not quiz:
            return

        try:
            # Update status
            quiz.processing_status = 'processing'
            quiz.processing_message = 'Generating vocabulary from prompt...'
            deps.db.session.commit()

            # Stage 1: Generate word pairs from prompt
            prompt_caller = get_gpt_caller_prompt()
            prompt_vocab = prompt_caller.generate_vocabulary_from_prompt(
                prompt=prompt,
                source_language=target_language,  # The language being learned (Polish/Ukrainian)
                target_language=source_language   # The language user knows (English/Swedish)
            )

            quiz.processing_message = f'Generated {len(prompt_vocab.words)} words. Analyzing in detail...'
            deps.db.session.commit()

            # Check for cancellation after prompt generation
            deps.db.session.refresh(quiz)
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
            deps.db.session.commit()

            # Check for cancellation before starting word analysis
            deps.db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_word = {
                    executor.submit(analyze_word, word_pair): word_pair
                    for word_pair in prompt_vocab.words
                }

                completed = 0
                for future in as_completed(future_to_word):
                    # Check for cancellation periodically
                    deps.db.session.refresh(quiz)
                    if quiz.processing_status == 'cancelled':
                        for f in future_to_word:
                            f.cancel()
                        return

                    result = future.result()
                    word_results.append(result)
                    completed += 1
                    quiz.processing_message = f'Analyzing words ({completed}/{len(prompt_vocab.words)})...'
                    deps.db.session.commit()

            # Save results
            for result in word_results:
                if result.get('skip'):
                    continue

                new_word = deps.Word(
                    lemma=result['lemma'],
                    translation=result['translation'],
                    quiz_id=quiz_id
                )

                word_data = result.get('word_data')
                if word_data and word_data.get('properties'):
                    new_word.set_properties(word_data['properties'])
                else:
                    new_word.set_properties({})

                if word_data and word_data.get('example_sentence'):
                    new_word.example_sentence = word_data['example_sentence']

                if word_data and word_data.get('explanation'):
                    new_word.explanation = word_data['explanation']

                deps.db.session.add(new_word)
                deps.db.session.flush()

                # Add variants if available
                if word_data and word_data.get('variants'):
                    for variant_data in word_data['variants']:
                        new_variant = deps.Variant(
                            value=variant_data['value'],
                            translation=variant_data['translation'],
                            word_id=new_word.id
                        )
                        if variant_data.get('tags'):
                            new_variant.set_tags(variant_data['tags'])
                        deps.db.session.add(new_variant)

            deps.db.session.commit()

            # Mark as completed
            quiz.processing_status = 'completed'
            quiz.processing_message = f'Completed! {len(prompt_vocab.words)} words generated.'
            deps.db.session.commit()

        except Exception as e:
            print(f"Error processing prompt quiz {quiz_id}: {e}")
            quiz.processing_status = 'error'
            quiz.processing_message = f'Error: {str(e)[:100]}'
            deps.db.session.commit()


def process_song_quiz_background(deps, quiz_id, lyrics, language, context=""):
    """Legacy function - calls the new generalized version."""
    process_text_import_background(deps, quiz_id, lyrics, language, context)


def process_image_import_background(deps, quiz_id, image_base64, context=""):
    """Background function to extract text from image and then process vocabulary."""
    with deps.app.app_context():
        quiz = deps.db.session.get(deps.Quiz, quiz_id)
        if not quiz:
            return

        # Abort early if processing was cancelled
        if quiz.processing_status == 'cancelled':
            return

        try:
            # Update status
            quiz.processing_status = 'processing'
            quiz.processing_message = 'Extracting text from image using AI...'
            deps.db.session.commit()

            # Check for cancellation before expensive OCR
            deps.db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return

            # Use GPT-4 Vision to extract text
            from openai import OpenAI

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

            # Check for cancellation before downstream processing
            deps.db.session.refresh(quiz)
            if quiz.processing_status == 'cancelled':
                return

            if not extracted_text or len(extracted_text.strip()) < 5:
                quiz.processing_status = 'error'
                quiz.processing_message = 'Could not extract text from image'
                deps.db.session.commit()
                return

            quiz.processing_message = 'Text extracted. Processing vocabulary...'
            deps.db.session.commit()

            # Check for cancellation after OCR
            deps.db.session.refresh(quiz)
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
            process_text_import_background(deps, quiz_id, extracted_text, language, context)

        except Exception as e:
            print(f"Error processing image: {e}")
            quiz.processing_status = 'error'
            quiz.processing_status = 'error'
            quiz.processing_message = f'Error: {str(e)}'
            deps.db.session.commit()
