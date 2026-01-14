class Word:
    def __init__(self, lemma: str, pos: str):
        self._lemma = lemma
        self._pos = pos              # noun, verb, adj, etc.

        self._translations = []
        self._variants = []
        self._properties = {}        # gender, animacy, aspect, etc.
        self._notes = []
        self._example_sentence = None

    # -------------------
    # Basic getters
    # -------------------

    @property
    def lemma(self) -> str:
        return self._lemma

    @property
    def language(self) -> str:
        return self._language

    @property
    def pos(self) -> str:
        return self._pos

    @property
    def translations(self) -> list:
        return list(self._translations)

    @property
    def variants(self) -> list:
        return list(self._variants)

    @property
    def properties(self) -> dict:
        return dict(self._properties)

    @property
    def notes(self) -> list:
        return list(self._notes)

    @property
    def example_sentence(self) -> str:
        return str(self._example_sentence)
    # -------------------
    # Setters / mutators
    # -------------------

    def set_lemma(self, lemma: str):
        self._lemma = lemma

    def set_pos(self, pos: str):
        self._pos = pos

    # -------------------
    # Translations
    # -------------------

    def add_translation(self, translation: str):
        if translation not in self._translations:
            self._translations.append(translation)

    def remove_translation(self, translation: str):
        if translation in self._translations:
            self._translations.remove(translation)

    # -------------------
    # Properties (non-testable facts)
    # -------------------

    def set_property(self, key: str, value):
        self._properties[key] = value

    def get_property(self, key: str, default=None):
        return self._properties.get(key, default)

    def remove_property(self, key: str):
        self._properties.pop(key, None)

    # -------------------
    # Variants (testable forms)
    # -------------------

    def add_variant(self, value: str, translation: str, **tags):
        self._variants.append(Variant(value, translation, tags))

    def remove_variant(self, value: str):
        self._variants = [v for v in self._variants if v.value != value]

    def get_variants(self, **criteria) -> list:
        return [v for v in self._variants if v.matches(**criteria)]

    def has_variant(self, **criteria) -> bool:
        return any(v.matches(**criteria) for v in self._variants)

    # -------------------
    # Notes
    # -------------------

    def add_note(self, note: str):
        self._notes.append(note)


class Variant:
    def __init__(self, value: str, translation: str, tags: dict):
        self.value = value
        self.translation = translation
        self.tags = tags

    def matches(self, **criteria) -> bool:
        return all(self.tags.get(k) == v for k, v in criteria.items())


