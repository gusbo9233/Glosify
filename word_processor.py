"""
Word and sentence processing logic for GPT analysis.
"""

from typing import Dict, Optional, List
from gptcaller import GPTCaller, convert_to_word_class


def process_single_sentence(
    line: str,
    language: str,
    context: Optional[str],
    caller: GPTCaller
) -> Dict:
    """
    Process a single sentence and return the result.
    
    Args:
        line: The sentence to translate
        language: The language of the sentence
        context: Optional context about the song/theme
        caller: GPTCaller instance for API calls
        
    Returns:
        Dictionary with keys: 'text', 'translation', 'error'
    """
    try:
        sentence_analysis = caller.generate_sentence_translation(
            sentence=line,
            language=language,
            context=context if context else None
        )
        translation = sentence_analysis.translation if hasattr(sentence_analysis, 'translation') else ""
        return {'text': line, 'translation': translation, 'error': None}
    except Exception as e:
        print(f"Failed to translate sentence '{line}': {e}")
        return {'text': line, 'translation': "", 'error': str(e)}


def process_single_word(
    word_text: str,
    sentence_context: List[str],
    language: str,
    context: Optional[str],
    caller: GPTCaller
) -> Dict:
    """
    Process a single word and return the result.
    
    Args:
        word_text: The word to analyze
        sentence_context: List of sentences where this word appears
        language: The language of the word
        context: Optional context about the song/theme
        caller: GPTCaller instance for API calls
        
    Returns:
        Dictionary with keys: 'word', 'translation', 'word_data', 'skip', 'reason', 'error'
    """
    try:
        analysis = caller.generate_word_analysis(
            lemma=word_text,
            translation="",
            language=language,
            context=context if context else None,
            sentence_context=sentence_context if sentence_context else None
        )
        
        # Skip words that GPT identifies as irrelevant
        if hasattr(analysis, 'is_irrelevant') and analysis.is_irrelevant:
            return {'word': word_text, 'skip': True, 'reason': 'irrelevant', 'error': None}
        
        # Check if analysis has meaningful data
        if not analysis.translations or len(analysis.translations) == 0:
            return {'word': word_text, 'skip': True, 'reason': 'no_translations', 'error': None}
        
        translation = analysis.translations[0] if analysis.translations else ""
        word_data = convert_to_word_class(analysis, word_text)
        
        return {
            'word': word_text,
            'translation': translation,
            'word_data': word_data,
            'skip': False,
            'error': None
        }
    except Exception as e:
        print(f"Failed to analyze word '{word_text}': {e}")
        return {'word': word_text, 'skip': True, 'reason': 'error', 'error': str(e)}

