#!/usr/bin/env python3
"""
Test script to verify GPT data accuracy.
Tests word analysis, sentence translation, and irrelevant word detection.
"""

import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gptcaller import get_gpt_caller


def test_word_analysis():
    """Test word analysis accuracy."""
    print("=" * 60)
    print("Testing Word Analysis Accuracy")
    print("=" * 60)
    
    caller = get_gpt_caller()
    
    test_cases = [
        {
            "name": "Regular verb (Ukrainian)",
            "lemma": "читати",
            "translation": "",
            "language": "Ukrainian",
            "expected_pos": "verb",
            "should_have_variants": True,
            "should_be_irrelevant": False
        },
        {
            "name": "Noun (Ukrainian)",
            "lemma": "книга",
            "translation": "",
            "language": "Ukrainian",
            "expected_pos": "noun",
            "should_have_variants": True,
            "should_be_irrelevant": False
        },
        {
            "name": "Proper noun - Name (should be irrelevant)",
            "lemma": "Олександр",
            "translation": "",
            "language": "Ukrainian",
            "expected_pos": None,  # May vary
            "should_have_variants": False,
            "should_be_irrelevant": True
        },
        {
            "name": "Place name (should be irrelevant)",
            "lemma": "Київ",
            "translation": "",
            "language": "Ukrainian",
            "expected_pos": None,
            "should_have_variants": False,
            "should_be_irrelevant": True
        },
        {
            "name": "Common word from translation only",
            "lemma": "",
            "translation": "table",
            "language": "Ukrainian",
            "expected_pos": "noun",
            "should_have_variants": True,
            "should_be_irrelevant": False
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test['name']}")
        print(f"   Lemma: '{test['lemma']}' | Translation: '{test['translation']}'")
        
        try:
            analysis = caller.generate_word_analysis(
                lemma=test['lemma'],
                translation=test['translation'],
                language=test['language']
            )
            
            # Check results
            passed = True
            issues = []
            
            # Check is_irrelevant flag
            if hasattr(analysis, 'is_irrelevant'):
                if analysis.is_irrelevant != test['should_be_irrelevant']:
                    passed = False
                    issues.append(f"is_irrelevant: expected {test['should_be_irrelevant']}, got {analysis.is_irrelevant}")
                print(f"   ✓ is_irrelevant: {analysis.is_irrelevant}")
            else:
                issues.append("Missing is_irrelevant field")
                print(f"   ✗ Missing is_irrelevant field")
            
            # Check POS
            if test['expected_pos']:
                if analysis.pos.lower() != test['expected_pos'].lower():
                    # Allow some flexibility
                    if test['expected_pos'] not in analysis.pos.lower() and analysis.pos.lower() not in test['expected_pos']:
                        issues.append(f"POS: expected '{test['expected_pos']}', got '{analysis.pos}'")
                        print(f"   ⚠ POS: '{analysis.pos}' (expected '{test['expected_pos']}')")
                    else:
                        print(f"   ✓ POS: '{analysis.pos}'")
                else:
                    print(f"   ✓ POS: '{analysis.pos}'")
            else:
                print(f"   ℹ POS: '{analysis.pos}'")
            
            # Check translations
            if analysis.translations:
                print(f"   ✓ Translations: {analysis.translations[:3]}{'...' if len(analysis.translations) > 3 else ''}")
            else:
                if not test['should_be_irrelevant']:
                    issues.append("No translations provided")
                    print(f"   ✗ No translations")
                else:
                    print(f"   ℹ No translations (expected for irrelevant word)")
            
            # Check variants
            if test['should_have_variants']:
                if len(analysis.variants) > 0:
                    print(f"   ✓ Variants: {len(analysis.variants)} variants")
                    # Show first variant
                    if analysis.variants:
                        first_var = analysis.variants[0]
                        print(f"      Example: '{first_var.value}' → '{first_var.translation}'")
                else:
                    issues.append("Expected variants but got none")
                    print(f"   ✗ No variants (expected some)")
            else:
                print(f"   ℹ Variants: {len(analysis.variants)} (may be empty for irrelevant words)")
            
            # Check properties
            try:
                props = json.loads(analysis.properties) if analysis.properties else {}
                if props:
                    print(f"   ✓ Properties: {props}")
                else:
                    print(f"   ℹ Properties: empty")
            except:
                print(f"   ⚠ Properties: Could not parse JSON")
            
            # Check example sentence
            if analysis.example_sentence:
                print(f"   ✓ Example sentence: '{analysis.example_sentence[:60]}...'")
            else:
                print(f"   ℹ No example sentence")
            
            results.append({
                "test": test['name'],
                "passed": passed and len(issues) == 0,
                "issues": issues
            })
            
        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            results.append({
                "test": test['name'],
                "passed": False,
                "issues": [f"Exception: {str(e)}"]
            })
    
    return results


def test_sentence_translation():
    """Test sentence translation accuracy."""
    print("\n" + "=" * 60)
    print("Testing Sentence Translation Accuracy")
    print("=" * 60)
    
    caller = get_gpt_caller()
    
    test_cases = [
        {
            "name": "Simple sentence",
            "sentence": "Я читаю книгу",
            "language": "Ukrainian",
            "context": None
        },
        {
            "name": "Sentence with context",
            "sentence": "Він дуже старий",
            "language": "Ukrainian",
            "context": "This is from a song about an old table"
        },
        {
            "name": "Complex sentence",
            "sentence": "На столі лежить книга про Україну",
            "language": "Ukrainian",
            "context": None
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: {test['name']}")
        print(f"   Sentence: '{test['sentence']}'")
        if test['context']:
            print(f"   Context: '{test['context']}'")
        
        try:
            translation = caller.generate_sentence_translation(
                sentence=test['sentence'],
                language=test['language'],
                context=test['context']
            )
            
            if hasattr(translation, 'translation') and translation.translation:
                print(f"   ✓ Translation: '{translation.translation}'")
                results.append({
                    "test": test['name'],
                    "passed": True,
                    "issues": []
                })
            else:
                print(f"   ✗ No translation returned")
                results.append({
                    "test": test['name'],
                    "passed": False,
                    "issues": ["No translation in response"]
                })
                
        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            results.append({
                "test": test['name'],
                "passed": False,
                "issues": [f"Exception: {str(e)}"]
            })
    
    return results


def test_irrelevant_detection():
    """Test if GPT correctly identifies irrelevant words."""
    print("\n" + "=" * 60)
    print("Testing Irrelevant Word Detection")
    print("=" * 60)
    
    caller = get_gpt_caller()
    
    test_cases = [
        {
            "word": "Олександр",
            "language": "Ukrainian",
            "should_be_irrelevant": True,
            "reason": "Person name"
        },
        {
            "word": "Київ",
            "language": "Ukrainian",
            "should_be_irrelevant": True,
            "reason": "City name"
        },
        {
            "word": "читати",
            "language": "Ukrainian",
            "should_be_irrelevant": False,
            "reason": "Common verb"
        },
        {
            "word": "книга",
            "language": "Ukrainian",
            "should_be_irrelevant": False,
            "reason": "Common noun"
        }
    ]
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. Testing: '{test['word']}' ({test['reason']})")
        print(f"   Expected irrelevant: {test['should_be_irrelevant']}")
        
        try:
            analysis = caller.generate_word_analysis(
                lemma=test['word'],
                translation="",
                language=test['language']
            )
            
            is_irrelevant = getattr(analysis, 'is_irrelevant', False)
            
            if is_irrelevant == test['should_be_irrelevant']:
                print(f"   ✓ Correctly identified as {'irrelevant' if is_irrelevant else 'relevant'}")
                results.append({
                    "word": test['word'],
                    "passed": True,
                    "issues": []
                })
            else:
                print(f"   ✗ Incorrect: expected {test['should_be_irrelevant']}, got {is_irrelevant}")
                results.append({
                    "word": test['word'],
                    "passed": False,
                    "issues": [f"Expected {test['should_be_irrelevant']}, got {is_irrelevant}"]
                })
                
        except Exception as e:
            print(f"   ✗ Error: {str(e)}")
            results.append({
                "word": test['word'],
                "passed": False,
                "issues": [f"Exception: {str(e)}"]
            })
    
    return results


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("GPT Accuracy Test Suite")
    print("=" * 60)
    
    try:
        # Test word analysis
        word_results = test_word_analysis()
        
        # Test sentence translation
        sentence_results = test_sentence_translation()
        
        # Test irrelevant detection
        irrelevant_results = test_irrelevant_detection()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        all_results = word_results + sentence_results + irrelevant_results
        passed = sum(1 for r in all_results if r['passed'])
        total = len(all_results)
        
        print(f"\nTotal tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success rate: {passed/total*100:.1f}%")
        
        # Show failures
        failures = [r for r in all_results if not r['passed']]
        if failures:
            print("\nFailed tests:")
            for failure in failures:
                test_name = failure.get('test') or failure.get('word', 'Unknown')
                print(f"  - {test_name}")
                for issue in failure.get('issues', []):
                    print(f"    • {issue}")
        
        print("\n" + "=" * 60)
        print("Test complete!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

