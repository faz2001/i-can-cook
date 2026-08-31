-- ============================================================================
-- I Can Cook -- consolidated schema (fresh-database version)
-- Equivalent to running, in order: schema.sql, 002_recipes.sql, 003_pantry.sql,
-- 004_community.sql, 005_admin.sql -- but written as CREATE TABLEs with every
-- column already in its final form, rather than ALTERs layered on afterward.
--
-- If you already have a database built from the incremental migration files,
-- keep using those -- don't run this against it (it will conflict with what's
-- already there). Use this only to set up a brand new database in one pass.
--
-- ALEMBIC NOTE: as of the alembic/ baseline migration, this file is no
-- longer how schema changes actually get applied -- Alembic
-- (`alembic upgrade head`) is the source of truth for that now. This file
-- is kept as a fresh-install/quickstart reference showing what the schema
-- looks like in its current, final form; see the "Database migrations"
-- section in README.md for the real workflow, including what to do if
-- you're restoring the seeded dump rather than starting from an empty DB.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Users & auth
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS users (
    id                    SERIAL PRIMARY KEY,
    email                 TEXT UNIQUE NOT NULL,
    password_hash         TEXT NOT NULL,
    full_name             TEXT,
    role                  TEXT NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    is_verified           BOOLEAN NOT NULL DEFAULT false,
    dietary_preferences   TEXT[] NOT NULL DEFAULT '{}',
    kitchen_equipment     TEXT[] NOT NULL DEFAULT '{}',
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Defensive migration for databases (e.g. the seeded dump) created before
-- is_verified existed -- CREATE TABLE IF NOT EXISTS above is a no-op against
-- an already-existing table, so the column needs adding explicitly.
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_verified BOOLEAN NOT NULL DEFAULT false;

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token       TEXT UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_user ON email_verification_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_email_verification_tokens_token ON email_verification_tokens(token);


-- ----------------------------------------------------------------------------
-- Ingredient taxonomy & recipe corpus
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ingredients (
    canonical_id  TEXT PRIMARY KEY,              -- e.g. 'ing_chicken'
    name          TEXT NOT NULL,
    category      TEXT,                          -- e.g. 'Meat', 'Spices', 'Vegetables'
    unit_default  TEXT,
    source        TEXT NOT NULL DEFAULT 'sl_cook100' CHECK (source IN ('sl_cook100', 'kaggle_epicurious')),
                                                   -- which dataset this canonical entry was added for; the ID
                                                   -- space itself stays SHARED across sources on purpose, so
                                                   -- pantry matching keeps working across every recipe regardless
                                                   -- of where it came from -- this column is for provenance/
                                                   -- auditing only, not a second foreign-key target
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recipes (
    id                  TEXT PRIMARY KEY,         -- 'sl_013' curated, uuid-based imported/community
    name_en             TEXT NOT NULL,
    name_native         TEXT,
    cuisine             TEXT NOT NULL,
    regional_origin     TEXT,
    course              TEXT,
    servings            INTEGER,
    prep_time_min       INTEGER,
    cook_time_min       INTEGER,
    total_time_min      INTEGER,
    tags                TEXT[] NOT NULL DEFAULT '{}',
    ayurvedic_balance   TEXT,
    image_url           TEXT,                      -- resolved at ingest time from COURSE_IMAGES in ingest_recipes.py; the dataset itself has no photos

    calories_kcal       NUMERIC,
    protein_g           NUMERIC,
    carbs_g             NUMERIC,
    fat_g               NUMERIC,
    fibre_g             NUMERIC,

    trust_score         NUMERIC(3,2) NOT NULL DEFAULT 0.50 CHECK (trust_score BETWEEN 0 AND 1),
    source_type         TEXT NOT NULL DEFAULT 'imported' CHECK (source_type IN ('curated', 'imported', 'community')),
    moderation_status   TEXT NOT NULL DEFAULT 'approved' CHECK (moderation_status IN ('approved', 'pending', 'rejected')),
    submitted_by        INTEGER REFERENCES users(id) ON DELETE SET NULL,

    source_url          TEXT,
    source_site         TEXT,
    collection_method   TEXT,
    annotated_by        TEXT,
    annotation_date     DATE,
    notes               TEXT,

    average_rating      NUMERIC(2,1),             -- denormalised from reviews, kept in sync on write
    review_count        INTEGER NOT NULL DEFAULT 0,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recipes_cuisine ON recipes(cuisine);
CREATE INDEX IF NOT EXISTS idx_recipes_source_type ON recipes(source_type);
CREATE INDEX IF NOT EXISTS idx_recipes_moderation_status ON recipes(moderation_status);
CREATE INDEX IF NOT EXISTS idx_recipes_tags ON recipes USING GIN(tags);

CREATE TABLE IF NOT EXISTS recipe_ingredients (
    id              SERIAL PRIMARY KEY,
    recipe_id       TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    ingredient_id   TEXT REFERENCES ingredients(canonical_id) ON DELETE SET NULL,
    raw_name        TEXT NOT NULL,   -- original ingredient text; kept even after canonical matching
    quantity        NUMERIC,
    unit            TEXT,
    notes           TEXT,
    position        INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_recipe ON recipe_ingredients(recipe_id);
CREATE INDEX IF NOT EXISTS idx_recipe_ingredients_ingredient ON recipe_ingredients(ingredient_id);

CREATE TABLE IF NOT EXISTS recipe_steps (
    id              SERIAL PRIMARY KEY,
    recipe_id       TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    step_number     INTEGER NOT NULL,
    instruction     TEXT NOT NULL,
    duration_min    INTEGER,
    UNIQUE (recipe_id, step_number)
);

CREATE INDEX IF NOT EXISTS idx_recipe_steps_recipe ON recipe_steps(recipe_id);


-- ----------------------------------------------------------------------------
-- Pantry (RB-02 / RB-05 / ML-02 dependency)
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS pantry_items (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ingredient_id       TEXT REFERENCES ingredients(canonical_id) ON DELETE SET NULL,
    raw_name            TEXT NOT NULL,
    quantity            NUMERIC,
    unit                TEXT,
    storage_condition   TEXT CHECK (storage_condition IN ('Refrigerated', 'Frozen', 'Pantry')),
    -- Matches the trained ML-02 classifier's vocabulary (app/services/shelf_life.py),
    -- not the earlier 4-value ambient/dry_container placeholder -- this table had no
    -- CHECK constraint before, so nothing was actually enforcing that comment.
    purchase_date       DATE,
    expiry_date         DATE,
    expiry_source       TEXT CHECK (expiry_source IN ('label', 'predicted')),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_pantry_items_user ON pantry_items(user_id);
CREATE INDEX IF NOT EXISTS idx_pantry_items_ingredient ON pantry_items(ingredient_id);
CREATE INDEX IF NOT EXISTS idx_pantry_items_expiry ON pantry_items(expiry_date);


-- ----------------------------------------------------------------------------
-- Community: reviews, occasion-tag voting, variation logging
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS reviews (
    id            SERIAL PRIMARY KEY,
    recipe_id     TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating        INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (recipe_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_reviews_recipe ON reviews(recipe_id);

CREATE TABLE IF NOT EXISTS occasion_tags (
    id            TEXT PRIMARY KEY,          -- slug, e.g. 'occ_rainy_day'
    label         TEXT NOT NULL UNIQUE,
    status        TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('approved', 'proposed', 'rejected')),
    proposed_by   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS recipe_occasion_votes (
    id                SERIAL PRIMARY KEY,
    recipe_id         TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    occasion_tag_id   TEXT NOT NULL REFERENCES occasion_tags(id) ON DELETE CASCADE,
    user_id           INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (recipe_id, occasion_tag_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_recipe_occasion_votes_recipe ON recipe_occasion_votes(recipe_id);

CREATE TABLE IF NOT EXISTS recipe_variations (
    id              SERIAL PRIMARY KEY,
    recipe_id       TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    description     TEXT NOT NULL,
    substitutions   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_recipe_variations_recipe ON recipe_variations(recipe_id);


-- ----------------------------------------------------------------------------
-- Admin: general tag vocabulary, trust score audit trail
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS recipe_tag_vocabulary (
    id            TEXT PRIMARY KEY,     -- slug, e.g. 'tag_one_pot'
    label         TEXT NOT NULL UNIQUE,
    category      TEXT,                 -- e.g. 'cooking_method', 'dietary', 'flavor'
    status        TEXT NOT NULL DEFAULT 'approved' CHECK (status IN ('approved', 'retired')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS trust_score_audit_log (
    id              SERIAL PRIMARY KEY,
    recipe_id       TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    admin_user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    old_value       NUMERIC(3,2),
    new_value       NUMERIC(3,2) NOT NULL,
    reason          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_trust_score_audit_log_recipe ON trust_score_audit_log(recipe_id);

CREATE TABLE IF NOT EXISTS favorites (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recipe_id   TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, recipe_id)
);

CREATE TABLE IF NOT EXISTS ingredient_substitutions (
    id                       SERIAL PRIMARY KEY,
    canonical_id             TEXT NOT NULL,   -- the ingredient being substituted for
    substitute_canonical_id  TEXT,
    substitute_name          TEXT NOT NULL,
    ratio                    TEXT,
    notes                    TEXT,
    context                  TEXT,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ingredient_substitutions_canonical ON ingredient_substitutions(canonical_id);


-- ----------------------------------------------------------------------------
-- Bookmark collections & shopping lists
-- ----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS bookmark_collections (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, name)
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id             SERIAL PRIMARY KEY,
    collection_id  INTEGER NOT NULL REFERENCES bookmark_collections(id) ON DELETE CASCADE,
    recipe_id      TEXT NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    added_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (collection_id, recipe_id)
);

CREATE TABLE IF NOT EXISTS shopping_lists (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    collection_id  INTEGER REFERENCES bookmark_collections(id) ON DELETE SET NULL,
    name           TEXT NOT NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS shopping_list_items (
    id                 SERIAL PRIMARY KEY,
    shopping_list_id   INTEGER NOT NULL REFERENCES shopping_lists(id) ON DELETE CASCADE,
    name               TEXT NOT NULL,
    quantity           NUMERIC,
    unit               TEXT,
    is_checked         BOOLEAN NOT NULL DEFAULT false,
    -- true for a manually-typed item, false for one generated from a recipe's ingredients
    is_manual          BOOLEAN NOT NULL DEFAULT false,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bookmark_collections_user ON bookmark_collections(user_id);
CREATE INDEX IF NOT EXISTS idx_bookmarks_collection ON bookmarks(collection_id);
CREATE INDEX IF NOT EXISTS idx_shopping_lists_user ON shopping_lists(user_id);
CREATE INDEX IF NOT EXISTS idx_shopping_list_items_list ON shopping_list_items(shopping_list_id);
