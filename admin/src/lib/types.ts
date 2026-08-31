// ---- Auth (app/schemas/auth.py) ----

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

// ---- Admin: dashboard (app/schemas/admin.py) ----

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

export interface AdminRecipeListItemOut {
  id: string;
  name_en: string;
  cuisine: string;
  source_type: string;
  moderation_status: string;
  trust_score: number;
  average_rating: number | null;
  review_count: number;
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
