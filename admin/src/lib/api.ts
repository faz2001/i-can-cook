import type {
  AdminRecipeListItemOut,
  DashboardSummaryOut,
  IngredientOut,
  OccasionTagAdminOut,
  TagVocabularyOut,
  TokenOut,
  TrustScoreAuditOut,
  TrustScoreFlaggedRecipeOut,
  UnmatchedIngredientGroupOut,
  UserOut,
  ValidationIssueOut,
} from './types';

// Same backend the consumer app talks to -- point this at wherever
// backend_final_pkg is running. No backend changes are required for this
// panel to work: it uses the same /api/auth/* and /api/admin/* routes,
// which are already gated server-side by require_admin.
const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || 'http://localhost:8000';

const TOKEN_KEY = 'icancook_admin_token';

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

/** Pulls a human-readable message out of FastAPI's error shape, which is
 * either {detail: string} (HTTPException) or {detail: [{msg, loc}, ...]}
 * (pydantic validation, 422). */
function extractErrorMessage(body: unknown, fallback: string): string {
  if (body && typeof body === 'object' && 'detail' in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => {
          if (d && typeof d === 'object' && 'msg' in d) {
            const loc = Array.isArray((d as any).loc) ? (d as any).loc.slice(-1)[0] : '';
            return loc ? `${loc}: ${(d as any).msg}` : String((d as any).msg);
          }
          return String(d);
        })
        .join('; ');
    }
  }
  return fallback;
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean; query?: Record<string, string | number | undefined> } = {}
): Promise<T> {
  const { method = 'GET', body, auth = true, query } = options;

  let url = `${BASE_URL}${path}`;
  if (query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') params.set(k, String(v));
    }
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (auth) {
    const token = getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  }

  let res: Response;
  try {
    res = await fetch(url, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, `Can't reach the server at ${BASE_URL}. Is the backend running?`);
  }

  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const data = text ? safeJsonParse(text) : undefined;

  if (!res.ok) {
    if (res.status === 401) setToken(null);
    throw new ApiError(res.status, extractErrorMessage(data, `Request failed (${res.status})`));
  }

  return data as T;
}

function safeJsonParse(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

// ---- Auth (app/routers/auth.py) ----
// Deliberately no register() here -- admin accounts are provisioned by an
// existing admin (via the DB, a seed script, or a future "invite" endpoint),
// not self-service sign-up.

export const authApi = {
  login: (email: string, password: string) =>
    request<TokenOut>('/api/auth/login', { method: 'POST', body: { email, password }, auth: false }),

  me: () => request<UserOut>('/api/auth/me'),
};

// ---- Admin: dashboard (app/routers/admin_dashboard.py) ----

export const adminDashboardApi = {
  summary: () => request<DashboardSummaryOut>('/api/admin/dashboard'),
};

// ---- Admin: recipes / moderation queue (app/routers/admin_recipes.py) ----

export const adminRecipesApi = {
  list: (
    params: {
      source_type?: string;
      moderation_status?: string;
      cuisine?: string;
      search?: string;
      limit?: number;
      offset?: number;
    } = {}
  ) => request<AdminRecipeListItemOut[]>('/api/admin/recipes', { query: params }),

  pending: () => request<AdminRecipeListItemOut[]>('/api/admin/recipes/pending'),

  moderate: (recipeId: string, action: 'approve' | 'reject', reason?: string) =>
    request<AdminRecipeListItemOut>(`/api/admin/recipes/${recipeId}/moderate`, {
      method: 'POST',
      body: { action, reason: reason || undefined },
    }),

  remove: (recipeId: string) => request<void>(`/api/admin/recipes/${recipeId}`, { method: 'DELETE' }),
};

// ---- Admin: tags (app/routers/admin_tags.py) ----

export const adminTagsApi = {
  listVocabulary: (statusFilter?: string) =>
    request<TagVocabularyOut[]>('/api/admin/tags/vocabulary', { query: { status_filter: statusFilter } }),

  createVocabularyTag: (label: string, category?: string) =>
    request<TagVocabularyOut>('/api/admin/tags/vocabulary', {
      method: 'POST',
      body: { label, category: category || undefined },
    }),

  updateVocabularyStatus: (tagId: string, tagStatus: 'approved' | 'retired') =>
    request<TagVocabularyOut>(`/api/admin/tags/vocabulary/${tagId}`, {
      method: 'PATCH',
      body: { status: tagStatus },
    }),

  listOccasionProposals: () => request<OccasionTagAdminOut[]>('/api/admin/tags/occasion-proposals'),

  reviewOccasionProposal: (tagId: string, action: 'approve' | 'reject') =>
    request<OccasionTagAdminOut>(`/api/admin/tags/occasion-proposals/${tagId}/review`, {
      method: 'POST',
      body: { action },
    }),
};

// ---- Admin: trust scores (app/routers/admin_trust_scores.py) ----

export const adminTrustScoresApi = {
  flagged: () => request<TrustScoreFlaggedRecipeOut[]>('/api/admin/trust-scores/flagged'),

  override: (recipeId: string, trustScore: number, reason?: string) =>
    request<TrustScoreAuditOut>(`/api/admin/trust-scores/${recipeId}`, {
      method: 'PATCH',
      body: { trust_score: trustScore, reason: reason || undefined },
    }),

  auditTrail: (recipeId: string) => request<TrustScoreAuditOut[]>(`/api/admin/trust-scores/${recipeId}/audit`),
};

// ---- Admin: dataset (app/routers/admin_dataset.py) ----

export const adminDatasetApi = {
  validate: () => request<ValidationIssueOut[]>('/api/admin/dataset/validate'),

  unmatchedIngredients: () =>
    request<UnmatchedIngredientGroupOut[]>('/api/admin/dataset/unmatched-ingredients'),

  resolveUnmatchedIngredient: (rawName: string, ingredientId: string) =>
    request<void>('/api/admin/dataset/unmatched-ingredients/resolve', {
      method: 'POST',
      body: { raw_name: rawName, ingredient_id: ingredientId },
    }),

  listIngredients: (search?: string) =>
    request<IngredientOut[]>('/api/admin/dataset/ingredients', { query: { search } }),
};
