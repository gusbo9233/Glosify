"""
GPT caller for generating vocabulary word pairs from learning prompts.
This is Stage 1: Prompt → Word List
Stage 2 uses existing gptcaller.py or gptcaller_polish.py for full analysis.
"""

from openai import OpenAI
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
import os


class PromptWordPair(BaseModel):
    """A word pair generated from a prompt."""
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
    
    lemma: str  # Base form in source language (Polish/Ukrainian)
    translation: str  # Translation in target language (English/Swedish)
    notes: Optional[str] = None  # Optional notes about the word


class PromptVocabulary(BaseModel):
    """Vocabulary generated from a prompt."""
    model_config = ConfigDict(json_schema_extra={"additionalProperties": False})
    
    words: List[PromptWordPair]


class GPTCallerPrompt:
    """Handles GPT calls for prompt-based vocabulary generation."""
    
    def __init__(self, api_key: Optional[str] = None, api_key_file: str = "apikey.txt"):
        """Initialize the GPT caller."""
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
    
    def generate_vocabulary_from_prompt(
        self,
        prompt: str,
        source_language: str,
        target_language: str
    ) -> PromptVocabulary:
        """
        Generate vocabulary word pairs from a learning prompt.
        
        Args:
            prompt: User's learning goal (e.g., "I want to practice Polish verbs 'to have' and 'to be'")
            source_language: The language being learned (Polish/Ukrainian)
            target_language: The language user knows (English/Swedish)
        
        Returns:
            PromptVocabulary with list of word pairs
        """
        system_prompt = f"""You are a language learning expert specializing in {source_language} to {target_language} vocabulary generation.

Your task is to generate a comprehensive list of vocabulary word pairs based on a user's learning prompt.

CRITICAL RULES:
1. Generate ALL relevant vocabulary words for the given prompt
2. Use the base form (lemma) for words in {source_language}:
   - For verbs: Use the infinitive form (e.g., "mieć" not "mam", "бути" not "є")
   - For nouns: Use the nominative singular form
   - For adjectives: Use the masculine nominative singular form
3. Provide accurate {target_language} translations
4. Be comprehensive - if the prompt mentions a category, include all commonly learned words in that category
5. Include related vocabulary that would naturally be learned together
6. For verb prompts: Include the infinitive forms, not conjugated forms
7. Think about what vocabulary a learner would need to practice this topic effectively

EXAMPLES:
- Prompt: "Polish verbs 'to have' and 'to be'"
  → Generate: mieć → to have, być → to be
  
- Prompt: "Ukrainian family members"
  → Generate: батько → father, мати → mother, сестра → sister, брат → brother, дідусь → grandfather, бабуся → grandmother, etc.
  
- Prompt: "Polish numbers 1-20"
  → Generate: jeden → one, dwa → two, trzy → three, cztery → four, pięć → five, etc.

- Prompt: "Ukrainian colors"
  → Generate: червоний → red, синій → blue, зелений → green, жовтий → yellow, etc.

OUTPUT:
- words: List of word pairs (lemma in {source_language}, translation in {target_language})
- Include notes if helpful (e.g., "irregular verb", "plural form", etc.)"""

        user_prompt = f"""Generate vocabulary word pairs for this learning goal:

"{prompt}"

Language pair: {source_language} → {target_language}

Generate a comprehensive list of all relevant vocabulary words. Be thorough and include all words that would naturally be part of learning this topic. Use base forms (infinitive for verbs, nominative singular for nouns)."""

        try:
            response = self.client.responses.parse(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                text_format=PromptVocabulary
            )
            
            return self._handle_response(response, PromptVocabulary)
            
        except ValueError:
            raise
        except Exception as e:
            raise Exception(f"Error calling OpenAI API: {str(e)}")


def get_gpt_caller_prompt(api_key: Optional[str] = None, api_key_file: str = "apikey.txt") -> GPTCallerPrompt:
    """Get a GPTCallerPrompt instance."""
    return GPTCallerPrompt(api_key=api_key, api_key_file=api_key_file)
