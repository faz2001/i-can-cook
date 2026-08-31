import { AlertCircle, Plus, Snowflake, Refrigerator, Package, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainHeader } from '../components/MainHeader';
import { MobileBottomNav } from '../components/MobileBottomNav';
import { EmptyBlock, ErrorBlock, LoadingBlock } from '../components/StatusBlocks';
import { ApiError, pantryApi } from '../lib/api';
import type { PantryItemOut, Urgency } from '../lib/types';

const URGENCY_STYLE: Record<Urgency, string> = {
  high: 'bg-error-container text-on-error-container',
  medium: 'bg-primary-container/30 text-on-primary-container',
  low: 'bg-surface-container-high text-on-surface-variant',
};

const STORAGE_ICON = {
  Frozen: Snowflake,
  Refrigerated: Refrigerator,
  Pantry: Package,
} as const;

export default function PantryPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<PantryItemOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await pantryApi.list();
      setItems(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load your pantry.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div className="bg-surface min-h-screen">
      <MainHeader />
      <main className="pt-32 pb-24 max-w-[1440px] mx-auto px-5 md:px-20">
        <div className="flex flex-wrap justify-between items-center gap-4 mb-10">
          <div>
            <h1 className="font-display text-3xl md:text-5xl text-on-surface">Your Digital Pantry</h1>
            {items && <p className="font-body-md text-on-surface-variant mt-1">{items.length} item{items.length === 1 ? '' : 's'} tracked</p>}
          </div>
          <button
            onClick={() => navigate('/pantry-add')}
            className="bg-primary text-on-primary px-6 py-3 rounded-full flex items-center gap-2 font-ui font-semibold shadow-lg shrink-0"
          >
            <Plus size={18} /> Add Item
          </button>
        </div>

        {loading && <LoadingBlock label="Loading your pantry…" />}
        {!loading && error && <ErrorBlock message={error} onRetry={load} />}
        {!loading && !error && items && items.length === 0 && (
          <EmptyBlock
            icon={<Package className="text-outline" size={40} />}
            title="Your pantry is empty"
            description="Add what's in your kitchen and recipes will show you exactly what you're missing."
            action={
              <button onClick={() => navigate('/pantry-add')} className="mt-2 flex items-center gap-2 bg-primary text-on-primary px-6 py-3 rounded-full font-ui font-semibold shadow-md">
                <Plus size={16} /> Add your first item
              </button>
            }
          />
        )}

        {!loading && !error && items && items.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {items.map((item) => {
              const StorageIcon = (item.storage_condition && STORAGE_ICON[item.storage_condition as keyof typeof STORAGE_ICON]) || Package;
              return (
                <div key={item.id} className="bg-surface-container/60 p-4 rounded-[24px] border border-outline-variant/20 shadow-sm">
                  <div className="flex gap-4">
                    <div className="w-14 h-14 rounded-2xl bg-primary-container/20 flex items-center justify-center shrink-0">
                      <StorageIcon className="text-primary" size={22} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-heading text-on-surface leading-tight truncate">{item.raw_name}</h3>
                      <p className="text-sm text-on-surface-variant">
                        {item.storage_condition || 'Unspecified'}
                        {item.quantity !== null ? ` • ${item.quantity}${item.unit ? ` ${item.unit}` : ''}` : ''}
                      </p>
                      {item.urgency && item.days_to_expiry !== null && (
                        <span className={`inline-flex items-center gap-1 mt-2 text-[10px] font-ui font-semibold uppercase tracking-wide px-2 py-0.5 rounded-full ${URGENCY_STYLE[item.urgency]}`}>
                          {item.urgency === 'high' && <AlertCircle size={11} />}
                          {item.days_to_expiry <= 0 ? 'Expires today' : `${item.days_to_expiry} day${item.days_to_expiry === 1 ? '' : 's'} left`}
                          {item.expiry_source === 'predicted' ? ' · predicted' : ''}
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => navigate(`/pantry-remove/${item.id}`, { state: { name: item.raw_name } })}
                      aria-label={`Remove ${item.raw_name}`}
                      className="text-on-surface-variant hover:text-error transition-colors shrink-0"
                    >
                      <Trash2 size={18} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>
      <MobileBottomNav />
    </div>
  );
}
