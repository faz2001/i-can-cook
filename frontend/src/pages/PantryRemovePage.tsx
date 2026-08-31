import { Loader2, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useLocation, useNavigate, useParams } from 'react-router-dom';
import { InlineError } from '../components/StatusBlocks';
import { ApiError, pantryApi } from '../lib/api';

export default function PantryRemovePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const name = (location.state as { name?: string } | null)?.name;

  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);

  function cancel() {
  navigate(-1);   // was: navigate('/pantry')
}

  async function confirmDelete() {
  if (!id) return;
  setError(null);
  setDeleting(true);
  try {
    await pantryApi.remove(Number(id));
    navigate(-1);   // was: navigate('/pantry')
  } catch (err) {
    setError(err instanceof ApiError ? err.message : 'Could not remove this item.');
    setDeleting(false);
  }
}

  return (
    <main className="flex items-center justify-center min-h-screen w-full relative p-5 bg-surface-dim/80 backdrop-blur-md">
      <div className="w-full max-w-[400px] bg-surface rounded-[36px] shadow-xl p-8 flex flex-col items-center text-center border border-white/20">
        <div className="w-16 h-16 rounded-full bg-error-container/60 flex items-center justify-center mb-6">
          <Trash2 className="text-error" size={28} />
        </div>
        <h2 className="font-heading text-xl text-on-surface mb-3">Remove {name ? `"${name}"` : 'this item'}?</h2>
        <p className="font-body-md text-on-surface-variant mb-6 px-2">This removes it from your pantry for good — recipes will stop counting it as something you have.</p>
        {error && (
          <div className="w-full mb-4">
            <InlineError message={error} />
          </div>
        )}
        <div className="flex w-full gap-4">
          <button onClick={cancel} disabled={deleting} className="flex-1 bg-surface-container-high text-on-surface font-ui py-3.5 rounded-full border border-outline-variant/30 uppercase text-xs font-semibold disabled:opacity-60">
            Cancel
          </button>
          <button
            onClick={confirmDelete}
            disabled={deleting}
            className="flex-1 bg-error text-on-error font-ui py-3.5 rounded-full shadow-lg uppercase text-xs font-semibold flex items-center justify-center gap-2 disabled:opacity-70"
          >
            {deleting ? <Loader2 className="animate-spin" size={16} /> : null}
            {deleting ? 'Removing…' : 'Delete'}
          </button>
        </div>
      </div>
    </main>
  );
}
