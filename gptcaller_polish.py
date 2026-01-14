"""
OpenAI API caller for generating Polish-English word pairs, variants, and example sentences.
Tailored specifically for Polish language learning.

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
    case: Optional[str] = None  # e.g., "nom", "gen", "dat", "acc", "inst", "loc", "voc"
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
    explanation: Optional[str] = None
    is_irrelevant: bool = False


class GPTCallerPolish:
    """Handles OpenAI API calls for Polish-English vocabulary tasks."""
    
    def __init__(self, api_key: Optional[str] = None, api_key_file: str = "apikey.txt"):
        """
        Initialize the GPT caller.
        
        Args:
            api_key: OpenAI API key. If not provided, will try to read from file or environment variable.
            api_key_file: Path to file containing API key (default: "apikey.txt")
        """
        if not api_key:
            if os.path.exists(api_key_file):
                try:
                    with open(api_key_file, 'r') as f:
                        api_key = f.read().strip()
                except Exception as e:
                    print(f"Warning: Could not read API key from {api_key_file}: {e}")
            
            if not api_key:
                api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError(
                f"OpenAI API key is required. "
                f"Set OPENAI_API_KEY environment variable, provide it as argument, "
                f"or create {api_key_file} file with the API key."
            )
        
        self.client = OpenAI(api_key=api_key)
        self.model = "gpt-4o-mini"
    
    def _handle_response(self, response, expected_type):
        """Handle the API response, checking for errors and refusals."""
        if hasattr(response, 'status'):
            if response.status == "incomplete":
                reason = getattr(response.incomplete_details, 'reason', 'unknown') if hasattr(response, 'incomplete_details') else 'unknown'
                if reason == "max_output_tokens":
                    raise ValueError("Response was truncated due to token limit. Try simplifying the request.")
                elif reason == "content_filter":
                    raise ValueError("Response was filtered due to content restrictions.")
                else:
                    raise ValueError(f"Response incomplete: {reason}")
        
        if hasattr(response, 'output') and response.output:
            first_output = response.output[0] if isinstance(response.output, list) else response.output
            if hasattr(first_output, 'content') and first_output.content:
                first_content = first_output.content[0] if isinstance(first_output.content, list) else first_output.content
                if hasattr(first_content, 'type') and first_content.type == "refusal":
                    refusal_text = getattr(first_content, 'refusal', 'Request was refused')
                    raise ValueError(f"Model refused the request: {refusal_text}")
        
        if hasattr(response, 'output_parsed') and response.output_parsed is not None:
            return response.output_parsed
        
        raise ValueError("No valid output received from the API")
    
    def generate_word_analysis(
        self,
        lemma: str = "",
        translation: str = "",
        language: str = "Polish",
        context: Optional[str] = None,
        sentence_context: Optional[List[str]] = None,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None
    ) -> WordAnalysis:
        """
        Generate variants, properties, and example sentence for a Polish word.
        """
        if not lemma.strip() and not translation.strip():
            raise ValueError("At least one of lemma or translation must be provided")
        
        context_note = ""
        if context:
            context_note = f"\n\nContext: {context}"
        
        sentence_note = ""
        if sentence_context:
            sentences_text = "\n".join([f"- {s}" for s in sentence_context[:3]])
            sentence_note = f"""

ORIGINAL TEXT CONTEXT - This word appears in these sentences:
{sentences_text}

IMPORTANT: 
1. Use one of these sentences as the example_sentence field
2. FORMAT the example_sentence as: "Original sentence" — "Translation" (BOTH parts required)
3. The translation must match how the word is used in these sentences
4. Reference this context in the explanation"""
        
        source_lang = source_language or "Polish"
        target_lang = target_language or "English"
        
        if lemma.strip() and translation.strip():
            user_prompt = f"""Provide a complete linguistic analysis for:
Polish word: {lemma}
English translation: {translation}{context_note}{sentence_note}"""
        elif lemma.strip():
            user_prompt = f"""Provide a complete linguistic analysis for:
Polish word: {lemma}{context_note}{sentence_note}

Provide the English translation(s) for this Polish word."""
        else:
            user_prompt = f"""Provide a complete linguistic analysis for:
English word: {translation}{context_note}{sentence_note}

Provide the Polish equivalent (lemma) for this English word."""
        
        # Polish is always Slavic, so always generate variants
        variants_instruction = """3. Variants (CRITICAL - REQUIRED for Polish words):
   
   For NOUNS - Generate ALL 14 case forms (7 cases × 2 numbers):
   Example for "okno" (window):
   - Nominative sg: okno, pl: okna
   - Genitive sg: okna, pl: okien
   - Dative sg: oknu, pl: oknom
   - Accusative sg: okno, pl: okna
   - Instrumental sg: oknem, pl: oknami
   - Locative sg: oknie, pl: oknach
   - Vocative sg: okno, pl: okna
   
   For VERBS - Generate ALL tense/person forms (12+ forms):
   Example for "zamykać" (to close):
   - Present: zamykam, zamykasz, zamyka, zamykamy, zamykacie, zamykają
   - Past: zamykałem/łam (m/f), zamykałeś/łaś, zamykał/ła/ło, zamykaliśmy/łyśmy, zamykaliście/łyście, zamykali/ły
   - Imperative: zamykaj, zamykajcie
   
   For ADJECTIVES - Generate case forms across genders (8+ forms):
   Example for "dobry" (good):
   - Nom: dobry (m), dobra (f), dobre (n), dobrzy/dobre (pl)
   - Gen: dobrego (m/n), dobrej (f), dobrych (pl)
   
   Each variant MUST include:
   - value: The Polish form
   - translation: The English translation for that specific form
   - Grammatical tags: case, number, gender, tense, person as applicable
   
   MINIMUM REQUIREMENTS:
   - Nouns: AT LEAST 10 variants (all major case forms)
   - Verbs: AT LEAST 10 variants (all conjugations)
   - Adjectives: AT LEAST 6 variants (gender/case forms)
   - Pronouns: AT LEAST 5 variants (all case forms)
   
   DO NOT SKIP VARIANTS. This is the most important data for Polish learning."""
        
        system_prompt = f"""You are a linguistic expert specializing in Polish to English translation.
Your task is to provide a complete linguistic analysis of Polish words.

IMPORTANT: Only mark as IRRELEVANT if the word is:
- A proper noun that is ONLY a personal name with no other meaning
- Onomatopoeia or interjections that don't have meaningful translations
- Very rare or archaic words not useful for language learning

DO NOT mark as irrelevant:
- Common words, even if they appear in names
- Pronouns, verbs, adjectives, nouns, adverbs - these are ALWAYS relevant

If the word IS relevant for vocabulary learning, provide ALL of the following (REQUIRED):

1. Part of Speech (pos): Determine the part of speech (noun, verb, adjective, adverb, pronoun, preposition, etc.)

2. Translations: List ALL common English translations of the Polish word

{variants_instruction}

4. Properties (REQUIRED): JSON object with ALL applicable properties:
   - For nouns: {{"gender": "masc/fem/neut", "animacy": "animate/inanimate"}}
   - For verbs: {{"aspect": "perfective/imperfective", "transitivity": "transitive/intransitive"}}
   - For adjectives: {{"type": "qualitative/relative"}}
   Include any other relevant linguistic properties

5. Notes: Any important notes about usage, common collocations, irregularities, etc.

6. Example sentence (REQUIRED): Provide a natural example sentence using this word in context.
   FORMAT: "Polish sentence" — "English translation"
   Example: "Czy zamykasz okna?" — "Are you closing the windows?"
   The sentence MUST include both the original and its translation, separated by " — "

7. Explanation (REQUIRED): Provide a DETAILED explanation (3-5 sentences) that includes:
   - The core meaning of the word
   - Common contexts where it's used
   - Any nuances or cultural connotations
   - How it compares to similar words (if any)
   - Tips for remembering or using the word correctly

Be THOROUGH - every field must be filled with comprehensive data. This is for Polish language learning.

CRITICAL REMINDER: The variants field is the MOST IMPORTANT field. Generate AT LEAST 10-14 variants for nouns, 10+ for verbs, 6+ for adjectives. Empty or minimal variants is NOT acceptable."""
        
        variants_note = """- variants: CRITICAL REQUIREMENT - You MUST generate comprehensive variants:
    
    * NOUNS: Generate ALL 14 forms (7 cases × singular + plural). Example for "okno":
      [{"value": "okno", "translation": "window", "case": "nom", "number": "sg"},
       {"value": "okna", "translation": "windows", "case": "nom", "number": "pl"},
       {"value": "okna", "translation": "of window", "case": "gen", "number": "sg"},
       {"value": "okien", "translation": "of windows", "case": "gen", "number": "pl"},
       ... all 14 forms]
    
    * VERBS: Generate 12+ forms (present 6 + past 4 + imperative 2). Example for "zamykać":
      [{"value": "zamykam", "translation": "I close", "tense": "pres", "person": "1", "number": "sg"},
       {"value": "zamykasz", "translation": "you close", "tense": "pres", "person": "2", "number": "sg"},
       ... all forms]
    
    * ADJECTIVES: Generate 8+ forms across genders and cases
    
    * PRONOUNS: Generate all available case forms
    
    FAILURE TO GENERATE VARIANTS IS NOT ACCEPTABLE. Every noun, verb, adjective, and pronoun MUST have variants."""
        
        user_prompt += f"""

YOU MUST fill in ALL fields with comprehensive data:

- is_irrelevant: Only true for pure personal names. Otherwise ALWAYS false.

- pos: The part of speech (noun, verb, adjective, adverb, pronoun, preposition, conjunction, particle, etc.)

- translations: List ALL common English translations (at least 1-3 translations)

- {variants_note}

- properties: JSON object with ALL linguistic properties:
  * Nouns: gender, animacy, declension type
  * Verbs: aspect (perfective/imperfective), transitivity
  * Adjectives: type (qualitative/relative)
  Include any special properties

- notes: Important usage notes, common collocations, irregularities (provide at least one note)

- example_sentence: REQUIRED - A natural example sentence using this word. FORMAT: "Polish sentence" — "English translation" (e.g., "Czy zamykasz okna?" — "Are you closing the windows?"). MUST include both original and translation separated by " — "

- explanation: REQUIRED - A DETAILED explanation (3-5 sentences) covering:
  * The core meaning and usage
  * Common contexts and collocations
  * Cultural connotations or nuances
  * Tips for learners
  This must be substantive and helpful for Polish language learning."""
        
        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                text_format=WordAnalysis,
                max_output_tokens=8000
            )
            
            result = self._handle_response(response, WordAnalysis)
            
            # Debug: Log if variants were not generated
            if len(result.variants) < 5:
                print(f"WARNING: Only {len(result.variants)} variants generated for '{lemma}' (expected 10+)")
            
            return result
            
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")

    def extract_vocabulary_from_text(
        self,
        text: str,
        language: str = "Polish",
        context: Optional[str] = None,
        source_language: Optional[str] = None,
        target_language: Optional[str] = None
    ):
        """
        Extract Polish-English vocabulary word pairs from text.
        Specifically designed for Polish textbook content.
        """
        class VocabularyItem(BaseModel):
            model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
            
            lemma: str  # Polish word (base form)
            translation: str  # English translation
            notes: Optional[str] = None
        
        class ExtractedSentence(BaseModel):
            model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
            
            text: str  # Polish sentence
            translation: str  # English translation
        
        class ExtractedVocabulary(BaseModel):
            model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
            
            words: List[VocabularyItem]
            sentences: List[ExtractedSentence]
        
        context_note = ""
        if context:
            context_note = f"\n\nAdditional context: {context}"
        
        system_prompt = """You are a Polish language learning expert. Your task is to extract Polish-English vocabulary pairs from text.

CRITICAL: You are creating POLISH-ENGLISH word pairs for learners.
- The "lemma" field MUST contain the POLISH word (in base/dictionary form)
- The "translation" field MUST contain the ENGLISH translation

IMPORTANT RULES FOR POLISH TEXTBOOK CONTENT:
1. Polish textbooks often show dialogues like:
   "Czy zamykacie okna?" (Polish question) followed by "Tak, zamykamy" (Polish answer)
   Then show English: "Are you closing the windows?" "Yes, we are."
   
   Extract: lemma="zamykać" (Polish verb), translation="to close" (English)
   NOT: lemma="zamykać", translation="zamykamy" (both Polish - WRONG!)

2. When you see a Polish sentence with its English translation:
   Extract the KEY Polish vocabulary word and its ENGLISH meaning

3. ALWAYS pair:
   - Polish word → English translation
   - NEVER: Polish word → Polish word
   - NEVER: English word → English word

4. Extract vocabulary from ALL useful words in the text:
   - Verbs: zamykać, mieć, być, etc. → to close, to have, to be
   - Nouns: okno, zadanie, etc. → window, exercise/task
   - Pronouns: ja, ty, my, wy, etc. → I, you, we, you (plural)
   - Adverbs: tak, nie, etc. → yes, no

5. For sentences, include Polish sentence + English translation

EXAMPLES:
Text: "Czy zamykacie okna? Are you closing the windows?"
Extract: lemma="zamykać", translation="to close" (infinitive form)
Extract: lemma="okno", translation="window"

Text: "Tak, zamykamy. Yes, we are."
Extract: lemma="tak", translation="yes"

Text: "Masz zadanie. You have the exercise."
Extract: lemma="mieć", translation="to have"
Extract: lemma="zadanie", translation="exercise, task"

OUTPUT FORMAT:
- words: List of {lemma: POLISH_WORD, translation: ENGLISH_TRANSLATION, notes: optional}
- sentences: List of {text: POLISH_SENTENCE, translation: ENGLISH_TRANSLATION}"""

        user_prompt = f"""Extract Polish-English vocabulary from this text:{context_note}

---
{text}
---

REMEMBER:
1. lemma = POLISH word (base form)
2. translation = ENGLISH meaning
3. NEVER create Polish-Polish or English-English pairs
4. Extract all useful vocabulary words
5. Include Polish sentences with their English translations

Extract vocabulary now:"""

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
    """
    import json
    
    try:
        properties = json.loads(analysis.properties) if analysis.properties else {}
    except:
        properties = {}
    
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


def get_gpt_caller_polish(api_key: Optional[str] = None, api_key_file: str = "apikey.txt") -> GPTCallerPolish:
    """Get a GPTCallerPolish instance."""
    return GPTCallerPolish(api_key=api_key, api_key_file=api_key_file)
