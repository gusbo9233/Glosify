#!/usr/bin/env python3
"""
Quick test of song lyrics processing with a real Ukrainian folk song.
"""

import sys
import os
import re

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gptcaller import get_gpt_caller

# The Ukrainian folk song lyrics
lyrics = """Несе Галя воду, коромисло гнеться.
За нею Іванко, як барвінок в'ється.
За нею Іванко, як барвінок в'ється.

Галю, ж, моя, Галю, дай води напиться.
Ти ж така хороша, дай хоч подивиться.
Ти ж така хороша, дай хоч подивиться.

Вода у ставочку, піди, та й напийся.
Я ж буду в садочку, прийди подивися.
Я ж буду в садочку, прийди подивися.

Прийшов у садочок, зозуля кувала.
А ти ж мене, Галю, та й не шанувала.
А ти ж мене, Галю, та й не шанувала.

Стелися, барвінку, буду поливати.
Вернися, Іванку, буду шанувати.
Вернися, Іванку, буду шанувати.

Скільки не стелився, ти не поливала.
Скільки не вертався, ти не шанувала.
Скільки не вертався, ти не шанувала.

Скільки не вертався, ти не шанувала.
Скільки не вертався, ти не шанувала."""

context = "Ukrainian folk song about a young man (Іванко) courting a girl (Галя). It's a traditional love song with nature imagery (barvinok/periwinkle flower)."

def main():
    print("=" * 60)
    print("Testing Song Lyrics Processing")
    print("=" * 60)
    
    # Extract unique words and lines
    lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
    unique_lines = list(dict.fromkeys(lines))
    
    all_words = re.findall(r'\b\w+\b', lyrics.lower())
    unique_words = list(dict.fromkeys(all_words))
    
    print(f"\nExtracted {len(unique_lines)} unique lines")
    print(f"Extracted {len(unique_words)} unique words")
    
    print("\n" + "=" * 60)
    print("Sample Words (first 20):")
    print("=" * 60)
    for word in unique_words[:20]:
        print(f"  - {word}")
    
    print("\n" + "=" * 60)
    print("Testing Word Analysis (sample of 5 words)")
    print("=" * 60)
    
    caller = get_gpt_caller()
    
    # Test a few words
    test_words = unique_words[:5]
    irrelevant_count = 0
    relevant_count = 0
    
    for word in test_words:
        print(f"\nTesting: '{word}'")
        try:
            analysis = caller.generate_word_analysis(
                lemma=word,
                translation="",
                language="Ukrainian",
                context=context
            )
            
            is_irrelevant = getattr(analysis, 'is_irrelevant', False)
            
            if is_irrelevant:
                irrelevant_count += 1
                print(f"  ✗ IRRELEVANT (will be skipped)")
                print(f"    POS: {analysis.pos}")
                print(f"    Translations: {analysis.translations[:2] if analysis.translations else 'None'}")
            else:
                relevant_count += 1
                print(f"  ✓ RELEVANT")
                print(f"    POS: {analysis.pos}")
                print(f"    Translations: {analysis.translations[:2] if analysis.translations else 'None'}")
                print(f"    Variants: {len(analysis.variants)}")
                if analysis.variants:
                    print(f"      Example: '{analysis.variants[0].value}' → '{analysis.variants[0].translation}'")
        except Exception as e:
            print(f"  ✗ Error: {str(e)[:100]}")
    
    print("\n" + "=" * 60)
    print("Testing Sentence Translation (sample of 3 lines)")
    print("=" * 60)
    
    for i, line in enumerate(unique_lines[:3], 1):
        print(f"\n{i}. '{line}'")
        try:
            translation = caller.generate_sentence_translation(
                sentence=line,
                language="Ukrainian",
                context=context
            )
            if hasattr(translation, 'translation'):
                print(f"   → '{translation.translation}'")
        except Exception as e:
            print(f"   ✗ Error: {str(e)[:100]}")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total unique words: {len(unique_words)}")
    print(f"Total unique lines: {len(unique_lines)}")
    print(f"\nSample analysis:")
    print(f"  Relevant words: {relevant_count}")
    print(f"  Irrelevant words: {irrelevant_count}")
    print(f"\nEstimated processing time:")
    print(f"  Sentences: ~{len(unique_lines) * 3.75 / 60:.1f} minutes")
    print(f"  Words: ~{len(unique_words) * 15.59 / 60:.1f} minutes")
    print(f"  Total: ~{(len(unique_lines) * 3.75 + len(unique_words) * 15.59) / 60:.1f} minutes")

if __name__ == "__main__":
    main()

