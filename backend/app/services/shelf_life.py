"""
ML-02 shelf-life prediction, loaded in-process.

This now serves `gradient_boosting_shelf_life_regressor_prod.pkl` -- a real
GradientBoostingRegressor, matching the proposal's literal spec (predicts
remaining shelf life in days, not a short/long class).

Provenance, honestly stated:
  - Trained on the 554-row enriched USDA FoodKeeper + Sri-Lankan-research-paper
    dataset (ml/ml02_shelf_life/data/enriched/ml02_shelf_life_train_enriched.csv).
  - Features: category, subcategory, storage_condition only -- the same three
    a live pantry item actually has. (An earlier regressor in the project
    history was trained with `data_source`/`confidence` columns too -- dataset
    provenance fields a real ingredient can never supply -- so it couldn't
    have been served; it was retrained here without them.)
  - Target: log1p(shelf_life_days). The raw day range spans 1 to 720+ days
    (a fresh herb vs. a dry spice), which badly skews a plain regressor;
    predicting log(days) and exponentiating back stabilised R^2, evaluated in
    log1p-space across 10 random 80/20 splits (random_state 0-9), from an
    unstable 0.079-0.401 (raw target, R^2 on the raw day scale) to 0.575-0.775
    (log1p target, R^2 on the log1p scale) -- worth citing as the key
    modelling decision in the dissertation.
  - Still a genuine limitation to state plainly: MAE is ~130 days on the raw
    scale (mean 130.6 across those same 10 splits), because a handful of
    very-long-shelf-life pantry staples (dried spices, grains) pull the error
    up even though most fresh-ingredient predictions are much closer. This is
    a real property of the data, not a bug -- flag it as a limitation rather
    than hide it.

Tried and NOT shipped: `ingredient_name` as a 4th feature (v2).
  - Motivation: category/subcategory/storage_condition can't distinguish
    "chicken breast, refrigerated" from "milk, refrigerated" -- both might
    fall in similar buckets. Adding the ingredient name itself lets the
    model learn ingredient-specific behaviour on top of the coarse buckets.
  - ingredient_name is high-cardinality (346 unique values across 554 rows,
    many appearing only once) -- naive one-hot encoding would massively
    inflate the feature space relative to the row count. Used
    `sklearn.preprocessing.TargetEncoder` instead (see train_v2.py under
    ml/ml02_shelf_life/), which internally cross-fits: it splits the
    training data into folds and encodes each row using only the *other*
    folds' target means, so a row's own label never leaks into its own
    encoding. This is the standard leakage-safe way to feed a
    high-cardinality categorical into a plain GradientBoostingRegressor
    (which, unlike HistGradientBoostingRegressor, has no native categorical
    support) without switching model classes.
  - Naive random 80/20 splits (same methodology/seeds as above) made the
    4-feature model look slightly *better*: log1p-space R^2 0.585-0.791
    (mean 0.671) vs. the 3-feature model's 0.575-0.775 (mean 0.666), and MAE
    129.1d vs. 130.6d. But that comparison is misleading here: ~63% of
    ingredients in this dataset appear 2-3 times (once per storage
    condition), so a plain random split routinely puts the *same*
    ingredient's other rows in both train and test -- the target encoder is
    partly just recognising a repeat, not learning transferable
    ingredient-level shelf-life behaviour.
  - Re-evaluated with `GroupShuffleSplit` grouped by `ingredient_name` (10
    splits, same seeds), so test-set ingredients are held out entirely and
    never seen in training -- the realistic scenario, since ~50% of the
    ingredients actually seeded in the app's own catalog (91 of 183) don't
    appear in this training set at all. Under that honest split the
    4-feature model is *worse*, not better: mean R^2 0.610 vs. 0.635 (higher
    on 3-feature in 8 of 10 seeds) and mean MAE 140.2d vs. 137.6d (3-feature
    had the lower, better MAE on 6 of 10 seeds). Adding ingredient_name is
    overfitting to the specific 554 training rows rather than learning
    something that generalises to the unseen ingredients production
    actually serves.
  - Decision: this is a legitimate negative result, documented rather than
    forced into production. The trained v2 model is still saved, as
    `models/gradient_boosting_shelf_life_regressor_v2_prod.pkl`, purely for
    comparison/reference -- `settings.SHELF_LIFE_MODEL_PATH` still defaults
    to the 3-feature v1 model. `predict_shelf_life()` below accepts
    `ingredient_name` and will use it *if* a model that was trained with it
    is ever loaded (it introspects `model.feature_names_in_`), so switching
    to v2 later -- e.g. once the training set has grown enough that
    ingredient-level patterns generalise -- is a config change, not a code
    change. It is not switched on by default today.
  - Explicitly NOT tried: adding `purchase_month` as a feature. This dataset
    is a static per-ingredient/storage lookup table (each row is "this
    ingredient, this storage condition -> this shelf life"), not a log of
    purchase events with dates -- there's no real relationship between
    "month purchased" and "how long a food keeps" to learn from it here, and
    fabricating a purchase_month column (e.g. by randomly assigning one)
    would just be fitting noise the model would confidently mispredict on.
    If a genuine seasonal effect on shelf life were ever worth modelling
    (e.g. produce freshness varying by harvest season), it would need actual
    purchase-event data with dates, not this table.

The classifier this replaces (`gradient_boosting_shelf_life_classifier_prod.pkl`)
is left in `models/` for reference/comparison but is no longer loaded here.
"""
import joblib
import numpy as np
import pandas as pd

from app.core.config import settings

VALID_STORAGE_CONDITIONS = {"Refrigerated", "Frozen", "Pantry"}

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = joblib.load(settings.SHELF_LIFE_MODEL_PATH)
    return _model


def predict_shelf_life(
    category: str,
    subcategory: str | None,
    storage_condition: str,
    ingredient_name: str,
) -> dict:
    if storage_condition not in VALID_STORAGE_CONDITIONS:
        raise ValueError(f"storage_condition must be one of {sorted(VALID_STORAGE_CONDITIONS)}")

    model = _get_model()

    row_values = {
        "category": category,
        "subcategory": subcategory or "Unknown",
        "storage_condition": storage_condition,
        "ingredient_name": ingredient_name,
    }
    # Only pass the columns the loaded model was actually trained with --
    # today that's the 3-feature v1 model, so ingredient_name is accepted
    # here but not fed in; see the docstring above for why. This keeps
    # predict_shelf_life() working unchanged if SHELF_LIFE_MODEL_PATH is
    # ever pointed at the 4-feature v2 model instead.
    model_columns = list(model.feature_names_in_)
    row = pd.DataFrame([{col: row_values[col] for col in model_columns}])

    pred_log_days = model.predict(row)[0]
    predicted_days = float(np.expm1(pred_log_days))
    # Never return a negative or absurdly-precise day count.
    predicted_days = max(0.0, round(predicted_days, 1))

    # Reflect whichever model is actually loaded (v1 by default; v2 only if
    # SHELF_LIFE_MODEL_PATH has been overridden -- see docstring above).
    model_version = "v2" if "ingredient_name" in model_columns else "v1"

    return {
        "predicted_days": predicted_days,
        "model": f"gradient_boosting_regressor_{model_version}",
    }
