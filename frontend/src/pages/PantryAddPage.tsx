import { Check, Loader2, Sparkles, X } from 'lucide-react';
import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { InlineError } from '../components/StatusBlocks';
import { ApiError, pantryApi } from '../lib/api';
import { STORAGE_CONDITIONS, type PantryItemOut, type StorageCondition } from '../lib/types';

export default function PantryAddPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();

  const [rawName, setRawName] = useState(params.get('name') || '');
  const [quantity, setQuantity] = useState('');
  const [unit, setUnit] = useState('');
  const [storageCondition, setStorageCondition] = useState<StorageCondition>('Refrigerated');
  const [expiryDate, setExpiryDate] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [created, setCreated] = useState<PantryItemOut | null>(null);

  function close() {
  navigate(-1);   // was: navigate('/pantry')
}

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!rawName.trim()) {
      setError('Ingredient name is required.');
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const item = await pantryApi.create({
        raw_name: rawName.trim(),
        quantity: quantity.trim() ? Number(quantity) : null,
        unit: unit.trim() || null,
        storage_condition: storageCondition,
        expiry_date: expiryDate || null,
      });
      setCreated(item);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not add this item.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="flex items-center justify-center min-h-screen w-full relative p-5 bg-surface-dim/80 backdrop-blur-md">
      <div className="w-full max-w-[560px] bg-surface rounded-[36px] shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-8 pt-8 pb-6">
          <h2 className="font-heading text-2xl text-on-surface">{created ? 'Item added' : 'Add Pantry Item'}</h2>
          <button onClick={close} aria-label="Close" className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container-high text-on-surface-variant">
            <X size={18} />
          </button>
        </div>

        {created ? (
          <div className="px-8 pb-8 space-y-6 overflow-y-auto">
            <div className="w-16 h-16 rounded-full bg-tertiary-container/30 flex items-center justify-center mx-auto">
              <Check className="text-tertiary" size={28} />
            </div>
            <div className="text-center">
              <p className="font-heading text-lg text-on-surface">{created.raw_name}</p>
              <p className="font-body-md text-sm text-on-surface-variant">{created.storage_condition}</p>
            </div>
            {created.expiry_date && (
              <div className="bg-tertiary-container/20 rounded-3xl p-5 flex items-start gap-4 border border-tertiary/10">
                <div className="w-10 h-10 rounded-full bg-tertiary text-on-tertiary flex items-center justify-center shrink-0">
                  <Sparkles size={18} />
                </div>
                <div>
                  <p className="font-ui text-xs text-on-tertiary-container uppercase font-semibold">
                    {created.expiry_source === 'predicted' ? 'Predicted' : 'Label'} expiry: {created.expiry_date}
                  </p>
                  <p className="font-body-md text-sm text-on-surface-variant">
                    {created.days_to_expiry !== null ? `${created.days_to_expiry} day${created.days_to_expiry === 1 ? '' : 's'} from now` : ''}
                    {created.urgency ? ` · ${created.urgency} urgency` : ''}
                    {created.expiry_source === 'predicted' ? ' — from the ML-02 shelf-life model' : ''}
                  </p>
                </div>
              </div>
            )}
            <div className="flex gap-4">
              <button
                onClick={() => {
                  setCreated(null);
                  setRawName('');
                  setQuantity('');
                  setUnit('');
                  setExpiryDate('');
                }}
                className="flex-1 h-14 rounded-full font-ui font-semibold text-on-surface bg-surface-container-high"
              >
                Add another
              </button>
              <button onClick={close} className="flex-1 h-14 rounded-full bg-primary text-on-primary font-ui font-semibold shadow-lg">
                Done
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="px-8 pb-4 space-y-6 overflow-y-auto scrollbar-hide">
            {error && <InlineError message={error} />}

            <div className="space-y-1.5">
              <label htmlFor="rawName" className="block font-ui text-[11px] uppercase tracking-wider text-on-surface-variant pl-4">
                Ingredient
              </label>
              <input
                id="rawName"
                value={rawName}
                onChange={(e) => setRawName(e.target.value)}
                required
                className="w-full h-14 px-6 bg-surface-container rounded-full focus:outline-none focus:ring-2 focus:ring-primary-container"
                placeholder="e.g. San Marzano tomatoes"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label htmlFor="quantity" className="block font-ui text-[11px] uppercase tracking-wider text-on-surface-variant pl-4">
                  Quantity
                </label>
                <input
                  id="quantity"
                  type="number"
                  min="0"
                  step="any"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="w-full h-14 px-6 bg-surface-container rounded-full focus:outline-none focus:ring-2 focus:ring-primary-container"
                  placeholder="2"
                />
              </div>
              <div className="space-y-1.5">
                <label htmlFor="unit" className="block font-ui text-[11px] uppercase tracking-wider text-on-surface-variant pl-4">
                  Unit
                </label>
                <input
                  id="unit"
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  className="w-full h-14 px-6 bg-surface-container rounded-full focus:outline-none focus:ring-2 focus:ring-primary-container"
                  placeholder="cans, g, cups…"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="storage" className="block font-ui text-[11px] uppercase tracking-wider text-on-surface-variant pl-4">
                Storage
              </label>
              <select
                id="storage"
                value={storageCondition}
                onChange={(e) => setStorageCondition(e.target.value as StorageCondition)}
                className="w-full h-14 px-6 bg-surface-container rounded-full focus:outline-none focus:ring-2 focus:ring-primary-container"
              >
                {STORAGE_CONDITIONS.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label htmlFor="expiry" className="block font-ui text-[11px] uppercase tracking-wider text-on-surface-variant pl-4">
                Expiry date (optional — leave blank to predict)
              </label>
              <input
                id="expiry"
                type="date"
                value={expiryDate}
                onChange={(e) => setExpiryDate(e.target.value)}
                className="w-full h-14 px-6 bg-surface-container rounded-full focus:outline-none focus:ring-2 focus:ring-primary-container"
              />
            </div>

            {!expiryDate && (
              <div className="bg-tertiary-container/20 rounded-3xl p-5 flex items-start gap-4 border border-tertiary/10">
                <div className="w-10 h-10 rounded-full bg-tertiary text-on-tertiary flex items-center justify-center shrink-0">
                  <Sparkles size={18} />
                </div>
                <div className="pt-0.5">
                  <p className="font-ui text-xs text-on-tertiary-container uppercase font-semibold">Shelf life will be predicted</p>
                  <p className="font-body-md text-sm text-on-surface-variant">The real ML-02 model estimates expiry from the ingredient and storage condition.</p>
                </div>
              </div>
            )}

            <div className="sticky bottom-0 bg-surface py-4 flex justify-end gap-4">
              <button type="button" onClick={close} className="h-14 px-8 rounded-full font-ui font-semibold text-on-surface">
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="h-14 px-10 rounded-full bg-primary-container text-on-primary-container font-ui font-semibold flex items-center gap-2 shadow-lg disabled:opacity-60"
              >
                {submitting ? <Loader2 className="animate-spin" size={18} /> : <Check size={18} />}
                {submitting ? 'Saving…' : 'Save Item'}
              </button>
            </div>
          </form>
        )}
      </div>
    </main>
  );
}
