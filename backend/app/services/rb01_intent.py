"""
RB-01 -- Context & Intent Extraction.

Converts a natural-language query into a controlled set of context tags (cuisine,
course, dietary requirement, spice level, cooking method, occasion, equipment,
allergen, texture) across 142 canonical values.

PLACEMENT DECISION (do not leave ambiguous -- read this before wiring this module
into anything):

This module is NOT used as the recommend pipeline's rule-based fallback tier, and
should not be. That role is already filled by
`app/services/ml01/rule_based_extractor.py` (+ `app/services/ml01/vocab.py`), which
is already wired into `app/services/ml01/pipeline.py` as Tier 3 and already called
from `app/routers/recommend.py`. Concretely, that existing tier is the better fit
for the pipeline, for three independent reasons:

  1. Vocabulary alignment. `vocab.INTENT_VOCAB` (44 tags / 10 categories) was built
     directly from the tags that actually appear on SL-Cook100 recipes (see
     `data_sl_cook100/tag_vocabulary.json`) -- every tag it can extract has real
     matching recipes. This module's vocabulary (142 tags / 9 categories, including
     `equipment`, `allergen`, `texture`) has no corresponding fields anywhere on the
     `Recipe` model or in the dataset, so those categories could never match a real
     recipe's tags in `recommender.py`'s scoring -- they'd be extracted and then
     silently do nothing.
  2. Shape mismatch. `extract_intent` here returns one `str | None` per category
     (`ExtractedIntent`). The pipeline's `IntentResult.tags` is `dict[str, list]`,
     and `recommender.score_recipe`'s category weights key off of that list shape
     and off `vocab.INTENT_VOCAB`'s category names (`meal_type`, `cooking_constraint`,
     ...), which don't match this module's category names (`course`,
     `cooking_method`, ...). Adapting the shape doesn't fix the vocabulary mismatch
     in (1).
  3. Matching quality. `rule_based_extractor.py` does word-boundary regex matching
     and negation handling ("nothing spicy", "no dairy"); this module does plain
     substring matching with no negation handling, so it would be a strict
     regression if substituted in as the fallback tier.

Given that, this module is instead exposed as its own small, independent
filter-tag endpoint (`GET /api/tags/extract`, see `app/routers/tags.py`) --
useful anywhere the app wants a fast, dependency-free tag guess from free text
(e.g. suggesting filter chips as someone types a search) without touching
`/api/recommendations` or its scoring. It is deliberately NOT called from
`app/services/ml01/pipeline.py` or `app/routers/recommend.py`, and should stay
that way unless someone first reconciles its vocabulary with real recipe data
(at which point it could reasonably be merged into `vocab.INTENT_VOCAB` instead
of kept as a second, parallel vocabulary).
"""
import re
from dataclasses import dataclass, field

# Keep these vocabularies in sync with tag_vocabulary.json / your controlled tag list.
#
# Every dict maps a lowercase keyword variant (including plurals, common
# misspellings, and synonyms) to exactly one canonical display value, so
# downstream filtering only ever has to deal with the canonical set.

CUISINE_KEYWORDS = {
    # Sri Lankan
    "sri lankan": "Sri Lankan", "srilankan": "Sri Lankan", "lankan": "Sri Lankan",
    "sri lanka": "Sri Lankan",
    # Indian
    "indian": "Indian", "indain": "Indian",
    # Thai
    "thai": "Thai", "thailand": "Thai",
    # Chinese
    "chinese": "Chinese", "chinesse": "Chinese",
    # Italian
    "italian": "Italian", "itallian": "Italian",
    # Mexican
    "mexican": "Mexican", "mexcian": "Mexican",
    # Japanese
    "japanese": "Japanese", "japanase": "Japanese",
    # Korean
    "korean": "Korean",
    # Continental
    "continental": "Continental",
    # Mediterranean
    "mediterranean": "Mediterranean", "mediteranean": "Mediterranean",
    "meditteranean": "Mediterranean",
    # Middle Eastern
    "middle eastern": "Middle Eastern", "middle-eastern": "Middle Eastern",
    "arabic": "Middle Eastern", "arab": "Middle Eastern",
    # French
    "french": "French",
    # Vietnamese
    "vietnamese": "Vietnamese", "viet": "Vietnamese",
    # Filipino
    "filipino": "Filipino", "philippine": "Filipino", "philippino": "Filipino",
    # Greek
    "greek": "Greek",
    # Spanish
    "spanish": "Spanish",
    # American
    "american": "American",
    # Fusion
    "fusion": "Fusion",
    # Nepali
    "nepali": "Nepali", "nepalese": "Nepali",
    # Pakistani
    "pakistani": "Pakistani",
    # Bangladeshi
    "bangladeshi": "Bangladeshi", "bengali": "Bangladeshi",
    # Indonesian
    "indonesian": "Indonesian",
    # Malaysian
    "malaysian": "Malaysian",
    # Turkish
    "turkish": "Turkish",
    # Lebanese
    "lebanese": "Lebanese",
    # Ethiopian
    "ethiopian": "Ethiopian",
    # Caribbean
    "caribbean": "Caribbean",
    # Peruvian
    "peruvian": "Peruvian",
}
COURSE_KEYWORDS = {
    # Breakfast
    "breakfast": "Breakfast", "breakfasts": "Breakfast",
    # Lunch
    "lunch": "Lunch", "lunches": "Lunch",
    # Dinner
    "dinner": "Dinner", "dinners": "Dinner", "supper": "Dinner",
    # Snack
    "snack": "Snack", "snacks": "Snack",
    # Dessert
    "dessert": "Dessert", "desserts": "Dessert", "sweet": "Dessert", "sweets": "Dessert",
    # Starter
    "starter": "Starter", "starters": "Starter",
    # Side Dish
    "side dish": "Side Dish", "side-dish": "Side Dish", "side dishes": "Side Dish",
    "sides": "Side Dish",
    # Beverage
    "beverage": "Beverage", "beverages": "Beverage", "drink": "Beverage",
    "drinks": "Beverage",
    # Soup
    "soup": "Soup", "soups": "Soup",
    # Salad
    "salad": "Salad", "salads": "Salad",
    # Appetizer
    "appetizer": "Appetizer", "appetizers": "Appetizer", "appetiser": "Appetizer",
    "appetisers": "Appetizer",
    # Main Course
    "main course": "Main Course", "main dish": "Main Course", "mains": "Main Course",
    "main meal": "Main Course",
    # Brunch
    "brunch": "Brunch",
    # Condiment
    "condiment": "Condiment", "condiments": "Condiment", "sauce": "Condiment",
    "sauces": "Condiment",
    # Street Food
    "street food": "Street Food", "streetfood": "Street Food",
    # Bread
    "bread": "Bread", "breads": "Bread",
    # Pickle
    "pickle": "Pickle", "pickles": "Pickle", "chutney": "Pickle", "chutneys": "Pickle",
    # Dip
    "dip": "Dip", "dips": "Dip",
    # Sandwich
    "sandwich": "Sandwich", "sandwiches": "Sandwich",
    # Wrap
    "wrap": "Wrap", "wraps": "Wrap",
}
DIETARY_KEYWORDS = {
    # vegetarian
    "vegetarian": "vegetarian", "veg": "vegetarian", "vegeterian": "vegetarian",
    # vegan
    "vegan": "vegan", "vegen": "vegan",
    # non-vegetarian
    "non-veg": "non-vegetarian", "non veg": "non-vegetarian", "nonveg": "non-vegetarian",
    "non-vegetarian": "non-vegetarian", "non vegetarian": "non-vegetarian",
    # gluten-free
    "gluten free": "gluten-free", "gluten-free": "gluten-free", "glutenfree": "gluten-free",
    # dairy-free
    "dairy free": "dairy-free", "dairy-free": "dairy-free", "dairyfree": "dairy-free",
    "lactose free": "dairy-free", "lactose-free": "dairy-free",
    # nut-free
    "nut free": "nut-free", "nut-free": "nut-free", "nutfree": "nut-free",
    # keto
    "keto": "keto", "ketogenic": "keto",
    # low-carb
    "low carb": "low-carb", "low-carb": "low-carb", "lowcarb": "low-carb",
    # high-protein
    "high protein": "high-protein", "high-protein": "high-protein",
    "highprotein": "high-protein", "protein rich": "high-protein",
    # jain
    "jain": "jain", "jain food": "jain",
    # halal
    "halal": "halal",
    # egg-free
    "egg free": "egg-free", "egg-free": "egg-free", "eggfree": "egg-free",
    "no egg": "egg-free",
    # sugar-free
    "sugar free": "sugar-free", "sugar-free": "sugar-free", "sugarfree": "sugar-free",
    "no sugar": "sugar-free",
    # kosher
    "kosher": "kosher",
    # low-fat
    "low fat": "low-fat", "low-fat": "low-fat", "lowfat": "low-fat",
    # paleo
    "paleo": "paleo",
    # whole30
    "whole30": "whole30", "whole 30": "whole30",
    # low-sodium
    "low sodium": "low-sodium", "low-sodium": "low-sodium", "lowsodium": "low-sodium",
    # low-fodmap
    "low fodmap": "low-fodmap", "low-fodmap": "low-fodmap", "fodmap friendly": "low-fodmap",
    # diabetic-friendly
    "diabetic friendly": "diabetic-friendly", "diabetic-friendly": "diabetic-friendly",
    "diabetic": "diabetic-friendly",
    # pescatarian
    "pescatarian": "pescatarian",
}
SPICE_KEYWORDS = {
    "mild": "mild", "no spice": "mild", "not spicy": "mild", "non spicy": "mild",
    "medium spice": "medium", "medium hot": "medium", "moderately spicy": "medium",
    "spicy": "spicy", "hot": "spicy", "chilli": "spicy", "chili": "spicy",
    "extra spicy": "very_spicy", "very spicy": "very_spicy", "super spicy": "very_spicy",
    "extremely spicy": "very_spicy",
}
COOKING_METHOD_KEYWORDS = {
    # fried
    "fried": "fried", "fry": "fried",
    # grilled
    "grilled": "grilled", "grill": "grilled", "bbq": "grilled",
    "barbecued": "grilled", "barbeque": "grilled", "barbecue": "grilled",
    # baked
    "baked": "baked", "bake": "baked",
    # steamed
    "steamed": "steamed", "steam": "steamed",
    # stir-fried
    "stir fried": "stir-fried", "stir-fried": "stir-fried", "stirfried": "stir-fried",
    "stir fry": "stir-fried",
    # roasted
    "roasted": "roasted", "roast": "roasted",
    # boiled
    "boiled": "boiled", "boil": "boiled",
    # no-cook
    "no cook": "no-cook", "no-cook": "no-cook", "nocook": "no-cook",
    "raw": "no-cook", "uncooked": "no-cook",
    # slow-cooked
    "slow cooked": "slow-cooked", "slow-cooked": "slow-cooked", "slowcooked": "slow-cooked",
    "slow cooker": "slow-cooked",
    # pressure-cooked
    "pressure cooked": "pressure-cooked", "pressure-cooked": "pressure-cooked",
    "pressurecooked": "pressure-cooked", "pressure cooker": "pressure-cooked",
    "instant pot": "pressure-cooked",
    # air-fried
    "air fried": "air-fried", "air-fried": "air-fried", "airfried": "air-fried",
    "air fryer": "air-fried",
    # smoked
    "smoked": "smoked", "smoke": "smoked",
    # sauteed
    "sauteed": "sauteed", "sautéed": "sauteed", "saute": "sauteed", "sauté": "sauteed",
    # deep-fried
    "deep fried": "deep-fried", "deep-fried": "deep-fried", "deepfried": "deep-fried",
    # one-pot
    "one pot": "one-pot", "one-pot": "one-pot", "onepot": "one-pot",
    # fermented
    "fermented": "fermented", "ferment": "fermented",
    # marinated
    "marinated": "marinated", "marinate": "marinated",
    # poached
    "poached": "poached", "poach": "poached",
    # blanched
    "blanched": "blanched", "blanch": "blanched",
    # charred
    "charred": "charred", "char grilled": "charred", "chargrilled": "charred",
}
OCCASION_KEYWORDS = {
    # quick
    "quick": "quick", "fast": "quick", "under 30 minutes": "quick",
    "under 30 min": "quick", "30 minutes": "quick", "30-minute": "quick",
    # make-ahead
    "make ahead": "make-ahead", "make-ahead": "make-ahead", "makeahead": "make-ahead",
    "prep ahead": "make-ahead",
    # kids-friendly
    "kids friendly": "kids-friendly", "kid friendly": "kids-friendly",
    "kids-friendly": "kids-friendly", "kid-friendly": "kids-friendly",
    "kids": "kids-friendly", "children friendly": "kids-friendly",
    # party
    "party": "party", "party food": "party", "potluck": "party",
    # festive
    "festive": "festive", "festival": "festive", "holiday": "festive",
    "celebration": "festive",
    # weeknight
    "weeknight": "weeknight", "weeknights": "weeknight", "weekday dinner": "weeknight",
    # meal-prep
    "meal prep": "meal-prep", "meal-prep": "meal-prep", "mealprep": "meal-prep",
    # comfort-food
    "comfort food": "comfort-food", "comfortfood": "comfort-food",
    "comfort-food": "comfort-food",
    # light
    "light": "light", "healthy": "light", "light and healthy": "light",
    "light meal": "light",
    # indulgent
    "indulgent": "indulgent", "indulgence": "indulgent", "decadent": "indulgent",
    "rich": "indulgent",
    # budget-friendly
    "budget friendly": "budget-friendly", "budget-friendly": "budget-friendly",
    "cheap": "budget-friendly", "inexpensive": "budget-friendly",
    "low cost": "budget-friendly", "low-cost": "budget-friendly",
    # high-protein-meal
    "high protein meal": "high-protein-meal", "protein packed": "high-protein-meal",
    "protein-packed": "high-protein-meal",
    # post-workout
    "post workout": "post-workout", "post-workout": "post-workout",
    "postworkout": "post-workout", "after gym": "post-workout",
    # leftover-friendly
    "leftover friendly": "leftover-friendly", "leftover-friendly": "leftover-friendly",
    "leftoverfriendly": "leftover-friendly", "uses leftovers": "leftover-friendly",
    # date-night
    "date night": "date-night", "date-night": "date-night",
    # family-style
    "family style": "family-style", "family-style": "family-style",
    # freezer-friendly
    "freezer friendly": "freezer-friendly", "freezer-friendly": "freezer-friendly",
    "freezes well": "freezer-friendly",
    # no-oven
    "no oven": "no-oven", "no-oven": "no-oven", "without oven": "no-oven",
    # one-bowl
    "one bowl": "one-bowl", "one-bowl": "one-bowl",
    # travel-friendly
    "travel friendly": "travel-friendly", "travel-friendly": "travel-friendly",
    "picnic": "travel-friendly",
}
EQUIPMENT_KEYWORDS = {
    # oven
    "oven": "oven",
    # stovetop
    "stovetop": "stovetop", "stove top": "stovetop", "stove": "stovetop",
    # microwave
    "microwave": "microwave",
    # blender
    "blender": "blender",
    # food-processor
    "food processor": "food-processor", "food-processor": "food-processor",
    # rice-cooker
    "rice cooker": "rice-cooker", "rice-cooker": "rice-cooker",
    # tandoor
    "tandoor": "tandoor", "tandoori oven": "tandoor",
    # wok
    "wok": "wok",
    # grill-pan
    "grill pan": "grill-pan", "grill-pan": "grill-pan", "griddle": "grill-pan",
    # no-equipment
    "no equipment": "no-equipment", "minimal equipment": "no-equipment",
    "no special equipment": "no-equipment",
}
ALLERGEN_KEYWORDS = {
    # contains-tree-nuts
    "tree nuts": "contains-tree-nuts", "treenuts": "contains-tree-nuts",
    "tree-nuts": "contains-tree-nuts",
    # contains-peanuts
    "peanuts": "contains-peanuts", "peanut": "contains-peanuts",
    # contains-dairy
    "contains dairy": "contains-dairy", "has dairy": "contains-dairy",
    # contains-eggs
    "contains egg": "contains-eggs", "contains eggs": "contains-eggs",
    "has egg": "contains-eggs",
    # contains-shellfish
    "shellfish": "contains-shellfish", "prawns": "contains-shellfish",
    "shrimp": "contains-shellfish",
    # contains-soy
    "contains soy": "contains-soy", "soya": "contains-soy",
    # contains-gluten
    "contains gluten": "contains-gluten", "has gluten": "contains-gluten",
    # contains-sesame
    "sesame": "contains-sesame", "sesame seeds": "contains-sesame",
    # contains-fish
    "contains fish": "contains-fish", "has fish": "contains-fish",
}
TEXTURE_KEYWORDS = {
    "crispy": "crispy", "crisp": "crispy",
    "crunchy": "crunchy",
    "creamy": "creamy",
    "chewy": "chewy",
    "tender": "tender",
    "soft": "soft",
    "crumbly": "crumbly",
    "gooey": "gooey",
    "fluffy": "fluffy",
    "juicy": "juicy",
}
# Anything left over after the above are stripped is treated as free-text ingredient/keyword hints.
_STOPWORDS = {"a", "with", "and", "for", "the", "some", "want", "i", "me", "please", "recipe",
              "food", "contains", "has", "in"}


@dataclass
class ExtractedIntent:
    cuisine: str | None = None
    course: str | None = None
    dietary: str | None = None
    spice_level: str | None = None
    cooking_method: str | None = None
    occasion: str | None = None
    equipment: str | None = None
    allergen: str | None = None
    texture: str | None = None
    keywords: list[str] = field(default_factory=list)   # leftover free-text tokens (likely ingredients)

    def as_dict(self) -> dict:
        return {
            "cuisine": self.cuisine,
            "course": self.course,
            "dietary": self.dietary,
            "spice_level": self.spice_level,
            "cooking_method": self.cooking_method,
            "occasion": self.occasion,
            "equipment": self.equipment,
            "allergen": self.allergen,
            "texture": self.texture,
            "keywords": self.keywords,
        }


def extract_intent(query: str) -> ExtractedIntent:
    """Rule-based keyword extraction. Case-insensitive substring matching against the
    controlled vocabularies above; whatever isn't consumed by a known tag becomes a
    free-text keyword used for a simple ingredient/name overlap match in retrieval."""
    text = query.lower().strip()

    cuisine = _first_match(text, CUISINE_KEYWORDS)
    course = _first_match(text, COURSE_KEYWORDS)
    dietary = _first_match(text, DIETARY_KEYWORDS)
    spice_level = _first_match(text, SPICE_KEYWORDS)
    cooking_method = _first_match(text, COOKING_METHOD_KEYWORDS)
    occasion = _first_match(text, OCCASION_KEYWORDS)
    equipment = _first_match(text, EQUIPMENT_KEYWORDS)
    allergen = _first_match(text, ALLERGEN_KEYWORDS)
    texture = _first_match(text, TEXTURE_KEYWORDS)

    all_keywords = {**CUISINE_KEYWORDS, **COURSE_KEYWORDS, **DIETARY_KEYWORDS,
                     **SPICE_KEYWORDS, **COOKING_METHOD_KEYWORDS, **OCCASION_KEYWORDS,
                     **EQUIPMENT_KEYWORDS, **ALLERGEN_KEYWORDS, **TEXTURE_KEYWORDS}
    # Longest phrases first, so e.g. "stir fried" is stripped whole before the bare
    # "fried" entry gets a chance to eat only part of it and leave "stir" dangling.
    consumed_phrases = sorted((k for k in all_keywords if k in text), key=len, reverse=True)
    remainder = text
    for phrase in consumed_phrases:
        remainder = remainder.replace(phrase, " ")

    tokens = re.findall(r"[a-z]+", remainder)
    keywords = [t for t in tokens if t not in _STOPWORDS and len(t) > 2]

    return ExtractedIntent(cuisine=cuisine, course=course, dietary=dietary,
                            spice_level=spice_level, cooking_method=cooking_method,
                            occasion=occasion, equipment=equipment, allergen=allergen,
                            texture=texture, keywords=keywords)


def _first_match(text: str, vocab: dict[str, str]) -> str | None:
    # Longer phrases first so e.g. "non veg" matches before a bare "veg" would.
    for phrase in sorted(vocab.keys(), key=len, reverse=True):
        if phrase in text:
            return vocab[phrase]
    return None


if __name__ == "__main__":
    # Sanity check: confirm the controlled vocabulary size and print the breakdown.
    ALL_VOCABS = [CUISINE_KEYWORDS, COURSE_KEYWORDS, DIETARY_KEYWORDS, SPICE_KEYWORDS,
                  COOKING_METHOD_KEYWORDS, OCCASION_KEYWORDS, EQUIPMENT_KEYWORDS,
                  ALLERGEN_KEYWORDS, TEXTURE_KEYWORDS]
    per_category = {name: len(set(vocab.values())) for name, vocab in zip(
        ["cuisine", "course", "dietary", "spice_level", "cooking_method", "occasion",
         "equipment", "allergen", "texture"],
        ALL_VOCABS)}
    ALL_CANONICAL_VALUES = [v for vocab in ALL_VOCABS for v in vocab.values()]
    print("Canonical tags per category:", per_category)
    print("Total distinct canonical tag values:", len(set(ALL_CANONICAL_VALUES)))
