import { Check, MessageSquare, Plus, ShieldQuestion, Sparkles, Star, ThumbsUp, Trash2 } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { communityApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { OccasionTagOut, ReviewOut, VariationOut } from '../lib/types';
import { InlineError } from './StatusBlocks';

/** Reviewer identity beyond the current user isn't available from the API --
 * ReviewOut/VariationOut only return a bare user_id, and there's no public
 * user-lookup endpoint. So everyone but the signed-in user is shown as an
 * anonymous "Community member" rather than a fabricated name. */
function attributionLabel(entryUserId: number, currentUserId: number | undefined): string {
  return entryUserId === currentUserId ? 'You' : 'Community member';
}

export function CommunitySection({ recipeId }: { recipeId: string }) {
  return (
    <section className="flex flex-col gap-6 mt-12">
      <h2 className="font-display text-2xl md:text-3xl text-on-surface">Community</h2>
      <ReviewsPanel recipeId={recipeId} />
      <OccasionTagsPanel recipeId={recipeId} />
      <VariationsPanel recipeId={recipeId} />
    </section>
  );
}

// ---------------------------------------------------------------------------
// Reviews
// ---------------------------------------------------------------------------

function ReviewsPanel({ recipeId }: { recipeId: string }) {
  const { user } = useAuth();
  const [reviews, setReviews] = useState<ReviewOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState(false);
  const [ratingDraft, setRatingDraft] = useState(5);
  const [textDraft, setTextDraft] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    communityApi
      .listReviews(recipeId)
      .then(setReviews)
      .catch(() => setError('Could not load reviews for this recipe.'))
      .finally(() => setLoading(false));
  }, [recipeId]);

  const ownReview = reviews.find((r) => r.user_id === user?.id);

  function startEdit() {
    setRatingDraft(ownReview?.rating ?? 5);
    setTextDraft(ownReview?.review_text ?? '');
    setEditing(true);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const saved = await communityApi.upsertReview(recipeId, ratingDraft, textDraft.trim() || undefined);
      setReviews((prev) => {
        const withoutOwn = prev.filter((r) => r.user_id !== saved.user_id);
        return [saved, ...withoutOwn];
      });
      setEditing(false);
    } catch {
      setError('Could not save your review.');
    } finally {
      setSaving(false);
    }
  }

  async function removeOwn() {
    setSaving(true);
    setError(null);
    try {
      await communityApi.deleteOwnReview(recipeId);
      setReviews((prev) => prev.filter((r) => r.user_id !== user?.id));
      setEditing(false);
    } catch {
      setError('Could not remove your review.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="bg-surface-container-lowest rounded-[36px] p-6 md:p-8 shadow-sm border border-outline-variant/10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-heading text-lg text-on-surface flex items-center gap-2">
          <MessageSquare size={17} className="text-primary" /> Reviews ({reviews.length})
        </h3>
        {!editing && (
          <button
            onClick={startEdit}
            className="text-primary font-ui text-xs font-semibold"
          >
            {ownReview ? 'Edit your review' : 'Write a review'}
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4">
          <InlineError message={error} />
        </div>
      )}

      {editing && (
        <form onSubmit={submit} className="mb-6 bg-surface-container rounded-2xl p-5 flex flex-col gap-4">
          <div className="flex items-center gap-1.5">
            {[1, 2, 3, 4, 5].map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setRatingDraft(n)}
                aria-label={`${n} star${n === 1 ? '' : 's'}`}
              >
                <Star
                  size={22}
                  className={n <= ratingDraft ? 'text-primary' : 'text-outline-variant'}
                  fill={n <= ratingDraft ? 'currentColor' : 'none'}
                />
              </button>
            ))}
          </div>
          <textarea
            value={textDraft}
            onChange={(e) => setTextDraft(e.target.value)}
            placeholder="Share how it turned out (optional)"
            rows={3}
            className="w-full px-4 py-3 rounded-2xl bg-surface-container-lowest border border-outline-variant/30 font-body-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-container resize-none"
          />
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={saving}
              className="flex items-center gap-2 bg-primary text-on-primary px-5 py-2.5 rounded-full font-ui text-xs font-semibold shadow-sm disabled:opacity-50"
            >
              <Check size={14} /> {saving ? 'Saving…' : 'Save review'}
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              disabled={saving}
              className="text-on-surface-variant font-ui text-xs font-semibold disabled:opacity-50"
            >
              Cancel
            </button>
            {ownReview && (
              <button
                type="button"
                onClick={removeOwn}
                disabled={saving}
                className="flex items-center gap-1.5 text-error font-ui text-xs font-semibold ml-auto disabled:opacity-50"
              >
                <Trash2 size={13} /> Delete
              </button>
            )}
          </div>
        </form>
      )}

      {loading ? (
        <p className="font-body-md text-sm text-on-surface-variant text-center py-6">Loading reviews…</p>
      ) : reviews.length === 0 ? (
        <p className="font-body-md text-sm text-on-surface-variant text-center py-6">
          No reviews yet — be the first to share how it went.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {reviews.map((review) => (
            <div key={review.id} className="rounded-2xl border border-outline-variant/20 p-4">
              <div className="flex items-center justify-between gap-3 mb-1.5">
                <div className="flex items-center gap-1">
                  {[1, 2, 3, 4, 5].map((n) => (
                    <Star
                      key={n}
                      size={13}
                      className={n <= review.rating ? 'text-primary' : 'text-outline-variant'}
                      fill={n <= review.rating ? 'currentColor' : 'none'}
                    />
                  ))}
                </div>
                <span className="font-ui text-[11px] text-on-surface-variant">
                  {attributionLabel(review.user_id, user?.id)} ·{' '}
                  {new Date(review.updated_at).toLocaleDateString()}
                </span>
              </div>
              {review.review_text && (
                <p className="font-body-md text-sm text-on-surface leading-relaxed">{review.review_text}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Occasion tags -- community voting on "good for a rainy day" style tags
// ---------------------------------------------------------------------------

function OccasionTagsPanel({ recipeId }: { recipeId: string }) {
  const [tags, setTags] = useState<OccasionTagOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const [proposing, setProposing] = useState(false);
  const [labelDraft, setLabelDraft] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    communityApi
      .listOccasionTags(recipeId)
      .then(setTags)
      .catch(() => setError('Could not load occasion tags.'))
      .finally(() => setLoading(false));
  }, [recipeId]);

  async function vote(tagId: string) {
    setBusyId(tagId);
    try {
      const result = await communityApi.toggleOccasionTagVote(recipeId, tagId);
      setTags((prev) =>
        prev.map((t) =>
          t.id === tagId ? { ...t, vote_count: result.vote_count, user_has_voted: result.user_has_voted } : t
        )
      );
    } catch {
      setError('Could not update your vote.');
    } finally {
      setBusyId(null);
    }
  }

  async function propose(e: React.FormEvent) {
    e.preventDefault();
    if (!labelDraft.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const tag = await communityApi.proposeOccasionTag(recipeId, labelDraft.trim());
      setTags((prev) => {
        const withoutExisting = prev.filter((t) => t.id !== tag.id);
        return [...withoutExisting, tag];
      });
      setLabelDraft('');
      setProposing(false);
    } catch {
      setError('Could not propose that tag.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="bg-surface-container-lowest rounded-[36px] p-6 md:p-8 shadow-sm border border-outline-variant/10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-heading text-lg text-on-surface flex items-center gap-2">
          <Sparkles size={17} className="text-primary" /> Good for…
        </h3>
        {!proposing && (
          <button
            onClick={() => setProposing(true)}
            className="flex items-center gap-1 text-primary font-ui text-xs font-semibold"
          >
            <Plus size={14} /> Propose a tag
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4">
          <InlineError message={error} />
        </div>
      )}

      {proposing && (
        <form onSubmit={propose} className="flex flex-col sm:flex-row gap-2 mb-6">
          <input
            type="text"
            placeholder="e.g. Rainy day, Sunday lunch"
            value={labelDraft}
            onChange={(e) => setLabelDraft(e.target.value)}
            className="flex-1 h-10 px-4 rounded-full bg-surface-container border border-outline-variant/30 font-body-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-container"
          />
          <div className="flex gap-2 shrink-0">
            <button
              type="submit"
              disabled={submitting || !labelDraft.trim()}
              className="h-10 px-5 rounded-full bg-primary text-on-primary font-ui text-xs font-semibold disabled:opacity-50"
            >
              {submitting ? 'Adding…' : 'Submit'}
            </button>
            <button
              type="button"
              onClick={() => setProposing(false)}
              disabled={submitting}
              className="h-10 px-4 rounded-full bg-surface-container text-on-surface-variant font-ui text-xs font-semibold disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="font-body-md text-sm text-on-surface-variant text-center py-4">Loading tags…</p>
      ) : tags.length === 0 ? (
        <p className="font-body-md text-sm text-on-surface-variant text-center py-4">
          No occasion tags yet — propose one above.
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {tags.map((tag) => (
            <button
              key={tag.id}
              onClick={() => vote(tag.id)}
              disabled={busyId === tag.id}
              className={`flex items-center gap-2 px-4 py-2 rounded-full font-ui text-xs font-medium border transition-colors disabled:opacity-50 ${
                tag.user_has_voted
                  ? 'bg-primary text-on-primary border-primary'
                  : 'bg-surface-container text-on-surface-variant border-outline-variant/30 hover:bg-surface-container-high'
              }`}
            >
              <ThumbsUp size={12} />
              {tag.label}
              <span className="font-heading">{tag.vote_count}</span>
              {tag.status === 'proposed' && (
                <span title="Awaiting admin approval">
                  <ShieldQuestion size={12} className="opacity-70" />
                </span>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Variations -- community-logged tweaks to the recipe
// ---------------------------------------------------------------------------

function VariationsPanel({ recipeId }: { recipeId: string }) {
  const { user } = useAuth();
  const [variations, setVariations] = useState<VariationOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [logging, setLogging] = useState(false);
  const [descriptionDraft, setDescriptionDraft] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    setLoading(true);
    setError(null);
    communityApi
      .listVariations(recipeId)
      .then(setVariations)
      .catch(() => setError('Could not load logged variations.'))
      .finally(() => setLoading(false));
  }, [recipeId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!descriptionDraft.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      // The API accepts a free-form `substitutions` object alongside the
      // description, but there's no defined schema for its shape -- so this
      // form only captures the description, which is the one field with a
      // clear UI meaning.
      const variation = await communityApi.logVariation(recipeId, descriptionDraft.trim());
      setVariations((prev) => [variation, ...prev]);
      setDescriptionDraft('');
      setLogging(false);
    } catch {
      setError('Could not log that variation.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="bg-surface-container-lowest rounded-[36px] p-6 md:p-8 shadow-sm border border-outline-variant/10">
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-heading text-lg text-on-surface">Variations people have tried</h3>
        {!logging && (
          <button
            onClick={() => setLogging(true)}
            className="flex items-center gap-1 text-primary font-ui text-xs font-semibold"
          >
            <Plus size={14} /> Log a variation
          </button>
        )}
      </div>

      {error && (
        <div className="mb-4">
          <InlineError message={error} />
        </div>
      )}

      {logging && (
        <form onSubmit={submit} className="mb-6 flex flex-col gap-3">
          <textarea
            value={descriptionDraft}
            onChange={(e) => setDescriptionDraft(e.target.value)}
            placeholder="What did you change? e.g. Used coconut oil instead of ghee"
            rows={2}
            className="w-full px-4 py-3 rounded-2xl bg-surface-container border border-outline-variant/30 font-body-md text-sm focus:outline-none focus:ring-2 focus:ring-primary-container resize-none"
          />
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={submitting || !descriptionDraft.trim()}
              className="bg-primary text-on-primary px-5 py-2.5 rounded-full font-ui text-xs font-semibold shadow-sm disabled:opacity-50"
            >
              {submitting ? 'Saving…' : 'Save variation'}
            </button>
            <button
              type="button"
              onClick={() => setLogging(false)}
              disabled={submitting}
              className="text-on-surface-variant font-ui text-xs font-semibold disabled:opacity-50"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="font-body-md text-sm text-on-surface-variant text-center py-4">Loading variations…</p>
      ) : variations.length === 0 ? (
        <p className="font-body-md text-sm text-on-surface-variant text-center py-4">
          No variations logged yet.
        </p>
      ) : (
        <div className="flex flex-col gap-3">
          {variations.map((v) => (
            <div key={v.id} className="rounded-2xl border border-outline-variant/20 p-4">
              <p className="font-body-md text-sm text-on-surface leading-relaxed">{v.description}</p>
              <p className="font-ui text-[11px] text-on-surface-variant mt-1.5">
                {attributionLabel(v.user_id, user?.id)} · {new Date(v.created_at).toLocaleDateString()}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}