"""
Importing this package registers every ORM model with SQLAlchemy's mapper
registry. This matters because several models reference each other by
string name in relationship() calls (e.g. RecipeIngredient.ingredient =
relationship("Ingredient")) -- if the referenced class was never imported
anywhere in the process, mapper configuration fails with
InvalidRequestError the first time any query touches that relationship.

Any script, test, or entry point that touches the DB should import
app.models (or app.main, which imports every router and transitively every
model) before running queries, rather than importing individual model
modules piecemeal.
"""
from app.models.user import User  # noqa: F401
from app.models.ingredient import Ingredient  # noqa: F401
from app.models.recipe import Recipe, RecipeIngredient, RecipeStep  # noqa: F401
from app.models.pantry import PantryItem  # noqa: F401
from app.models.favorite import Favorite  # noqa: F401
from app.models.substitution import IngredientSubstitution  # noqa: F401
from app.models.community import *  # noqa: F401,F403
from app.models.tag_vocabulary import *  # noqa: F401,F403
from app.models.trust_audit import *  # noqa: F401,F403
from app.models.bookmark import BookmarkCollection, Bookmark, ShoppingList, ShoppingListItem  # noqa: F401
from app.models.email_verification_token import EmailVerificationToken  # noqa: F401