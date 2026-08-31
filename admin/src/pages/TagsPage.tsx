import { Check, X } from 'lucide-react';
import React, { useCallback, useEffect, useState } from 'react';
import { InlineError, LoadingBlock } from '../components/StatusBlocks';
import { adminTagsApi, ApiError } from '../lib/api';
import type { OccasionTagAdminOut, TagVocabularyOut } from '../lib/types';
import { PageHeader } from './OverviewPage';

function errMsg(err: unknown, fallback: string) {
  return err instanceof ApiError ? err.message : fallback;
}

export default function TagsPage() {
  const [vocabulary, setVocabulary] = useState<TagVocabularyOut[]>([]);
  const [proposals, setProposals] = useState<OccasionTagAdminOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newLabel, setNewLabel] = useState('');
  const [newCategory, setNewCategory] = useState('');
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([adminTagsApi.listVocabulary(), adminTagsApi.listOccasionProposals()])
      .then(([v, p]) => {
        setVocabulary(v);
        setProposals(p);
      })
      .catch((err) => setError(errMsg(err, 'Could not load tags.')))
      .finally(() => setLoading(false));
  }, []);

  useEffect(load, [load]);

  async function createTag(e: React.FormEvent) {
    e.preventDefault();
    if (!newLabel.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const tag = await adminTagsApi.createVocabularyTag(newLabel.trim(), newCategory.trim() || undefined);
      setVocabulary((prev) => [...prev, tag].sort((a, b) => a.label.localeCompare(b.label)));
      setNewLabel('');
      setNewCategory('');
    } catch (err) {
      setError(errMsg(err, 'Could not create that tag.'));
    } finally {
      setCreating(false);
    }
  }

  async function toggleVocabStatus(tag: TagVocabularyOut) {
    const nextStatus = tag.status === 'approved' ? 'retired' : 'approved';
    setBusyId(tag.id);
    try {
      const updated = await adminTagsApi.updateVocabularyStatus(tag.id, nextStatus);
      setVocabulary((prev) => prev.map((t) => (t.id === tag.id ? updated : t)));
    } catch (err) {
      setError(errMsg(err, 'Could not update that tag.'));
    } finally {
      setBusyId(null);
    }
  }

  async function reviewProposal(tagId: string, action: 'approve' | 'reject') {
    setBusyId(tagId);
    try {
      await adminTagsApi.reviewOccasionProposal(tagId, action);
      setProposals((prev) => prev.filter((p) => p.id !== tagId));
    } catch (err) {
      setError(errMsg(err, 'Could not review that proposal.'));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div>
      <PageHeader title="Tags" subtitle="Community-proposed occasion tags and the controlled vocabulary." />

      {loading && <LoadingBlock label="Sorting the labels…" />}
      {!loading && error && (
        <div className="mb-4">
          <InlineError message={error} />
        </div>
      )}

      {!loading && (
        <>
          <Section title={`Occasion tag proposals (${proposals.length})`}>
            {proposals.length === 0 ? (
              <p className="font-body text-sm text-ticket-dim text-center py-6">No proposals waiting on review.</p>
            ) : (
              <div className="space-y-2.5">
                {proposals.map((p) => (
                  <div key={p.id} className="flex items-center justify-between gap-3 rounded-lg border border-line px-4 py-3">
                    <div>
                      <p className="font-body text-sm text-ticket">{p.label}</p>
                      <p className="font-mono-ticket text-[10px] text-ticket-faint mt-0.5">
                        Proposed {new Date(p.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => reviewProposal(p.id, 'approve')}
                        disabled={busyId === p.id}
                        className="stamp text-mint disabled:opacity-50 hover:bg-mint-container transition-colors"
                      >
                        <Check size={12} /> Approve
                      </button>
                      <button
                        onClick={() => reviewProposal(p.id, 'reject')}
                        disabled={busyId === p.id}
                        className="stamp text-rust disabled:opacity-50 hover:bg-rust-container transition-colors"
                      >
                        <X size={12} /> Reject
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Section>

          <Section title={`Tag vocabulary (${vocabulary.length})`}>
            <form onSubmit={createTag} className="flex flex-col sm:flex-row gap-2 mb-5">
              <input
                type="text"
                placeholder="New tag label"
                value={newLabel}
                onChange={(e) => setNewLabel(e.target.value)}
                className="flex-1 h-10 px-4 rounded-lg bg-backstage border border-line text-ticket font-body text-sm focus:outline-none focus:ring-2 focus:ring-ember/40"
              />
              <input
                type="text"
                placeholder="Category (optional)"
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="sm:w-48 h-10 px-4 rounded-lg bg-backstage border border-line text-ticket font-body text-sm focus:outline-none focus:ring-2 focus:ring-ember/40"
              />
              <button
                type="submit"
                disabled={creating || !newLabel.trim()}
                className="h-10 px-5 rounded-lg bg-ember text-backstage font-body text-xs font-semibold shrink-0 disabled:opacity-50 hover:bg-ember-dim transition-colors"
              >
                {creating ? 'Adding…' : 'Add tag'}
              </button>
            </form>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
              {vocabulary.map((tag) => (
                <div
                  key={tag.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-line px-4 py-3"
                >
                  <div>
                    <p className="font-body text-sm text-ticket">{tag.label}</p>
                    <p className="font-mono-ticket text-[10px] text-ticket-faint">{tag.category || 'uncategorized'}</p>
                  </div>
                  <button
                    onClick={() => toggleVocabStatus(tag)}
                    disabled={busyId === tag.id}
                    className={`font-mono-ticket text-[10px] font-semibold px-3 py-1.5 rounded-full shrink-0 disabled:opacity-50 ${
                      tag.status === 'approved'
                        ? 'bg-backstage-high text-ticket-dim'
                        : 'bg-ember-container text-ember'
                    }`}
                  >
                    {tag.status === 'approved' ? 'Retire' : 'Reapprove'}
                  </button>
                </div>
              ))}
            </div>
          </Section>
        </>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="chit p-6 mb-5">
      <h2 className="font-display text-sm font-semibold text-ticket mb-4">{title}</h2>
      {children}
    </section>
  );
}
