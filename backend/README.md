# i-can-cook backend (Auth + Pantry + Recipe Detail + Favorites + Zero-Waste + Scaling + Substitutions + Shelf-Life API + Ingredients)

Built and verified against a real Postgres 16 instance. This build replaces
the earlier `X-User-Id`-header auth stub with **real JWT auth**: Auth is a
first-class module now (register/login/me, bcrypt hashing, HS256 JWTs), and
Pantry/Favorites were switched over to it and re-tested end to end.

Modules: **Auth**, **Pantry** (real ML-02 model, real predictions),
**Recipe Detail** (real SL-Cook100 dataset, 99 recipes), **Favorites**,
**Zero-Waste Suggestions (RB-05)**, **Serving-Size Scaling (RB-03)**,
**Substitutions (RB-02)**, a standalone **Shelf-Life lookup API**, and the
**canonical Ingredients taxonomy** (112 ingredients). Every response shown
during development was live, not mocked.

## What's here

```
app/
  core/
    config.py      # env-driven settings (DATABASE_URL, model path)
    database.py     # SQLAlchemy engine/session
    security.py       # bcrypt hashing + JWT create/decode
    deps.py             # REAL JWT auth dependency (get_current_user, get_current_user_id)
  models/
    user.py          # users ORM model
    pantry.py         # pantry_items ORM model
    recipe.py          # recipes / recipe_ingredients / recipe_steps ORM models
    favorite.py          # favorites ORM model
    substitution.py         # ingredient_substitutions ORM model
    ingredient.py             # canonical ingredients ORM model
  schemas/
    user.py              # Pydantic schemas for auth/user
    pantry.py           # Pydantic request/response schemas for pantry
    recipe.py            # Pydantic response schemas for recipe detail
    favorite.py            # Pydantic schemas for favorites
    zero_waste.py             # Pydantic schemas for zero-waste suggestions
    scale.py                    # Pydantic schemas for serving-size scaling
    substitution.py               # Pydantic schemas for substitutions
    shelf_life.py                   # Pydantic schemas for standalone shelf-life lookup
  services/
    shelf_life.py          # loads the real .pkl, runs predictions in-process
  routers/
    auth.py                   # register / login / me
    shelf_life.py               # standalone POST .../shelf-life, .../shelf-life/batch
    pantry.py                     # pantry CRUD, 5 endpoints
    recipes.py                      # GET /api/recipes/{id}
    favorites.py                      # add/remove/list favorites
    zero_waste.py                       # GET /api/recipes/zero-waste-suggestions
    scale.py                              # GET /api/recipes/{id}/scale
    substitutions.py                        # GET .../substitutions, POST /api/substitutions
  main.py                                      # FastAPI app
db/
  schema.sql                                     # full DDL: users, pantry_items, recipes/ingredients/steps, favorites, ingredient_substitutions, ingredients
scripts/
  ingest_recipes.py                                # loads the 99 SL-Cook100 recipes
  ingest_ingredients.py                              # loads the 112-item canonical ingredient taxonomy
scripts/
  ingest_recipes.py                  # one-off loader: JSON recipes -> Postgres
models/
  gradient_boosting_shelf_life_classifier_prod.pkl
  gradient_boosting_shelf_life_regressor_prod.pkl        # served by default (3 features)
  gradient_boosting_shelf_life_regressor_v2_prod.pkl      # +ingredient_name experiment, NOT served -- see ML_INTEGRATION_README.md
data_sl_cook100/
  sl_001.json ... sl_100.json          # source recipe data (99 files)
requirements.txt
```

## Auth is now real

`app/models/user.py` is the real `User` model (not a stub anymore), and
`app/core/deps.py` decodes an actual JWT via `Authorization: Bearer <token>`.
Pantry, Favorites, and Zero-Waste were switched over from the earlier
`X-User-Id` header stub and re-tested end to end against real tokens — the
old header no longer works at all (tested: sending only `X-User-Id` with no
bearer token now correctly gets a 401).

Get a token via `POST /api/auth/register` or `/login`, then send
`Authorization: Bearer <access_token>` on every Pantry/Favorites/Zero-Waste
call.

## Endpoints

Auth (public):

| Method | Path | Behavior |
|---|---|---|
| POST | `/api/auth/register` | Create an account, returns a token immediately (register-then-login in one call) |
| POST | `/api/auth/login` | Returns a token. Wrong password and nonexistent email return the *same* 401 message, so this can't be used to enumerate registered emails |
| GET | `/api/auth/me` | Current user, requires a valid bearer token |

Shelf-Life lookup (public, standalone — not tied to a pantry item):

| Method | Path | Behavior |
|---|---|---|
| POST | `/api/ingredients/shelf-life` | One category/subcategory/storage_condition → one real ML-02 prediction |
| POST | `/api/ingredients/shelf-life/batch` | Same, up to 100 items per call |

Pantry (require `Authorization: Bearer <token>`):

| Method | Path | Behavior |
|---|---|---|
| POST | `/api/pantry` | Create item, runs ML-02 immediately, returns item + shelf-life flag |
| GET | `/api/pantry` | List current user's items, newest first |
| GET | `/api/pantry/{id}` | Single item (404 if not yours) |
| PATCH | `/api/pantry/{id}` | Partial update; re-runs ML-02 only if category/subcategory/storage_condition changed |
| DELETE | `/api/pantry/{id}` | Delete (404 if not yours) |

Recipes (public, no auth needed):

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/recipes/{id}` | Full detail: ingredients, steps, nutrition, tags. Serves from Postgres, not the ML-01 Flask service. |

Favorites (require `Authorization: Bearer <token>`):

| Method | Path | Behavior |
|---|---|---|
| POST | `/api/recipes/{id}/favorite` | Favorite a recipe. Idempotent — favoriting twice returns the same row, no duplicate, no error. 404 if the recipe doesn't exist. |
| DELETE | `/api/recipes/{id}/favorite` | Un-favorite. 404 if it wasn't favorited (or belongs to someone else). |
| GET | `/api/favorites` | List the current user's favorites, newest first, each with a small embedded recipe summary (name, cuisine, total time) so the frontend can render a list without N+1 calls. |

Zero-Waste (RB-05, requires `Authorization: Bearer <token>`):

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/recipes/zero-waste-suggestions?limit=10` | Cross-references the user's pantry items with a `short` ML-02 shelf-life prediction against recipe ingredients (matched on `ingredient_canonical_id`), returns recipes ranked by how many expiring items they use, then by what fraction of the recipe that covers. No new table — pure query, as originally scoped. |

Scaling (RB-03, public, no auth needed):

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/recipes/{id}/scale?servings=N` | Every ingredient quantity scaled proportionally to `N` servings (`N` between 1–100). 422 if the recipe has no base serving count on record. Steps are unchanged — only quantities scale, not instructions. |

Substitutions (RB-02, public GET, unprotected POST — see note):

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/recipes/{id}/substitutions?missing_ingredient={canonical_id}` | Substitutes for one ingredient in one recipe. 404 if the recipe doesn't exist, or if that ingredient isn't actually in the recipe. Returns `[]` if the ingredient is valid but no substitution data exists for it yet. |
| POST | `/api/substitutions` | Adds one substitution row. **No admin-role check** — there's no admin auth module in this session to guard it with. Treat this as open/internal until you wire a real admin dependency in. |

⚠️ **`ingredient_substitutions` ships empty.** No real substitution dataset
was available in this session (the research-papers zip referenced earlier
belongs to a different conversation and wasn't re-uploaded here; what
uploaded material exists is unrelated — a mushroom shelf-life paper, not
substitutions). Every lookup will correctly return `[]` until you seed real
data via `POST /api/substitutions` or a bulk import script.

Note: ML-01's existing `/api/recipes/recommend` (in the earlier transcript,
proxying to the Flask service on `localhost:5001`) is unchanged and separate
from this file. The natural next step there is to have `/recommend` return
just `id`/`name`/`score` as it does now, and let the frontend follow up with
`GET /api/recipes/{id}` from this module for the full card.

## What was actually tested, live

- Create → real model prediction returned (verified both `short` and `long`
  outcomes with different categories/storage conditions)
- Missing/invalid auth header → 401
- Nonexistent user id → 401
- Invalid `storage_condition` → 422, with the model never called
- List → correctly scoped to the requesting user, empty for a user with no items
- Get/Patch/Delete on another user's item → 404 (not 403 — doesn't reveal the item exists)
- Patch that only touches `quantity` → shelf-life fields and `shelf_life_checked_at` untouched (no wasted model call)
- Patch that changes `storage_condition` → model re-run, prediction actually flipped in the live test (Refrigerated/short → Frozen/long)
- Delete → 204, then a follow-up GET on the same id → 404

### Recipe Detail
- Ingested all 99 SL-Cook100 JSON files into Postgres (`scripts/ingest_recipes.py`), verified row counts: 99 recipes, 1246 ingredient rows, 687 step rows
- `GET /api/recipes/sl_013` → full match against the source JSON (Sinhala name, nutrition, all 18 ingredients with notes, all 8 steps in order)
- Spot-checked a second, unrelated recipe (`sl_050`, a dessert) to confirm it wasn't a one-off match
- Nonexistent id → clean 404
- SQL-injection-shaped id (`'; DROP TABLE recipes;--`, URL-encoded) → clean 404, table still has all 99 rows afterward (SQLAlchemy's parameterized queries hold)

### Favorites
- Missing auth header → 401
- Favorite a real recipe → 201, correct row in Postgres
- Favorite a nonexistent recipe → 404, no row created
- Favorite the same recipe twice → both calls return 201 with the *same* favorite id and timestamp — confirmed only one row exists in the DB (`SELECT * FROM favorites` showed exactly one row for that user/recipe pair)
- List favorites → correctly scoped per user (empty for a user with none), newest first, each with an embedded recipe summary
- Un-favorite as a different user → 404, underlying row untouched
- Un-favorite as the real owner → 204, then a second delete attempt → 404 (already gone)
- Final DB state matched exactly what the API reported after the whole sequence

### Zero-Waste Suggestions (RB-05)
- Route ordering verified: `/api/recipes/zero-waste-suggestions` is registered before `/api/recipes/{recipe_id}` and confirmed NOT swallowed by it (hit the real handler, didn't 404 as "recipe id not found")
- No expiring pantry items → `[]`, not an error
- Added a real pantry item (`ing_chicken`, Refrigerated) → ML-02 predicted `short` → correctly appeared as matches, ranked by coverage fraction
- Added items that predicted `long` (coconut oil, and once, tomato) → correctly excluded — this used the model's real output, not a rigged one
- Added a second expiring item (`ing_egg`) that co-occurs with chicken in 3 real recipes → those 3 recipes correctly jumped to a 2-ingredient match and ranked above every 1-ingredient match
- `limit` query param respected
- Different user with no pantry items → `[]`
- Missing auth header → 401

### Serving-Size Scaling (RB-03)
- Doubled servings (4 → 8) on a real recipe → every quantity exactly doubled, verified against the source JSON values
- Halved servings (4 → 2) → every quantity exactly halved
- Same servings (4 → 4) → scale factor `1.0`, quantities unchanged
- Non-round scale (4 → 3, factor `0.75`) → checked the actual rounding math by hand (0.25 tsp × 0.75 = 0.1875 → correctly rounds to 0.19)
- `servings` missing, `0`, negative, and `1000` → all 422 with clear validation messages (bounds are 1–100)
- Nonexistent recipe → 404
- Recipe with no base `servings` on record → tested by inserting a real temporary row with `servings = NULL`, confirmed a clean 422 rather than a divide-by-zero crash, then deleted the test row and confirmed the recipe count returned to exactly 99

### Substitutions (RB-02)
- Valid ingredient in a real recipe, before any data seeded → `[]`, HTTP 200 (not an error — just no data yet)
- Ingredient that exists but isn't in *that* recipe → 404 with a specific message
- Nonexistent recipe → 404
- Missing `missing_ingredient` query param → 422
- Seeded one real substitution via `POST /api/substitutions` (chicken → tofu) → immediately confirmed the follow-up GET returned exactly that row
- Blank `substitute_name` (whitespace only) → 422
- A different, unrelated ingredient in the same recipe → still `[]`, confirming the lookup is scoped to the specific `canonical_id`, not "any substitution exists for this recipe"
- Cleaned up the seeded test row afterward; table verified empty again

### Auth
- Register → 201, real bcrypt hash confirmed in the DB directly (not plaintext), token returned
- Duplicate email → 409
- Weak password (<8 chars) → 422
- Malformed email → 422
- Login with correct password → 200 with a working token
- Login with wrong password → 401
- Login with a nonexistent email → 401 with the *exact same* message as wrong password (checked byte-for-byte) — can't be used to enumerate accounts
- `GET /me` with a valid token → real user data
- `GET /me` with no token → 401 ("Missing bearer token")
- `GET /me` with a tampered token → 401 ("Invalid or expired token")
- Confirmed the old `X-User-Id` stub header, sent alone with no bearer token, is now correctly rejected — there's no silent fallback to the old auth scheme
- Re-ran Pantry create/list and Favorites create against the new JWT flow end to end — same real predictions, same real DB writes, now gated by a real token instead of a stand-in header

### Shelf-Life lookup API
- Single lookup → real model prediction (not the pantry-embedded version — the standalone one)
- Invalid `storage_condition` → 422
- Batch of 3 real category/storage combos → 3 real predictions, spanning short and long outcomes
- Empty batch → `[]`
- Batch with one bad item → 422 naming which item was invalid, whole batch rejected (no partial success)

### Ingredients (canonical taxonomy)
- Ingested all 112 entries from `ingredient_taxonomy.json`, confirmed count in Postgres
- Spot-checked a row (`ing_chicken` → name/category/unit_default) against the source JSON — exact match

## What's still not built

**Admin CRUD, Community (ratings/reviews), and Bookmarks/profile/shopping-list
are not built yet** — these are genuinely new, larger modules, not things
that exist elsewhere and need merging. They weren't started in this session.
Worth scoping as separate follow-ups rather than one big batch, since Admin
in particular needs a role-check dependency (`role == 'admin'`) that doesn't
exist yet — right now `get_current_user` only confirms *a* valid user, not
an admin one.

## Design choice worth flagging

The original ML-02 handoff assumed a separate Flask microservice on
`localhost:5001`. Since there's no way to stand up and verify a second server
in this sandbox, `app/services/shelf_life.py` loads the `.pkl` directly with
`joblib` and predicts in-process instead. If you want the two-service split
for deployment, swap that function's body for an `httpx` call — the
signature and return shape are already shaped for that to be a drop-in change.

## Running locally

```bash
pip install -r requirements.txt
createdb icancook
alembic upgrade head                    # applies every migration -- see "Database migrations" below
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/icancook
export JWT_SECRET_KEY=change-me-in-production   # optional, has a dev default
python3 scripts/ingest_ingredients.py   # loads the 112 canonical ingredients -- MUST run first, recipe_ingredients FKs into it
python3 scripts/ingest_recipes.py       # loads the 99 recipes -- one-off, safe to re-run
uvicorn app.main:app --reload
```

## Database migrations

Schema changes are managed with [Alembic](https://alembic.sqlalchemy.org/)
now, not by hand-editing `db/schema.sql` and re-running it. `alembic/env.py`
imports `Base` and every model under `app/models/` and reads the DB URL from
`app.core.config.settings.DATABASE_URL` (the same env var the app itself
uses), so there's one source of truth for which database it's pointed at.

**After changing a model:**

```bash
alembic revision --autogenerate -m "add is_verified to users"
```

Then **open the generated file in `alembic/versions/` and read it** --
autogenerate is a good first draft, not a guarantee. It regularly misses or
mis-renders things like `CHECK` constraints declared via `__table_args__`,
array-column `server_default`s (`'{}'::text[]` vs a bare `'{}'`), and
non-FK indexes (a GIN index, say) that aren't expressible as a plain
`Column(index=True)`. Fix those by hand in the generated script before
committing it -- the baseline migration (`alembic/versions/
f131a5f3859b_baseline.py`) has worked examples of each, since exactly
these gaps came up reconciling it against `db/schema.sql`.

**To apply migrations** (fresh DB or after pulling new ones):

```bash
alembic upgrade head
```

**Restoring the seeded dump** (`icancook_seeded_dump_sql.gz`) is a special
case: that dump was taken *before* the email-verification migration
(`a3f9c1d2e6b0_add_email_verification.py`) but already contains every
table `baseline` (`f131a5f3859b`) creates. So it needs to be stamped at
`baseline`, not `head` -- stamping straight to `head` would silently skip
the email-verification migration too, leaving `users.is_verified` and
`email_verification_tokens` missing even though the app expects them:

```bash
gunzip -c icancook_seeded_dump_sql.gz | psql -d icancook
alembic stamp f131a5f3859b   # tell Alembic the dump already matches baseline...
alembic upgrade head         # ...then actually run everything after it for real
```

`alembic stamp <revision>` writes Alembic's version-tracking row without
touching any table, so the first command is a no-op against the data --
it just tells Alembic "the database already looks like this revision."
The second command then runs every migration *after* that revision for
real, which today means `a3f9c1d2e6b0_add_email_verification` actually
executes and adds the missing column/table. If a future migration lands
after that one, this same two-step recipe still works unchanged -- the
`stamp` target only ever needs to move if the seeded dump itself gets
regenerated from a newer database.

**Don't** `alembic stamp head` against the seeded dump specifically --
that's only correct once the dump is regenerated from a database that
already has every current migration applied.
