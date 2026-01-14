import random
import uuid


class Quiz:
    def __init__(self, name: str):
        self.name = name
        self.uid = str(uuid.uuid4())
        self.words = []
        self.sentences = []
        self.active_words = []

        # Settings for filtering variants
        self.allowed_tags = {}
        self.excluded_tags = {}
        self.max_variants_per_word = None
        self.randomize = True

    # ---------- Existing methods ----------

    def add_word(self, word):
        self.words.append(word)

    def add_sentence(self, sentence):
        self.sentences.append(sentence)

    def get_sentences(self):
        return self.sentences

    def get_words(self):
        return self.words

    def allow(self, **tags):
        self.allowed_tags.update(tags)

    def exclude(self, **tags):
        self.excluded_tags.update(tags)

    def clear_filters(self):
        self.allowed_tags.clear()
        self.excluded_tags.clear()

    def _variant_allowed(self, variant) -> bool:
        for k, v in self.allowed_tags.items():
            if variant.tags.get(k) != v:
                return False
        for k, v in self.excluded_tags.items():
            if variant.tags.get(k) == v:
                return False
        return True

    def get_variants_for_word(self, word):
        variants = [v for v in word.variants if self._variant_allowed(v)]
        if self.randomize:
            random.shuffle(variants)
        if self.max_variants_per_word:
            variants = variants[:self.max_variants_per_word]
        return variants

    def fill_active_words(self):
        self.active_words = []
        for word in self.words:
            allowed_variants = self.get_variants_for_word(word)
            if allowed_variants:
                self.active_words.append({
                    "word": word,
                    "variants": allowed_variants
                })

    # ---------- New methods ----------

    def generate_mc_question(self, num_options=4):
        """
        Generate a multiple-choice question.
        Returns a dict:
        {
            "word": Word object,
            "question_variant": Variant object,
            "options": list of strings (shuffled),
            "correct_answer": string
        }
        """
        if not self.active_words:
            self.fill_active_words()
            if not self.active_words:
                return None  # no variants available

        # Pick a random word entry
        word_entry = random.choice(self.active_words)
        # Pick a random variant for the question
        question_variant = random.choice(word_entry["variants"])
        correct_answer = question_variant.value

        # Collect distractors
        distractors = []

        # Use other variants from same word first
        for v in word_entry["variants"]:
            if v.value != correct_answer:
                distractors.append(v.value)

        # If needed, use variants from other words
        if len(distractors) < num_options - 1:
            for entry in self.active_words:
                if entry == word_entry:
                    continue
                for v in entry["variants"]:
                    if v.value != correct_answer and v.value not in distractors:
                        distractors.append(v.value)
                        if len(distractors) >= num_options - 1:
                            break
                if len(distractors) >= num_options - 1:
                    break

        # Take exactly num_options-1 distractors
        distractors = distractors[:num_options-1]

        # Combine and shuffle options
        options = distractors + [correct_answer]
        random.shuffle(options)

        return {
            "word": word_entry["word"],
            "question_variant": question_variant,
            "options": options,
            "correct_answer": correct_answer
        }

    def check_answer(self, selected_option: str, question: dict) -> bool:
        """
        Returns True if the selected_option matches the correct answer.
        """
        return selected_option == question["correct_answer"]
