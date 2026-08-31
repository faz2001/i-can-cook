// Mirrors app/schemas/*.py in the backend, field for field. Keep in sync by
// hand -- there's no shared codegen between the two repos.

export interface UserOut {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_verified: boolean;
  dietary_preferences: string[];
  kitchen_equipment: string[];
  created_at: string;
}

export interface TokenOut {
  access_token: string;
  token_type: string;
  user: UserOut;
}

// ---- Pantry (app/schemas/pantry.py) ----

export const STORAGE_CONDITIONS = ['Refrigerated', 'Frozen', 'Pantry'] as const;
export type StorageCondition = (typeof STORAGE_CONDITIONS)[number];

export type Urgency = 'high' | 'medium' | 'low';

export interface PantryItemOut {
  id: number;
  ingredient_id: string | null;
  raw_name: string;
  quantity: number | null;
  unit: string | null;
  storage_condition: string | null;
  purchase_date: string | null;
  expiry_date: string | null;
  expiry_source: 'label' | 'predicted' | null;
  days_to_expiry: number | null;
  urgency: Urgency | null;
}

export interface PantryItemCreate {
  raw_name: string;
  quantity?: number | null;
  unit?: string | null;
  storage_condition: StorageCondition;
  purchase_date?: string | null;
  expiry_date?: string | null;
}

// ---- Recipes (app/schemas/recipe.py) ----

export type PantryStatus = 'have' | 'partial' | 'missing' | 'unmatched';

export interface IngredientLineOut {
  ingredient_id: string | null;
  name: string;
  quantity: number | null;
  unit: string | null;
  notes: string | null;
  pantry_status: PantryStatus;
  pantry_quantity_available: number | null;
}

export interface StepOut {
  step_number: number;
  instruction: string;
  duration_min: number | null;
}

export interface NutritionOut {
  calories: number | null;
  protein_g: number | null;
  carbs_g: number | null;
  fat_g: number | null;
  fibre_g: number | null;
  per: string;
  available: boolean;
}

export interface RecipeDetailOut {
  id: string;
  name_en: string;
  name_native: string | null;
  cuisine: string;
  regional_origin: string | null;
  course: string | null;
  ayurvedic_balance: string | null;
  tags: string[];
  image_url: string | null;
  base_servings: number | null;
  requested_servings: number;
  scale_factor: number;
  ingredients: IngredientLineOut[];
  steps: StepOut[];
  nutrition: NutritionOut;
  trust_score: number;
  health_score: number | null;
  source_type: string;
  source_url: string | null;
  average_rating: number | null;
  review_count: number;
  is_favorited: boolean;
}

// ---- Recipe browse/search (app/schemas/recipe_browse.py, GET /api/recipes) ----

export interface RecipeListItemOut {
  id: string;
  name_en: string;
  name_native: string | null;
  cuisine: string;
  course: string | null;
  image_url: string | null;
  tags: string[];
  servings: number | null;
  prep_time_min: number | null;
  cook_time_min: number | null;
  total_time_min: number | null;
  calories_kcal: number | null;
  trust_score: number;
  average_rating: number | null;
  review_count: number;
  source_type: string;
}

export interface RecipeBrowseResponse {
  total: number;
  limit: number;
  offset: number;
  items: RecipeListItemOut[];
}

// GET /api/recipes/facets -- live distinct course/cuisine values, for
// building filter chips/dropdowns instead of reading them off the static
// data/catalog.ts snapshot.
export interface RecipeFacetsOut {
  courses: string[];
  cuisines: string[];
}

// ---- Bookmarks / Collections / Shopping lists (app/schemas/bookmark.py) ----

export interface CollectionOut {
  id: number;
  name: string;
  recipe_count: number;
  created_at: string;
}

export interface BookmarkRecipeOut {
  recipe_id: string;
  name_en: string;
  cuisine: string | null;
  course: string | null;
  added_at: string;
}

export interface CollectionDetailOut {
  id: number;
  name: string;
  recipes: BookmarkRecipeOut[];
}

export interface ShoppingListItemOut {
  id: number;
  name: string;
  quantity: number | null;
  unit: string | null;
  is_checked: boolean;
  is_manual: boolean;
}

export interface ShoppingListOut {
  id: number;
  name: string;
  items: ShoppingListItemOut[];
}

export interface ChecklistItemOut {
  name: string;
  quantity: number | null;
  unit: string | null;
  notes: string | null;
}

export interface CookStepOut {
  step_number: number;
  instruction: string;
  duration_min: number | null;
  timer_seconds: number | null;
}

export interface CookSessionOut {
  recipe_id: string;
  name_en: string;
  requested_servings: number;
  scale_factor: number;
  total_active_time_min: number;
  prep_checklist: ChecklistItemOut[];
  steps: CookStepOut[];
}

// ---- Zero-waste (app/schemas/zero_waste.py) ----

export interface MatchedIngredient {
  canonical_id: string;
  pantry_item_name: string;
}

export interface ZeroWasteSuggestion {
  recipe_id: string;
  name_en: string;
  total_time_min: number | null;
  matched_ingredient_count: number;
  total_ingredient_count: number;
  coverage_fraction: number;
  matched_ingredients: MatchedIngredient[];
}

// ---- Favorites (app/schemas/favorite.py) ----

export interface FavoriteRecipeSummary {
  id: string;
  name_en: string;
  cuisine: string | null;
  course: string | null;
  image_url: string | null;
  servings: number | null;
  total_time_min: number | null;
}

export interface FavoriteOut {
  id: number;
  user_id: number;
  created_at: string;
  recipe: FavoriteRecipeSummary;
}

// ---- Profile stats (app/schemas/profile.py) ----

export interface ProfileStatsOut {
  pantry_item_count: number;
  favorites_count: number;
}

export interface EquipmentTagOut {
  id: string;
  label: string;
}

// ---- Admin (app/schemas/admin.py) ----

export interface DashboardSummaryOut {
  total_recipes: number;
  recipes_by_source_type: Record<string, number>;
  pending_recipe_moderation: number;
  pending_occasion_tag_proposals: number;
  recipes_below_trust_threshold: number;
  unmatched_ingredient_lines: number;
  total_users: number;
  total_reviews: number;
}

export type ModerationStatus = 'pending' | 'approved' | 'rejected';

export interface AdminRecipeListItemOut {
  id: string;
  name_en: string;
  cuisine: string;
  source_type: string;
  moderation_status: string;
  trust_score: number;
  average_rating: number | null;
  review_count: number;
  submitted_by: number | null;
}

export interface TagVocabularyOut {
  id: string;
  label: string;
  category: string | null;
  status: 'approved' | 'retired';
}

export interface OccasionTagAdminOut {
  id: string;
  label: string;
  status: 'approved' | 'proposed' | 'rejected';
  proposed_by: number | null;
  created_at: string;
}

export interface TrustScoreFlaggedRecipeOut {
  id: string;
  name_en: string;
  source_type: string;
  trust_score: number;
  average_rating: number | null;
  review_count: number;
  flag_reason: string;
}

export interface TrustScoreAuditOut {
  id: number;
  recipe_id: string;
  admin_user_id: number;
  old_value: number | null;
  new_value: number;
  reason: string | null;
  created_at: string;
}

export interface ValidationIssueOut {
  recipe_id: string;
  recipe_name: string;
  issue: string;
  severity: 'error' | 'warning';
}

export interface UnmatchedIngredientGroupOut {
  raw_name: string;
  occurrence_count: number;
  sample_recipe_ids: string[];
}

export interface IngredientOut {
  canonical_id: string;
  name: string;
  category: string | null;
  unit_default: string | null;
}

// ---- Community: reviews, occasion tags, variations (app/schemas/community.py) ----
// All scoped to a single recipe -- the community router is mounted at
// /api/recipes/{recipe_id}/..., there's no cross-recipe activity feed.

export interface ReviewOut {
  id: number;
  recipe_id: string;
  user_id: number;
  rating: number;
  review_text: string | null;
  created_at: string;
  updated_at: string;
}

export type OccasionTagStatus = 'approved' | 'proposed' | 'rejected';

export interface OccasionTagOut {
  id: string;
  label: string;
  status: OccasionTagStatus;
  vote_count: number;
  user_has_voted: boolean;
}

export interface OccasionTagVoteOut {
  occasion_tag_id: string;
  vote_count: number;
  user_has_voted: boolean;
}

export interface VariationOut {
  id: number;
  recipe_id: string;
  user_id: number;
  description: string;
  substitutions: Record<string, unknown> | null;
  created_at: string;
}