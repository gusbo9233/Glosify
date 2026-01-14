"""
Utility functions for data conversion and parsing.
"""

from typing import Dict, List, Any


def parse_tags_from_string(tags_string: str) -> Dict[str, str]:
    """
    Parse tags from string format "key1=value1,key2=value2" into a dictionary.
    
    Args:
        tags_string: String in format "key1=value1,key2=value2"
        
    Returns:
        Dictionary of tags
    """
    tags_dict = {}
    if tags_string:
        for tag_pair in tags_string.split(','):
            tag_pair = tag_pair.strip()
            if '=' in tag_pair:
                key, value = tag_pair.split('=', 1)
                tags_dict[key.strip()] = value.strip()
    return tags_dict


def word_to_dict(word: Any) -> Dict:
    """
    Convert a Word SQLAlchemy object to a dictionary for JSON serialization.
    
    Args:
        word: Word SQLAlchemy model instance (or any object with id, lemma, translation, get_properties, example_sentence)
        
    Returns:
        Dictionary representation of the word
    """
    return {
        'id': word.id,
        'lemma': word.lemma,
        'translation': word.translation,
        'properties': word.get_properties(),
        'example_sentence': word.example_sentence or ''
    }


def words_to_dict_list(words: List[Any]) -> List[Dict]:
    """
    Convert a list of Word SQLAlchemy objects to a list of dictionaries.
    
    Args:
        words: List of Word SQLAlchemy model instances
        
    Returns:
        List of dictionary representations
    """
    return [word_to_dict(word) for word in words]


def sentence_to_dict(sentence: Any) -> Dict:
    """
    Convert a Sentence SQLAlchemy object to a dictionary for JSON serialization.
    
    Args:
        sentence: Sentence SQLAlchemy model instance (or any object with text, translation)
        
    Returns:
        Dictionary representation of the sentence
    """
    return {
        'text': sentence.text,
        'translation': sentence.translation or ''
    }


def sentences_to_dict_list(sentences: List[Any]) -> List[Dict]:
    """
    Convert a list of Sentence SQLAlchemy objects to a list of dictionaries.
    
    Args:
        sentences: List of Sentence SQLAlchemy model instances
        
    Returns:
        List of dictionary representations
    """
    return [sentence_to_dict(sentence) for sentence in sentences]

