"""
OpenAI API caller for generating Ukrainian-English word pairs, variants, and example sentences.
Tailored specifically for Ukrainian language learning (English-Ukrainian direction).

For Polish, use gptcaller_polish.py instead.

Based on OpenAI Responses API documentation with Structured Outputs.
"""

from openai import OpenAI
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import os


class VariantData(BaseModel):
    """Represents a word variant with its translation and grammatical tags."""
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
    
    value: str
    translation: str
    case: Optional[str] = None  # e.g., "nom", "gen", "dat", "acc", "inst", "loc"
    number: Optional[str] = None  # "sg" or "pl"
    gender: Optional[str] = None  # "masc", "fem", "neut"
    tense: Optional[str] = None  # "pres", "past", "fut"
    person: Optional[str] = None  # "1", "2", "3"
    aspect: Optional[str] = None  # "perf", "impf"
    animacy: Optional[str] = None  # "animate", "inanimate"


class WordAnalysis(BaseModel):
    """Structured output for word analysis matching the Word class structure."""
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
    
    pos: str  # Part of speech: noun, verb, adjective, etc.
    translations: List[str]  # Multiple translations if applicable
    variants: List[VariantData]
    properties: str = "{}"  # JSON string for properties dict (gender, aspect, animacy, etc.)
    notes: List[str] = []  # Additional notes about the word
    example_sentence: Optional[str] = None
    explanation: Optional[str] = None  # Detailed explanation of the word (can be several sentences)
    is_irrelevant: bool = False  # True if word is a name, proper noun, or irrelevant for vocabulary learning


class GPTCaller:
    """Handles OpenAI API calls for vocabulary-related tasks."""
    
    def __init__(self, api_key: Optional[str] = None, api_key_file: str = "apikey.txt"):
        """
        Initialize the GPT caller.
        
        Args:
            api_key: OpenAI API key. If not provided, will try to read from file or environment variable.
            api_key_file: Path to file containing API key (default: "apikey.txt")
        """
        # Priority: provided key > file > environment variable
        if not api_key:
            # Try to read from file
            if os.path.exists(api_key_file):
                try:
                    with open(api_key_file, 'r') as f:
                        api_key = f.read().strip()
                except Exception as e:
                    print(f"Warning: Could not read API key from {api_key_file}: {e}")
            
            # Fall back to environment variable
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError(
                f"OpenAI API key is required. "
                f"Set OPENAI_API_KEY environment variable, provide it as argument, "
                f"or create {api_key_file} file with the API key."
            )
        
        self.client = OpenAI(api_key=api_key)
        # Model that supports Structured Outputs (gpt-4o-2024-08-06 and later)
        self.model = "gpt-4o-mini"
    
    def _handle_response(self, response, expected_type):
        """
        Handle the API response, checking for errors and refusals.
        
        Args:
            response: The API response object
            expected_type: The expected Pydantic model type
            
        Returns:
            Parsed output if successful
            
        Raises:
            ValueError: If the response indicates a refusal or error
        """
        # Check if the response was completed successfully
        if hasattr(response, 'status'):
            if response.status == "incomplete":
                reason = getattr(response.incomplete_details, 'reason', 'unknown') if hasattr(response, 'incomplete_details') else 'unknown'
                if reason == "max_output_tokens":
                    raise ValueError("Response was truncated due to token limit. Try simplifying the request.")
                elif reason == "content_filter":
                    raise ValueError("Response was filtered due to content restrictions.")
                else:
                    raise ValueError(f"Response incomplete: {reason}")
        
        # Check for refusal in output content
        if hasattr(response, 'output') and response.output:
            first_output = response.output[0] if isinstance(response.output, list) else response.output
            if hasattr(first_output, 'content') and first_output.content:
                first_content = first_output.content[0] if isinstance(first_output.content, list) else first_output.content
                if hasattr(first_content, 'type') and first_content.type == "refusal":
                    refusal_text = getattr(first_content, 'refusal', 'Request was refused')
                    raise ValueError(f"Model refused the request: {refusal_text}")
        
        # Return the parsed output
        if hasattr(response, 'output_parsed') and response.output_parsed is not None:
            return response.output_parsed
        
        raise ValueError("No valid output received from the API")
    
    def generate_word_analysis(
        self,
        lemma: str = "",
        translation: str = "",
        language: str = "unknown",
        context: Optional[str] = None,
        sentence_context: Optional[List[str]] = None,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None
    ) -> WordAnalysis:
        """
        Generate variants, properties, and example sentence for a word.
        GPT will automatically determine the part of speech and missing information.
        
        Args:
            lemma: The base form of the word (optional - GPT will determine if missing)
            translation: The translation of the word (optional - GPT will determine if missing)
            language: The language of the word (e.g., "Ukrainian", "Polish")
            context: Optional context about the song/lyrics to help with accurate translations
            sentence_context: Optional list of sentences where this word appears (for consistency with sentence translations)
        
        Returns:
            WordAnalysis object with variants, properties, and example sentence
        
        Note:
            At least one of lemma or translation must be provided.
        """
        if not lemma.strip() and not translation.strip():
            raise ValueError("At least one of lemma or translation must be provided")
        
        # Build the prompt based on what's provided
        context_note = ""
        if context:
            context_note = f"\n\nContext: {context}\n\nIMPORTANT: Use this context to provide translations that match the meaning and theme of the song/lyrics. The word may have a specific meaning or connotation in this context that differs from its general translation."
        
        sentence_note = ""
        if sentence_context:
            sentences_text = "\n".join([f"- {s}" for s in sentence_context[:3]])  # Limit to first 3 sentences
            sentence_note = f"""

ORIGINAL TEXT CONTEXT - This word appears in these sentences from the source text:
{sentences_text}

IMPORTANT: 
1. Use one of these sentences as the example_sentence field - this is the best example for this word!
2. FORMAT the example_sentence as: "Original sentence" — "Translation" (BOTH parts required)
3. The translation must match how the word is used in these sentences
4. Reference this context in the explanation"""
        
        # Use source/target languages if provided, otherwise fall back to language parameter
        source_lang = source_language or language
        target_lang = target_language or "English"
        
        if lemma.strip() and translation.strip():
            user_prompt = f"""Provide a complete linguistic analysis for:
Lemma: {lemma} ({source_lang})
Translation: {translation} ({target_lang})
Language pair: {source_lang} → {target_lang}{context_note}{sentence_note}"""
        elif lemma.strip():
            user_prompt = f"""Provide a complete linguistic analysis for:
Lemma: {lemma} ({source_lang})
Language pair: {source_lang} → {target_lang}{context_note}{sentence_note}

Note: The translation is not provided. Determine the most appropriate {target_lang} translation(s) for this {source_lang} word based on the context and how it's used in the sentences above."""
        else:  # only translation provided
            user_prompt = f"""Provide a complete linguistic analysis for:
Translation: {translation} ({target_lang})
Language pair: {source_lang} → {target_lang}{context_note}{sentence_note}

Note: The lemma is not provided. Determine the most appropriate {source_lang} base form (lemma) for this {target_lang} translation based on the context."""
        
        # Determine if SOURCE language is Slavic (Ukrainian/Polish - the language being practiced)
        # Variants are ALWAYS generated for Ukrainian/Polish words (the practice language)
        slavic_languages = ["Polish", "Ukrainian", "Russian", "Czech", "Slovak", "Bulgarian", "Serbian", "Croatian", "Slovenian"]
        is_slavic_source = source_lang in slavic_languages
        
        variants_instruction = ""
        if is_slavic_source:
            variants_instruction = f"""3. Variants (CRITICAL - REQUIRED for ALL {source_lang} words):
   
   For NOUNS - Generate ALL 14 case forms (7 cases × 2 numbers):
   Example for "батько" (father):
   - Nominative sg: батько, pl: батьки
   - Genitive sg: батька, pl: батьків
   - Dative sg: батькові/батьку, pl: батькам
   - Accusative sg: батька, pl: батьків
   - Instrumental sg: батьком, pl: батьками
   - Locative sg: батькові/батьку, pl: батьках
   - Vocative sg: батьку, pl: батьки
   
   For VERBS - Generate ALL tense/person forms (12+ forms):
   Example for "робити" (to do):
   - Present: роблю, робиш, робить, робимо, робите, роблять
   - Past: робив (m), робила (f), робило (n), робили (pl)
   - Imperative: роби, робіть
   - Infinitive: робити
   
   For ADJECTIVES - Generate case forms across genders (8+ forms):
   Example for "добрий" (good):
   - Nom: добрий (m), добра (f), добре (n), добрі (pl)
   - Gen: доброго (m/n), доброї (f), добрих (pl)
   - etc.
   
   For PRONOUNS - Generate ALL available case forms
   
   Each variant MUST include:
   - value: The {source_lang} form
   - translation: The {target_lang} translation for that specific form
   - Grammatical tags: case, number, gender, tense, person as applicable
   
   MINIMUM REQUIREMENTS:
   - Nouns: AT LEAST 10 variants (all major case forms)
   - Verbs: AT LEAST 10 variants (all conjugations)
   - Adjectives: AT LEAST 6 variants (gender/case forms)
   - Pronouns: AT LEAST 5 variants (all case forms)
   
   DO NOT SKIP VARIANTS. This is the most important data for language learning."""
        else:
            variants_instruction = """3. Variants: DO NOT generate variants for non-Slavic languages. Leave variants as an empty list []."""
        
        system_prompt = f"""You are a linguistic expert specializing in {source_lang} to {target_lang} translation.
Your task is to provide a complete linguistic analysis of words, filling in all available information:

IMPORTANT: Only mark as IRRELEVANT if the word is:
- A proper noun that is ONLY a personal name with no other meaning (like "Ярина" as just a name)
- Onomatopoeia or interjections that don't have meaningful translations
- Very rare or archaic words not useful for language learning

DO NOT mark as irrelevant:
- Common words that happen to be used in names (extract them as vocabulary)
- Words that are useful for language learning, even if they appear in names
- Pronouns, verbs, adjectives, nouns, adverbs - these are ALWAYS relevant

If the word is irrelevant, set is_irrelevant=true and you may leave other fields minimal

If the word IS relevant for vocabulary learning, provide ALL of the following (REQUIRED):

1. Part of Speech (pos): Determine the part of speech (noun, verb, adjective, adverb, pronoun, preposition, etc.)

2. Translations: List ALL common {target_lang} translations of the word

{variants_instruction}

4. Properties (REQUIRED): JSON object with ALL applicable properties:
   - For nouns: {{"gender": "masc/fem/neut", "animacy": "animate/inanimate"}}
   - For verbs: {{"aspect": "perfective/imperfective", "transitivity": "transitive/intransitive"}}
   - For adjectives: {{"type": "qualitative/relative"}}
   Include any other relevant linguistic properties

5. Notes: Any important notes about usage, common collocations, irregularities, etc.

6. Example sentence (REQUIRED): Provide a natural example sentence using this word in context.
   FORMAT: "{source_lang} sentence" — "{target_lang} translation"
   Example: "Як справи?" — "How are things?"
   The sentence MUST include both the original and its translation, separated by " — "

7. Explanation (REQUIRED): Provide a DETAILED explanation (3-5 sentences) that includes:
   - The core meaning of the word
   - Common contexts where it's used
   - Any nuances or cultural connotations
   - How it compares to similar words (if any)
   - Tips for remembering or using the word correctly

Be THOROUGH - every field must be filled with comprehensive data. This is for language learning, so more detail is better.

CRITICAL REMINDER: The variants field is the MOST IMPORTANT field for Slavic languages. Generate AT LEAST 10-14 variants for nouns, 10+ for verbs, 6+ for adjectives. Empty or minimal variants for Slavic words is NOT acceptable."""
        
        variants_note = ""
        if is_slavic_source:
            variants_note = """- variants: CRITICAL REQUIREMENT - You MUST generate comprehensive variants:
    
    * NOUNS: Generate ALL 14 forms (7 cases × singular + plural). Example for "батько":
      [{"value": "батько", "translation": "father", "case": "nom", "number": "sg"},
       {"value": "батьки", "translation": "fathers", "case": "nom", "number": "pl"},
       {"value": "батька", "translation": "of father", "case": "gen", "number": "sg"},
       {"value": "батьків", "translation": "of fathers", "case": "gen", "number": "pl"},
       ... all 14 forms]
    
    * VERBS: Generate 12+ forms (present 6 + past 4 + imperative 2). Example for "робити":
      [{"value": "роблю", "translation": "I do", "tense": "pres", "person": "1", "number": "sg"},
       {"value": "робиш", "translation": "you do", "tense": "pres", "person": "2", "number": "sg"},
       ... all forms]
    
    * ADJECTIVES: Generate 8+ forms across genders and cases
    
    * PRONOUNS: Generate all available case forms
    
    FAILURE TO GENERATE VARIANTS IS NOT ACCEPTABLE. Every noun, verb, adjective, and pronoun MUST have variants."""
        else:
            variants_note = "- variants: Leave as empty list [] - variants are ONLY generated for Slavic languages"
        
        user_prompt += f"""

YOU MUST fill in ALL fields with comprehensive data:

- is_irrelevant: Only true for pure personal names. Otherwise ALWAYS false.

- pos: The part of speech (noun, verb, adjective, adverb, pronoun, preposition, conjunction, particle, etc.)

- translations: List ALL common {target_lang} translations (at least 1-3 translations)

- {variants_note}

- properties: JSON object with ALL linguistic properties:
  * Nouns: gender, animacy, declension type
  * Verbs: aspect (perfective/imperfective), transitivity
  * Adjectives: type (qualitative/relative)
  Include any special properties

- notes: Important usage notes, common collocations, irregularities (provide at least one note)

- example_sentence: REQUIRED - A natural example sentence using this word. FORMAT: "{source_lang} sentence" — "{target_lang} translation" (e.g., "Як справи?" — "How are things?"). MUST include both original and translation separated by " — "

- explanation: REQUIRED - A DETAILED explanation (3-5 sentences) covering:
  * The core meaning and usage
  * Common contexts and collocations
  * Cultural connotations or nuances
  * Tips for learners
  This must be substantive and helpful for language learning."""
        
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                text_format=WordAnalysis,
                max_output_tokens=8000  # Ensure enough tokens for comprehensive variants
            )
            
            result = self._handle_response(response, WordAnalysis)
            
            # Debug: Log if variants were not generated for Slavic words
            if is_slavic_source and len(result.variants) < 5:
                print(f"WARNING: Only {len(result.variants)} variants generated for '{lemma}' (expected 10+). Source language: {source_lang}")
            
            return result
            
        except ValueError:
            raise  # Re-raise ValueError as-is
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")
    
    def generate_variants_only(
        self,
        lemma: str,
        translation: str,
        language: str = "unknown",
        max_variants: int = 5
    ) -> List[VariantData]:
        """
        Generate only variants for a word (simpler use case).
        
        Args:
            lemma: The base form of the word
            translation: The translation of the word
            language: The language of the word
            max_variants: Maximum number of variants to generate
        
        Returns:
            List of VariantData objects
        """
        class VariantsOnly(BaseModel):
            variants: List[VariantData]
        
        system_prompt = f"""You are a linguistic expert specializing in {language} language.
Generate common grammatical variants (inflected forms) for the given word.
For each variant, provide the variant form and its translation.
Include grammatical tags if relevant (case, number, tense, person, etc.)."""
        
        user_prompt = f"""Generate up to {max_variants} common variants for:
Word: {lemma}
Translation: {translation}
Language: {language}"""
        
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                text_format=VariantsOnly
            )
            
            result = self._handle_response(response, VariantsOnly)
            return result.variants
            
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")
    
    def generate_example_sentence(
        self,
        lemma: str,
        translation: str,
        language: str = "unknown"
    ) -> str:
        """
        Generate an example sentence using the word.
        
        Args:
            lemma: The base form of the word
            translation: The translation of the word
            language: The language of the word
        
        Returns:
            Example sentence as a string
        """
        class ExampleSentence(BaseModel):
            model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
            
            sentence: str
            translation: str
        
        system_prompt = f"""You are a language teacher. Create a natural example sentence using the given word in {language}."""
        
        user_prompt = f"""Create an example sentence using:
Word: {lemma}
Translation: {translation}
Language: {language}

Provide the sentence in {language} and its English translation."""
        
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                text_format=ExampleSentence
            )
            
            result = self._handle_response(response, ExampleSentence)
            return f"{result.sentence} ({result.translation})"
            
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")
    
    def generate_sentence_translation(
        self,
        sentence: str,
        language: str = "unknown",
        context: Optional[str] = None
    ):
        """
        Translate a sentence from the source language to English.
        
        Args:
            sentence: The sentence to translate
            language: The source language
            context: Optional context about the song/lyrics to help with accurate translation
        
        Returns:
            SentenceTranslation object with translation
        """
        class SentenceTranslation(BaseModel):
            model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
            
            translation: str
        
        system_prompt = f"""You are a translator specializing in {language}. 
Translate the given sentence to English accurately while maintaining natural phrasing."""
        
        context_note = ""
        if context:
            context_note = f"\n\nContext: {context}\n\nIMPORTANT: Use this context to provide a translation that matches the meaning, theme, and style of the song/lyrics. The translation should reflect the specific context rather than just a literal translation."
        
        user_prompt = f"""Translate this {language} sentence to English:
"{sentence}"{context_note}

Provide a natural, accurate translation that fits the context."""
        
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                text_format=SentenceTranslation
            )
            
            return self._handle_response(response, SentenceTranslation)
            
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")

    def extract_vocabulary_from_text(
        self,
        text: str,
        language: str,
        context: Optional[str] = None,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None
    ):
        """
        Extract vocabulary word pairs from any text - songs, word lists, textbook excerpts, articles, etc.
        GPT intelligently parses the text and extracts useful vocabulary items.
        
        Args:
            text: Any text content to extract vocabulary from
            language: The language of the source text
            context: Optional context to help with accurate translations
        
        Returns:
            ExtractedVocabulary object with words and sentences
        """
        class VocabularyItem(BaseModel):
            model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
            
            lemma: str  # Base form of the word
            translation: str  # English translation
            notes: Optional[str] = None  # Any notes (from textbook, context, etc.)
        
        class ExtractedSentence(BaseModel):
            model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
            
            text: str  # Original sentence
            translation: str  # English translation
        
        class ExtractedVocabulary(BaseModel):
            model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
            
            words: List[VocabularyItem]
            sentences: List[ExtractedSentence]
        
        context_note = ""
        if context:
            context_note = f"\n\nAdditional context: {context}"
        
        # Use source/target languages if provided, otherwise fall back to language parameter
        source_lang = source_language or language
        target_lang = target_language or "English"
        
        system_prompt = f"""You are a language learning expert specializing in {source_lang} to {target_lang} translation.
Your task is to extract vocabulary items from text for language learning purposes.

The source text is in {source_lang} and should be translated to {target_lang}.

The text could be in ANY format:
- Song lyrics (extract unique words + lines as sentences)
- Word lists (one word per line)
- Textbook excerpts (may have word – translation pairs already)
- Articles or stories (extract key vocabulary)
- Mixed content

CRITICAL RULES:
1. PRESERVE PHRASES: If the text contains phrases or expressions (like "До побачення!" or "будь ласка"), keep them as single vocabulary items - do NOT break them into individual words
2. RECOGNIZE EXISTING TRANSLATIONS: If the text has "word – translation" or "word = translation" format, extract the EXACT word/phrase with its given translation
3. Extract ALL UNIQUE vocabulary items (no duplicates) - be comprehensive, extract common words too
4. Use the lemma (dictionary/base form) for single words, but KEEP PHRASES intact
5. ONLY skip: proper nouns that are clearly just names (like "Ярина", "Роксоляна", "Оксана", "Володимир") - but DO extract common words even if they appear in names
6. Extract ALL common vocabulary words from dialogues, conversations, and text - be thorough
7. For sentences: Include all meaningful sentences from dialogues, conversations, etc.
8. IMPORTANT: Extract words like "ти", "ви", "я", "ми", "це", "моя", "мій", "добре", "дякую", "привіт", "справи", "куди", "додому", "бувай", "побачення" - these are essential vocabulary

EXAMPLES:
- "будь ласка – please" → word: "будь ласка", translation: "please" (DON'T split into "будь" and "ласка")
- "До побачення! – Goodbye!" → word: "До побачення!", translation: "Goodbye!"
- Song line "Я тебе кохаю" → sentence with translation, PLUS individual words if not phrase-based

OUTPUT:
- words: List of vocabulary items (lemma/phrase + translation + optional notes)
- sentences: List of meaningful sentences with translations (if present in the text)"""

        user_prompt = f"""Extract vocabulary from this {source_lang} text (translate to {target_lang}):{context_note}

---
{text}
---

Extract:
1. ALL unique vocabulary words (lemmas) with their {target_lang} translations - be comprehensive and extract common words too
2. Any meaningful sentences with their {target_lang} translations (if present in the text)

ONLY skip: proper nouns that are clearly just personal names (like "Ярина", "Роксоляна"). 
DO extract: all common words, pronouns, verbs, adjectives, nouns, adverbs, prepositions, etc.
Use base/dictionary forms for words. Be thorough - extract as many vocabulary items as possible from the text."""

        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                text_format=ExtractedVocabulary
            )
            
            return self._handle_response(response, ExtractedVocabulary)
            
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")


def convert_to_word_class(analysis: WordAnalysis, lemma: str) -> dict:
    """
    Convert WordAnalysis to a format compatible with the Word class from word.py.
    
    Args:
        analysis: WordAnalysis object from GPT
        lemma: The lemma (base form) of the word
    
    Returns:
        Dictionary with structure matching Word class:
        {
            'lemma': str,
            'pos': str,
            'translations': list[str],
            'variants': list[dict with 'value', 'translation', 'tags'],
            'properties': dict,
            'notes': list[str],
            'example_sentence': str or None
        }
    """
    import json
    
    # Parse properties from JSON string
    try:
        properties = json.loads(analysis.properties) if analysis.properties else {}
    except:
        properties = {}
    
    # Convert variants to dict format matching Word.Variant
    variants = []
    for variant in analysis.variants:
        tags = {}
        if variant.case:
            tags['case'] = variant.case
        if variant.number:
            tags['number'] = variant.number
        if variant.gender:
            tags['gender'] = variant.gender
        if variant.tense:
            tags['tense'] = variant.tense
        if variant.person:
            tags['person'] = variant.person
        if variant.aspect:
            tags['aspect'] = variant.aspect
        if variant.animacy:
            tags['animacy'] = variant.animacy
        
        variants.append({
            'value': variant.value,
            'translation': variant.translation,
            'tags': tags
        })
    
    return {
        'lemma': lemma,
        'pos': analysis.pos,
        'translations': analysis.translations,
        'variants': variants,
        'properties': properties,
        'notes': analysis.notes,
        'example_sentence': analysis.example_sentence,
        'explanation': analysis.explanation
    }


# Convenience function for easy importing
def get_gpt_caller(api_key: Optional[str] = None, api_key_file: str = "apikey.txt") -> GPTCaller:
    """
    Get a GPTCaller instance.
    
    Args:
        api_key: OpenAI API key (optional, will try file or environment variable if not provided)
        api_key_file: Path to file containing API key (default: "apikey.txt")
    
    Returns:
        GPTCaller instance
    """
    return GPTCaller(api_key=api_key, api_key_file=api_key_file)