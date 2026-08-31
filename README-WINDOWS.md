# I Can Cook — Final Merged Build (Windows PowerShell Edition)

This is the single, reconciled build of everything worked on so far: Alembic
migrations, email verification (with a real frontend confirmation page),
production safety checks (JWT secret + configurable CORS), the ML-02
shelf-life model, the RB-01 tag vocabulary, favorites, bookmarks /
collections / shopping lists, profile stats + password change, the
redesigned landing page, and the step-by-step Kitchen Mode — **including the
fix for the Kitchen Mode timer resetting when you navigate between steps**
(see §4 and §7).

This supersedes every earlier zip/README you've been given for this
project. If you have older copies of `backend_final_pkg` or
`frontend_final_pkg` lying around, use this one instead — don't hand-merge
files between them.

> **Windows PowerShell commands throughout.** Adjust the project path
> (`C:\Users\user\Downloads\project`) and PostgreSQL version number (`16`)
> below to match your actual setup.

---

## 1. Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 14+ (the seeded dump was made with pg_dump 16.15 — see note in step 2.3)
- Windows PowerShell

---

## 2. Backend setup

### 2.1 Install dependencies

```powershell
cd C:\Users\user\Downloads\project\backend_final_pkg
pip install -r requirements.txt
```

> This installs into your global/system Python rather than an isolated
> virtual environment. That's fine for a quick run, but be aware it can
> collide with package versions other projects on this machine expect. If
> you'd rather isolate it, create a venv first (`python -m venv venv` then
> `.\venv\Scripts\Activate.ps1`) and run the same `pip install` inside it.

### 2.2 Environment variables

None of these are required to boot the app for local dev (all have working
defaults), but you should set at least `JWT_SECRET_KEY` before this touches
real user data:

| Variable | Default | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/icancook` | |
| `JWT_SECRET_KEY` | `dev-secret-change-me-in-production` | **Change this before deploying anywhere.** See §5 — production startup now refuses to boot on the default value. |
| `API_BASE_URL` | `http://localhost:8000` | Absolute base URL of the API itself. Not used to build the verification email link (see `FRONTEND_BASE_URL` below) — kept for anything else that needs an absolute API URL. |
| `FRONTEND_BASE_URL` | `http://localhost:5173` | Base URL of the frontend app. The verification email link points at `{FRONTEND_BASE_URL}/verify-email?token=...`, a real page in the app, not raw API JSON. |
| `SHELF_LIFE_MODEL_PATH` | v1 (3-feature) model | Don't point this at the v2 model — see §5. |
| `ML01_MIN_CONFIDENCE` | `0.4` | Confidence threshold for the tiered intent pipeline. |
| `GEMMA_OLLAMA_URL` | unset | Set to e.g. `http://localhost:11434` to enable the Gemma tier via Ollama. Left unset, that tier is skipped. |
| `ENV` | `development` | Set to `production` to enable a startup safety check — refuses to start if `JWT_SECRET_KEY` is still the default. No other effect. **Leave this unset for local dev** (see the CORS troubleshooting note in §7 if you're seeing 400s on every request). |
| `CORS_ALLOWED_ORIGINS` | unset (→ `*`, allow everything) | Comma-separated list of allowed origins, e.g. `https://app.example.com,https://admin.example.com`. **Leave this unset for local dev.** See §7 if you've set it and requests from your dev frontend are now failing. |

Set these for your current PowerShell session:

```powershell
$env:JWT_SECRET_KEY="a-real-secret-change-me"
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/icancook"
$env:API_BASE_URL="http://localhost:8000"
$env:FRONTEND_BASE_URL="http://localhost:5173"
$env:ML01_MIN_CONFIDENCE="0.4"
```

**Don't add a line for `SHELF_LIFE_MODEL_PATH`** unless you're deliberately
pointing it at a real file — the table above shows `path\to\v1\model` purely
to illustrate the variable, not as something to paste in literally. The
default (the v1 model already bundled under `models/`) works out of the
box; overriding it with a path that doesn't exist won't stop the app from
starting (the model loads lazily), so it'll seem fine right up until the
first shelf-life prediction request, which will then fail with a
`joblib.load` file-not-found error. Same idea for `GEMMA_OLLAMA_URL` — only
set it if you're actually running Ollama locally:

```powershell
$env:GEMMA_OLLAMA_URL="http://localhost:11434"   # only if Ollama is actually running
```

These only last for the current terminal session. For a permanent
(per-user) setting instead, use:

```powershell
[System.Environment]::SetEnvironmentVariable("JWT_SECRET_KEY", "a-real-secret-change-me", "User")
```

Then close and reopen PowerShell for it to take effect.

**For local development, don't set `ENV` or `CORS_ALLOWED_ORIGINS` at all.**
Their defaults (`development` and `*`) are what make `npm run dev` on
`localhost:5173` talk to `uvicorn` on `localhost:8000` without any
extra configuration. Only set them once you're actually deploying somewhere
real — see §5.

### 2.3 Database: create it and restore the seeded dump

The original commands (`createdb`, `gunzip`, `psql`) are Linux-style
invocations. On Windows these exist as `.exe` files under your PostgreSQL
`bin` folder. `gunzip` has no native Windows equivalent, so the `.gz` file is
decompressed with .NET instead.

**Find your PostgreSQL bin folder** (skip this if `psql` already works when
typed directly):

```powershell
Get-ChildItem "C:\Program Files\PostgreSQL" -Directory
```

Substitute your version number (e.g. `16`) for `<VERSION>` in the commands
below.

**Create the database:**

```powershell
& "C:\Program Files\PostgreSQL\<VERSION>\bin\createdb.exe" -U postgres icancook
```

**Decompress the seeded dump** (the `.gz` file ships at the root of this zip
— move or copy it into `backend_final_pkg` first, or adjust the paths below):

```powershell
cd C:\Users\user\Downloads\project\backend_final_pkg
$inStream = [System.IO.File]::OpenRead("$PWD\icancook_seeded_dump_sql.gz")
$outStream = [System.IO.File]::Create("$PWD\icancook_seeded_dump_sql.sql")
$gzipStream = New-Object System.IO.Compression.GzipStream($inStream, [System.IO.Compression.CompressionMode]::Decompress)
$gzipStream.CopyTo($outStream)
$gzipStream.Close()
$outStream.Close()
$inStream.Close()
```

**Restore the dump:**

```powershell
& "C:\Program Files\PostgreSQL\<VERSION>\bin\psql.exe" -U postgres -d icancook -f "icancook_seeded_dump_sql.sql"
```

The dump was made with `pg_dump` 16.15 and contains `\restrict` /
`\unrestrict` lines. If your local `psql` is older than 16, those two lines
will error — harmless, psql skips them and continues — but check your
version first so you're not surprised:

```powershell
& "C:\Program Files\PostgreSQL\<VERSION>\bin\psql.exe" --version
```

**Verify the restore actually got everything:**

```powershell
& "C:\Program Files\PostgreSQL\<VERSION>\bin\psql.exe" -U postgres -d icancook -c "SELECT count(*) FROM recipes;"
```

You're looking for **13,562** (13,463 imported Epicurious/Kaggle recipes +
99 curated Sri Lankan recipes). If you get 99, the dump didn't actually
restore — drop and recreate the DB and try again, watching the terminal for
`ERROR:` lines during the restore.

**Optional: add PostgreSQL to PATH permanently**, so you can drop the full
`.exe` paths above and just use `psql`, `createdb`, etc.:

```powershell
[System.Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Program Files\PostgreSQL\<VERSION>\bin", "User")
```

Restart PowerShell for this to take effect.

### 2.4 Tell Alembic about the existing data

The seeded dump was captured at the **baseline** schema (revision
`f131a5f3859b`) — it predates two later migrations: `add_email_verification`
(adds `users.is_verified` and the `email_verification_tokens` table) and
`seed_equipment_tags` (seeds equipment rows into `recipe_tag_vocabulary`).
So don't stamp straight to `head` — that would tell Alembic those two
migrations already ran when they didn't, leaving your database missing
`users.is_verified` entirely. That's exactly the bug behind a `500` on
login with `column users.is_verified does not exist` in the traceback (see
§7) — the fix below prevents it:

```powershell
cd C:\Users\user\Downloads\project\backend_final_pkg
alembic stamp f131a5f3859b
alembic upgrade head
```

The first command tells Alembic "the dump already has everything the
baseline migration creates" (true — don't re-run it). The second then
actually runs `add_email_verification` and `seed_equipment_tags` for real
against your restored data, adding the missing column/table and equipment
tags. `alembic history` will show you the full chain if you want to confirm
where you are at any point.

Only run `alembic upgrade head` **without** the `stamp` step first on a
genuinely empty database (no seeded dump restored). Going forward, any
schema change should be made via `alembic revision --autogenerate -m "..."`
then `alembic upgrade head` — not by hand-editing `db/schema.sql` (which is
now a reference/quickstart doc only, not the source of truth).

### 2.5 Run it

```powershell
cd C:\Users\user\Downloads\project\backend_final_pkg
uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for the full interactive API — 54
registered paths across auth (incl. `/verify` and `/resend-verification`),
pantry, recipes, favorites, bookmarks/collections/shopping-lists, profile
(incl. stats/password-change), admin, and recommend.

---

## 3. Frontend setup

```powershell
cd C:\Users\user\Downloads\project\frontend_final_pkg
npm install
Copy-Item .env.example .env
npm run dev
```

`.env` defaults to `http://localhost:8000` — edit it in VS Code if your API
runs elsewhere:

```powershell
code .env
```

Production build (output in `dist\`):

```powershell
npm run build
```

---

## 4. What's actually implemented right now

| Feature | Status |
|---|---|
| JWT auth + email verification | Done. The verification link points at the frontend (`FRONTEND_BASE_URL/verify-email?token=...`), which has a real page (`VerifyEmailPage.tsx`) that calls the API and shows loading/success/error states — clicking the link no longer dumps raw JSON. A `VerifyEmailBanner` also nudges unverified logged-in users to resend the email. Verification emails themselves are logged to the console (no real SMTP configured) — see `app/services/email.py`, written as a small interface so swapping in a real provider later is a one-class change. |
| Alembic migrations | Done — see §2.4. |
| Favorites (heart-toggle) | Done — `/api/favorites`, wired into `RecipeDetailPage` and shown on `ProfilePage`. |
| Bookmarks / Collections / Shopping lists | Done — separate feature from Favorites (organize recipes into named collections, generate a shopping list from a collection). Both exist because they serve different purposes: Favorites is a quick "I like this", Bookmarks is meal-planning. |
| Profile stats + password change | Done — `/api/profile/stats`, `/api/profile/change-password`. |
| Kitchen Mode | Done — dedicated `/recipe/:id/cook` route, prep checklist, one-step-at-a-time with Next/Back, per-step countdown timer. **The timer-resets-on-navigation issue from earlier builds is fixed**: the countdown now lives at the page level (one timer slot for the whole session, tracking which step it belongs to), so it keeps running in the background if you step away, and a small pill in the header (e.g. "4:12 (Step 3)") lets you jump back to it. Starting a second step's timer while one is already running now asks for confirmation first instead of silently overwriting it. See §7 if you want the implementation details. |
| Landing page redesign | Done — hero section with time-of-day greeting and a pantry-matched featured recipe, horizontally-scrollable "Recommended for you" rail with visible pantry-match badges, browse-by-course chips. |
| ML-02 shelf-life model | v1 (3-feature: category/subcategory/storage_condition) is what's actually served. A v2 (adds ingredient_name) was built and evaluated with an ingredient-held-out split, came out *worse*, and was deliberately not shipped — kept on disk for reference. See the provenance comment in `app/services/shelf_life.py`. This is a legitimate tested-and-rejected result, not a bug. |
| RB-01 rule-based tags | Code is done — 142 canonical tags across 9 categories (cuisine, course, dietary, spice, cooking method, occasion, equipment, allergen, texture). **Not wired into any live endpoint** — the actual `/api/recommend` route uses a separate tiered ML pipeline (`app/services/ml01/pipeline.py`), not `rb01_intent.py`. Decide whether to wire it in somewhere or document it as a standalone/tested module. |
| Universal unit conversion | **Not implemented.** Pantry and recipe-ingredient units are still stored as free text with no g/kg/lb or ml/l/cup conversion. This was scoped out (see earlier prompts) but never run. |
| Indian recipe corpus (Indian Food 101 / 6000+ Indian Recipes / RecipeNLG) | **Not implemented** — those Kaggle files were never obtained. The Epicurious/Kaggle "Food Ingredients and Recipes Dataset with Images" (13,463 rows) is the real supplementary corpus and is fully imported; if your dissertation names the other three datasets, correct that text rather than the code. |

---

## 5. Things worth fixing before this goes anywhere near production

- `JWT_SECRET_KEY` still defaults to a placeholder — must be overridden.
  **Now enforced**: the app refuses to start if `ENV=production` and
  `JWT_SECRET_KEY` is still the default. Local dev (`ENV` unset or
  `development`) is unaffected.
- CORS in `app/main.py` defaulted to `allow_origins=["*"]` with no way to
  change it without editing code. **Now configurable** via
  `CORS_ALLOWED_ORIGINS` (comma-separated origins); still defaults to `*`
  when unset, so local dev needs no changes. **Whatever origins you list
  here must include every real domain your deployed frontend is served
  from** — see §7 for what happens when it doesn't.
- Email verification only logs to console; there's no real email delivery.

---

## 6. What was verified before this was packaged

Not just assembled and hoped for the best:

- **Backend:** `import app.main` succeeds with zero errors; the OpenAPI
  schema was enumerated and confirmed 54 registered paths present (auth
  incl. `/verify` and `/resend-verification`, pantry, recipes, favorites,
  bookmarks/collections/shopping-lists, profile incl. stats/password-change,
  admin, recommend). `settings.FRONTEND_BASE_URL`/`API_BASE_URL` confirmed
  to resolve to the expected defaults and the verification link now
  resolves to `{FRONTEND_BASE_URL}/verify-email?token=...`. The startup
  secret-key check was exercised in all three states — `ENV` unset with
  the default secret (starts fine), `ENV=production` with the default
  secret (raises `RuntimeError` before serving any request), and
  `ENV=production` with a real secret (starts fine) — and
  `CORS_ALLOWED_ORIGINS` was confirmed to default to `["*"]` when unset and
  to parse correctly into a list when set.
- **Frontend:** `tsc --noEmit` passes with zero type errors across the
  entire merged tree, including the new `VerifyEmailPage.tsx` and its
  `/verify-email` route, and the reworked `KitchenModePage.tsx` timer
  state (§7); `vite build` succeeds and produces a working production
  bundle.

Neither of those was run against a live Postgres in this environment (no DB
available here) — run the alembic baseline migration against a real
throwaway database once yourself to confirm it applies cleanly, per §2.4.

---

## 7. Troubleshooting

### `500 Internal Server Error` on login — `column users.is_verified does not exist`

If `uvicorn`'s traceback ends in something like:

```
psycopg2.errors.UndefinedColumn: column users.is_verified does not exist
```

your database was stamped straight to `head` instead of following the two
-step process in §2.4, so Alembic believes the `add_email_verification`
migration already ran when it never actually touched your database. Fix it
by rewinding the stamp and then genuinely upgrading:

```powershell
cd C:\Users\user\Downloads\project\backend_final_pkg
alembic stamp f131a5f3859b
alembic upgrade head
```

This is safe to run even though you already have data — `alembic stamp`
only rewrites Alembic's bookkeeping (the `alembic_version` table), it
doesn't touch your actual tables, so `alembic upgrade head` will now find
real work to do (`ALTER TABLE users ADD COLUMN is_verified ...`, create
`email_verification_tokens`, seed equipment tags) instead of skipping it.
Confirm it worked with:

```powershell
& "C:\Program Files\PostgreSQL\<VERSION>\bin\psql.exe" -U postgres -d icancook -c "\d users"
```

— you should see `is_verified` in the column list.

### Shelf-life prediction fails with a `joblib.load` / file-not-found error

This means `SHELF_LIFE_MODEL_PATH` got set to something that isn't a real
file — usually from copy-pasting the illustrative
`$env:SHELF_LIFE_MODEL_PATH="path\to\v1\model"` line from §2.2 literally.
The app starts fine either way (the model loads lazily, on first use), so
this only shows up when a shelf-life prediction is actually requested. Fix:

```powershell
Remove-Item Env:\SHELF_LIFE_MODEL_PATH -ErrorAction SilentlyContinue
```

then restart `uvicorn`, so it falls back to the bundled v1 model under
`models/`. Only set this variable if you're pointing it at a real `.pkl`
file you actually have.

### "OPTIONS ... 400 Bad Request" on every `/api/auth/...` call

If your `uvicorn` log looks like this and the frontend can't log in or
register at all:

```
INFO: 127.0.0.1:xxxxx - "OPTIONS /api/auth/me HTTP/1.1" 400 Bad Request
INFO: 127.0.0.1:xxxxx - "OPTIONS /api/auth/login HTTP/1.1" 400 Bad Request
INFO: 127.0.0.1:xxxxx - "OPTIONS /api/auth/register HTTP/1.1" 400 Bad Request
```

this is CORS rejecting the browser's preflight request — not a bug in the
route handlers themselves (they never even get called; the `OPTIONS`
request is intercepted and answered by the CORS middleware before it
reaches your code). Starlette's `CORSMiddleware` returns exactly this
"400 Bad Request" — with a body like `Disallowed CORS origin` — whenever a
preflight's `Origin` doesn't match anything in `allow_origins`.

**The near-certain cause**: `CORS_ALLOWED_ORIGINS` is set in your
environment to something that doesn't include the origin your frontend is
actually running on (for example, you copied the production example from
§2.2 — `https://app.example.com,https://admin.example.com` — into your
local `.env`/session, while your frontend is really being served from
`http://localhost:5173`).

**Fix — pick one:**

1. For local dev, just unset it, so the wide-open default (`*`) applies:
   ```powershell
   Remove-Item Env:\CORS_ALLOWED_ORIGINS -ErrorAction SilentlyContinue
   ```
   Then restart `uvicorn`.
2. Or set it to the exact origin(s) you're really using (scheme + host +
   port, no trailing slash):
   ```powershell
   $env:CORS_ALLOWED_ORIGINS="http://localhost:5173"
   ```
   Then restart `uvicorn` — env changes aren't picked up by `--reload`.

Same logic applies if you've set `ENV=production`: that doesn't affect CORS
directly, but if you're testing locally with `ENV=production` set from an
earlier session, unset it too (`Remove-Item Env:\ENV`) unless you've also
set a real `JWT_SECRET_KEY`, or the app will refuse to start at all.

### Kitchen Mode timer used to reset when you tapped Next/Back

Fixed. The previous `StepTimer` component owned its own countdown state
keyed off the current step's `timer_seconds` prop, so navigating to a
different step remounted it and lost the running countdown. The countdown
now lives in `KitchenModePage` itself as a single `{ stepNumber, remaining,
running }` slot that ticks on an interval independent of which step is on
screen; `StepTimer` is now a plain presentational component. If you
navigate away while a timer's running, a small pill appears in the header
(`⏱ 4:12 (Step 3)`) — tapping it jumps back to that step. Trying to start a
second step's timer while one is already running now asks "Stop the Step 3
timer and start this one?" instead of silently replacing it.
