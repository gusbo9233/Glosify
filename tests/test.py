# -----------------------------------
# 1. Create Word objects with variants
# -----------------------------------
from word import Word
from quiz import Quiz
# Ukrainian noun
stol = Word("стіл", "noun")
stol.add_translation("table")
stol.set_property("gender", "masc")
stol.set_property("animacy", "inanimate")

stol.add_variant("стіл", "table", number="sg", case="nom")
stol.add_variant("столу", "table", number="sg", case="gen")
stol.add_variant("столи", "tables", number="pl", case="nom")

# Polish verb
pisac = Word("pisać", "verb")
pisac.add_translation("to write")
pisac.set_property("aspect", "impf")

pisac.add_variant("piszę", "I write", tense="pres", person=1, number="sg")
pisac.add_variant("pisaliśmy", "we wrote", tense="past", number="pl", gender="masc_personal")

# -----------------------------------
# 2. Create a Quiz and add words
# -----------------------------------

quiz = Quiz("Slavic Practice")
quiz.add_word(stol)
quiz.add_word(pisac)

# -----------------------------------
# 3. Configure Quiz settings (filters)
# -----------------------------------

# Only allow genitive forms for nouns
quiz.allow(case="gen")

# Exclude plural forms
quiz.exclude(number="pl")

# -----------------------------------
# 4. Fill active words based on settings
# -----------------------------------

quiz.fill_active_words()

# -----------------------------------
# 5. Loop through active words and variants
# -----------------------------------

for entry in quiz.active_words:
    word_obj = entry["word"]
    variants = entry["variants"]

    print(f"\nPractice word: {word_obj.lemma}")
    print("Translations:", ", ".join(word_obj.translations))

    for variant in variants:
        # Simulate user input (replace with actual input in real app)
        user_input = variant.value  # here we simulate correct answer
        print(f"Provide the form for tags: {variant.tags}")
        print(f"Translation: {variant.translation}")
        print("User typed:", user_input)

        # Check answer
        if user_input == variant.value:
            print("Correct!")
        else:
            print(f"Incorrect! Correct answer: {variant.value}")
