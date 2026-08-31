"""
Controlled vocabulary for RB-01 / ML-01 intent extraction.

Per proposal section 4.1: "a rule-based intent extraction module that
identifies relevant context tags such as cuisine preference, dietary
requirements, meal type, occasion, and cooking constraints."

All three extraction tiers (Gemma, Sentence Transformer, rule-based) map
free-text queries onto THIS SAME controlled vocabulary, so their outputs
are directly comparable and interchangeable by the pipeline. The vocab
values below are drawn from the actual tags/course fields used across the
100 SL-Cook100 recipes, so every tag here has real matching recipes.
"""

# category -> {canonical_tag: [keywords / example phrases for that tag]}
# The keyword lists double as (a) rule-based regex triggers and
# (b) example phrases the embedding tier compares the query against.
INTENT_VOCAB = {
    "meal_type": {
        "breakfast": ["breakfast", "morning meal", "brekkie"],
        "lunch": ["lunch", "midday meal"],
        "dinner": ["dinner", "evening meal", "supper"],
        "snack": ["snack", "quick bite", "something small"],
        "dessert": ["dessert", "sweet treat", "something sweet"],
    },
    "dietary": {
        "vegetarian": ["vegetarian", "veggie", "no meat"],
        "vegan": ["vegan", "plant based", "plant-based", "no dairy no meat"],
        "gluten-free": ["gluten free", "gluten-free", "no gluten", "celiac"],
        "dairy-free": ["dairy free", "dairy-free", "no dairy", "lactose free"],
    },
    "spice_level": {
        "very-spicy": ["very spicy", "extra hot", "fiery", "super spicy"],
        "spicy": ["spicy", "hot", "with a kick", "chilli heat"],
        "mild": ["mild", "not spicy", "nothing spicy", "no chilli", "low spice", "not too hot"],
    },
    "cooking_constraint": {
        "under-30-min": ["quick", "fast", "under 30 minutes", "in a hurry", "30 minutes or less"],
        "30-60-min": ["about an hour", "30 to 60 minutes"],
        "over-60-min": ["slow cooked", "takes a while", "weekend project", "over an hour"],
        "meal-prep-friendly": ["meal prep", "make ahead", "batch cook", "meal-prep friendly"],
    },
    "occasion": {
        "festival": ["festival", "avurudu", "new year", "celebration", "festive"],
        "everyday": ["everyday", "weeknight", "casual", "regular meal"],
        "crowd-pleaser": ["for a crowd", "party", "guests", "crowd pleaser"],
        "wedding": ["wedding"],
        "street-food": ["street food", "street-food style"],
    },
    "cuisine": {
        "sri-lankan": ["sri lankan", "sri lanka", "local", "ceylon"],
    },
}

# Recognized protein/course-adjacent keywords, used by the recommender's
# ingredient-overlap scoring, not by intent-tag extraction directly.
KNOWN_INGREDIENT_HINTS = [
    "chicken", "prawns", "prawn", "fish", "beef", "pork", "egg", "eggs",
    "coconut milk", "lentil", "dhal", "dal", "jackfruit", "eggplant", "brinjal",
    "potato", "cashew", "mango", "pumpkin",
]


def all_tags_flat():
    """Every canonical tag across all categories, as a flat list."""
    out = []
    for cat, tags in INTENT_VOCAB.items():
        out.extend(tags.keys())
    return out
