"""
Text processing utilities for extracting words and sentences from lyrics.
"""

import re
from typing import List, Dict


def extract_unique_lines(text: str) -> List[str]:
    """
    Extract unique non-empty lines from text.
    
    Args:
        text: The input text (e.g., song lyrics)
        
    Returns:
        List of unique lines, preserving order
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    return list(dict.fromkeys(lines))  # Preserve order while removing duplicates


def extract_unique_words(text: str) -> List[str]:
    """
    Extract unique words from text (lowercase).
    
    Args:
        text: The input text
        
    Returns:
        List of unique words, preserving order
    """
    all_words = re.findall(r'\b\w+\b', text.lower())
    return list(dict.fromkeys(all_words))  # Preserve order while removing duplicates


def create_word_to_sentences_mapping(words: List[str], sentences: List[str]) -> Dict[str, List[str]]:
    """
    Create a mapping of words to the sentences they appear in.
    
    Args:
        words: List of unique words to map
        sentences: List of sentences to search in
        
    Returns:
        Dictionary mapping word -> list of sentences containing that word
    """
    word_to_sentences = {}
    for line in sentences:
        line_lower = line.lower()
        for word in words:
            # Check if word appears in this sentence (as whole word, not substring)
            word_pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(word_pattern, line_lower):
                if word not in word_to_sentences:
                    word_to_sentences[word] = []
                if line not in word_to_sentences[word]:  # Avoid duplicates
                    word_to_sentences[word].append(line)
    return word_to_sentences

