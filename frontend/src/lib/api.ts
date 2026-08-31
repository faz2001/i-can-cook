import type {
  AdminRecipeListItemOut,
  CollectionDetailOut,
  CollectionOut,
  CookSessionOut,
  DashboardSummaryOut,
  EquipmentTagOut,
  FavoriteOut,
  IngredientOut,
  OccasionTagAdminOut,
  OccasionTagOut,
  OccasionTagVoteOut,
  PantryItemCreate,
  PantryItemOut,
  ProfileStatsOut,
  RecipeBrowseResponse,
  RecipeDetailOut,
  RecipeFacetsOut,
  ReviewOut,
  ShoppingListOut,
  TagVocabularyOut,
  TokenOut,
  TrustScoreAuditOut,
  TrustScoreFlaggedRecipeOut,
  UnmatchedIngredientGroupOut,
  UserOut,
  ValidationIssueOut,
  VariationOut,
  ZeroWasteSuggestion,
} from './types';

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') || 'http://localhost:8000';

const TOKEN_KEY = 'icancook_token';

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

// ---- Auth ----

export const authApi = {
  register: (email: string, password: string, full_name: string) =>
    request<TokenOut>('/api/auth/register', { method: 'POST', body: { email, password, full_name }, auth: false }),

  login: (email: string, password: string) =>
    request<TokenOut>('/api/auth/login', { method: 'POST', body: { email, password }, auth: false }),

  me: () => request<UserOut>('/api/auth/me'),

  resendVerification: () =>
    request<{ message: string }>('/api/auth/resend-verification', { method: 'POST' }),

  verifyEmail: (token: string) =>
    request<{ message: string }>('/api/auth/verify', { auth: false, query: { token } }),
};

// ---- Profile ----

export const profileApi = {
  get: () => request<UserOut>('/api/profile'),
  stats: () => request<ProfileStatsOut>('/api/profile/stats'),
  update: (payload: { full_name?: string; dietary_preferences?: string[]; kitchen_equipment?: string[] }) =>
    request<UserOut>('/api/profile', { method: 'PATCH', body: payload }),
  changePassword: (current_password: string, new_password: string) =>
    request<void>('/api/profile/change-password', { method: 'POST', body: { current_password, new_password } }),
};

// ---- Tags ----

export const tagsApi = {
  // Canonical "equipment a user might own" list -- DB-backed (recipe_tag_vocabulary,
  // category='equipment'), replacing the hardcoded EQUIPMENT_OPTIONS that used to
  // live in ProfilePage.tsx so it can't drift out of sync with the backend.
  equipment: () => request<EquipmentTagOut[]>('/api/tags/equipment', { auth: false }),
};

// ---- Favorites ----

export const favoritesApi = {
  list: () => request<FavoriteOut[]>('/api/favorites'),
  add: (recipeId: string) => request<FavoriteOut>(`/api/recipes/${recipeId}/favorite`, { method: 'POST' }),
  remove: (recipeId: string) => request<void>(`/api/recipes/${recipeId}/favorite`, { method: 'DELETE' }),
};

// ---- Pantry ----

export const pantryApi = {
  list: () => request<PantryItemOut[]>('/api/pantry'),
  create: (payload: PantryItemCreate) => request<PantryItemOut>('/api/pantry', { method: 'POST', body: payload }),
  remove: (id: number) => request<void>(`/api/pantry/${id}`, { method: 'DELETE' }),
};

// ---- Recipes ----

export const recipesApi = {
  browse: (
    params: {
      q?: string;
      cuisine?: string;
      course?: string;
      tag?: string;
      max_time_min?: number;
      sort_by?: 'relevance' | 'rating' | 'newest' | 'quickest';
      limit?: number;
      offset?: number;
    } = {}
  ) =>
    request<RecipeBrowseResponse>('/api/recipes', {
      auth: false,
      query: {
        search: params.q,
        cuisine: params.cuisine,
        course: params.course,
        tag: params.tag,
        max_time_min: params.max_time_min,
        sort_by: params.sort_by,
        limit: params.limit,
        offset: params.offset,
      },
    }),
  // Live, DB-backed filter options for course chips / cuisine dropdown --
  // replaces deriving them from the static 99-recipe CATALOG snapshot in
  // data/catalog.ts, which could never reflect cuisines/courses introduced
  // by later imports.
  facets: () => request<RecipeFacetsOut>('/api/recipes/facets', { auth: false }),
  detail: (id: string, servings?: number) =>
    request<RecipeDetailOut>(`/api/recipes/${id}`, { query: { servings } }),
  cookSession: (id: string, servings?: number) =>
    request<CookSessionOut>(`/api/recipes/${id}/cook`, { query: { servings }, auth: false }),
};

// ---- Zero-waste ----

export const zeroWasteApi = {
  suggestions: (withinDays = 3, limit = 10) =>
    request<ZeroWasteSuggestion[]>('/api/recipes/zero-waste-suggestions', {
      query: { within_days: withinDays, limit },
    }),
};

// ---- Bookmarks / Collections / Shopping lists ----

export const bookmarksApi = {
  listCollections: () => request<CollectionOut[]>('/api/bookmarks/collections'),
  createCollection: (name: string) =>
    request<CollectionOut>('/api/bookmarks/collections', { method: 'POST', body: { name } }),
  collectionDetail: (collectionId: number) =>
    request<CollectionDetailOut>(`/api/bookmarks/collections/${collectionId}`),

  addBookmark: (recipeId: string, collectionId?: number) =>
    request<void>('/api/bookmarks', {
      method: 'POST',
      body: { recipe_id: recipeId, collection_id: collectionId ?? null },
    }),
  removeBookmark: (collectionId: number, recipeId: string) =>
    request<void>(`/api/bookmarks/collections/${collectionId}/recipes/${recipeId}`, { method: 'DELETE' }),

  generateShoppingList: (collectionId: number, name?: string) =>
    request<ShoppingListOut>(`/api/bookmarks/collections/${collectionId}/shopping-list`, {
      method: 'POST',
      body: { name: name || null },
    }),
  shoppingListDetail: (shoppingListId: number) =>
    request<ShoppingListOut>(`/api/bookmarks/shopping-lists/${shoppingListId}`),
  addShoppingListItem: (shoppingListId: number, payload: { name: string; quantity?: number; unit?: string }) =>
    request<void>(`/api/bookmarks/shopping-lists/${shoppingListId}/items`, { method: 'POST', body: payload }),
  toggleShoppingListItem: (shoppingListId: number, itemId: number) =>
    request<void>(`/api/bookmarks/shopping-lists/${shoppingListId}/items/${itemId}`, { method: 'PATCH' }),
  removeShoppingListItem: (shoppingListId: number, itemId: number) =>
    request<void>(`/api/bookmarks/shopping-lists/${shoppingListId}/items/${itemId}`, { method: 'DELETE' }),
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

// ---- Community: reviews, occasion tags, variations (app/routers/community.py) ----
// Every endpoint is scoped to one recipe -- there's no cross-recipe feed to fetch here.

export const communityApi = {
  listReviews: (recipeId: string) => request<ReviewOut[]>(`/api/recipes/${recipeId}/reviews`),

  upsertReview: (recipeId: string, rating: number, reviewText?: string) =>
    request<ReviewOut>(`/api/recipes/${recipeId}/reviews`, {
      method: 'POST',
      body: { rating, review_text: reviewText || undefined },
    }),

  deleteOwnReview: (recipeId: string) =>
    request<void>(`/api/recipes/${recipeId}/reviews`, { method: 'DELETE' }),

  listOccasionTags: (recipeId: string) => request<OccasionTagOut[]>(`/api/recipes/${recipeId}/occasion-tags`),

  proposeOccasionTag: (recipeId: string, label: string) =>
    request<OccasionTagOut>(`/api/recipes/${recipeId}/occasion-tags`, {
      method: 'POST',
      body: { label },
    }),

  toggleOccasionTagVote: (recipeId: string, tagId: string) =>
    request<OccasionTagVoteOut>(`/api/recipes/${recipeId}/occasion-tags/${tagId}/vote`, { method: 'POST' }),

  listVariations: (recipeId: string) => request<VariationOut[]>(`/api/recipes/${recipeId}/variations`),

  logVariation: (recipeId: string, description: string, substitutions?: Record<string, unknown>) =>
    request<VariationOut>(`/api/recipes/${recipeId}/variations`, {
      method: 'POST',
      body: { description, substitutions: substitutions || undefined },
    }),
};