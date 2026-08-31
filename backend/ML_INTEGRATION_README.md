# i-can-cook backend -- consolidated

This is `newbackend_updated` (the most complete FastAPI app across your
uploads -- has `recipes_browse.py`, all five admin routers, community,
bookmarks, profile) with ML-01 and ML-02 merged in from the nested
`files__10_.zip -> i-can-cook.zip` project, where those two were built but
never wired into a live backend.

## What changed from `newbackend_updated`

### ML-02 (shelf life) -- now a real regressor, not a classifier + table hack
- **New model**: `models/gradient_boosting_shelf_life_regressor_prod.pkl`,
  retrained here from `ml/ml02_shelf_life/data/enriched/...csv` (554 rows,
  USDA FoodKeeper + 12 rows mined from Sri Lankan research papers).
- **Why retrained rather than reusing the existing regressor**: the one
  already in the project (`ml/ml02_shelf_life/models/gradient_boosting_shelf_life_model.pkl`,
  kept here for reference) was trained on `data_source`/`confidence`
  columns -- fields describing which dataset a training row came from, not
  properties of a real ingredient, which a live request can never supply.
  Its own README flagged this and recommended NOT serving it as-is.
- **Fix applied**: retrained on `category` + `subcategory` +
  `storage_condition` only (the three fields a live pantry item actually
  has), predicting `log1p(shelf_life_days)` instead of raw days. The log
  transform stabilised mean R² from an unstable 0.07-0.48 (raw target,
  10 random splits) to 0.60-0.78 (log target, same splits) -- worth citing
  as the key modelling decision in your dissertation.
- **Honest limitation to state**: MAE is still ~130 days on the raw scale,
  because a handful of very-long-shelf-life pantry staples (dried spices,
  grains -- up to 720 days) pull the average error up even though most
  fresh-ingredient predictions are much closer. This is a genuine property
  of the skewed target distribution, not a bug -- say so plainly rather
  than letting the R² figure alone imply more precision than it has.
- `app/services/shelf_life.py`, `app/schemas/shelf_life.py`,
  `app/routers/shelf_life.py`, `app/services/ml02_shelf_life.py` were all
  updated to match (return `predicted_days` directly; the old
  classify-then-check-against-a-table logic is gone since the model now
  gives a real day count). The old classifier `.pkl` is left in `models/`
  for reference/comparison but nothing loads it anymore.
- `app/core/config.py`'s `SHELF_LIFE_MODEL_PATH` now points at the
  regressor.

### ML-02 follow-up: tried `ingredient_name` as a 4th feature, didn't ship it
- Retrained with `ingredient_name` added alongside `category`/`subcategory`/
  `storage_condition`, using `sklearn.preprocessing.TargetEncoder` (cross-fitted,
  leakage-safe) since it's high-cardinality (346 unique values / 554 rows) and a
  naive one-hot would overfit.
- On a plain random 80/20 split it looked slightly better, but that's
  misleading: ~63% of ingredients repeat 2-3 times in this dataset, so a
  random split often puts the same ingredient in both train and test. Re-run
  with `GroupShuffleSplit` grouped by `ingredient_name` -- holding out whole
  ingredients, the realistic case, since ~50% of the app's own seeded
  ingredient catalog (91/183) isn't in this 554-row training set at all --
  the 4-feature model came out *worse* (lower R², higher MAE, loses on a
  majority of held-out splits).
- Saved as `models/gradient_boosting_shelf_life_regressor_v2_prod.pkl` for
  reference, but `SHELF_LIFE_MODEL_PATH` still defaults to the 3-feature
  model above -- this is a documented negative result, not shipped.
  `predict_shelf_life()` now accepts `ingredient_name` and will use it
  automatically if `SHELF_LIFE_MODEL_PATH` is ever pointed at v2 instead.
  Full writeup in `app/services/shelf_life.py`'s docstring and
  `ml/ml02_shelf_life/notebooks/ML02_Gradient_Boosting_Shelf_Life.ipynb`.

### ML-01 (recipe recommendation) -- built from scratch, didn't exist before
Nothing in `newbackend_updated` implemented this at all. Added:
- `app/services/ml01/` -- the tiered extraction pipeline (copied from the
  `ml01_recipe_recommendation/src/` project and adapted: relative imports,
  and `gemma_extractor.py` rewritten from an always-raising stub into a
  real Ollama call):
  - **Tier 1 (Gemma)**: calls a local Gemma model via Ollama
    (`GEMMA_OLLAMA_URL` in `.env` / `app/core/config.py`). Unset by
    default -- Tier 1 is skipped until you point it at a running Ollama
    instance with a Gemma model pulled (`ollama pull gemma2:2b`). This
    keeps the proposal's "no third-party AI APIs" constraint: Ollama runs
    entirely on-device.
  - **Tier 2 (Sentence Transformer)**: real `sentence-transformers`
    (`all-MiniLM-L6-v2`) embedding similarity against the controlled
    vocabulary. Needs the model weights downloaded once (needs internet
    the first time it runs, then it's cached locally).
  - **Tier 3 (rule-based)**: keyword matching, always succeeds -- this is
    functionally your existing `rb01_intent.py`'s approach, reimplemented
    against the same shared vocabulary as tiers 1-2 so all three tiers'
    outputs are directly comparable.
- `app/services/ml01/recommender.py` -- the actual scoring/ranking step
  (ingredient overlap with pantry, meal type, spice level, dietary/cuisine
  match), rewritten to query the real `recipes` / `recipe_ingredients`
  tables instead of the original project's SL-Cook100 JSON files.
- `app/routers/recommend.py` + `app/schemas/recommend.py` -- new endpoint,
  `POST /api/recommendations`. Public; pass `use_pantry: true` with a
  bearer token to also weight by the caller's pantry contents.
- `app/core/deps.py` gained `get_current_user_optional` (additive --
  doesn't touch the existing `get_current_user`) so this endpoint can
  personalise for logged-in users without requiring auth for anonymous
  browsing.

### Not touched
Auth (still no email verification -- flagged separately, not part of this
ML merge), the four missing frontend pages, and the Next.js-vs-Vite
decision are all still open from the earlier gap analysis. This zip is
backend-only, per your ask.

## Setup
```
pip install -r requirements.txt
# DB: point DATABASE_URL at your Postgres, run db/schema.sql
uvicorn app.main:app --reload
```
Tier 1 (Gemma) and Tier 2 (Sentence Transformer) are both optional at
runtime -- the app works end-to-end on Tier 3 alone if neither is set up.

## New/changed endpoints
- `POST /api/recommendations` -- ML-01, new
- `POST /api/ingredients/shelf-life`, `POST /api/ingredients/shelf-life/batch`
  -- same paths as before, response shape changed (`predicted_days` float
  instead of `prediction`/`probability_short`/`probability_long`)
