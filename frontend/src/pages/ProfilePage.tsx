import { Check, Heart, Lock, LogOut, User as UserIcon, Utensils } from 'lucide-react';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { MainHeader } from '../components/MainHeader';
import { MobileBottomNav } from '../components/MobileBottomNav';
import { RecipeCard } from '../components/RecipeCard';
import { InlineError } from '../components/StatusBlocks';
import { ApiError, favoritesApi, profileApi, tagsApi } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { EquipmentTagOut, FavoriteOut, ProfileStatsOut } from '../lib/types';

const DIET_OPTIONS = ['Vegetarian', 'Vegan', 'Gluten-Free', 'Dairy-Free', 'Pescatarian', 'Halal'];

export default function ProfilePage() {
  const { user, logout, refreshUser } = useAuth();
  const navigate = useNavigate();

  const [selectedDiet, setSelectedDiet] = useState<string[]>(user?.dietary_preferences || []);
  const [selectedEquipment, setSelectedEquipment] = useState<string[]>(user?.kitchen_equipment || []);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  const [stats, setStats] = useState<ProfileStatsOut | null>(null);
  const [equipmentOptions, setEquipmentOptions] = useState<EquipmentTagOut[]>([]);

  const [favorites, setFavorites] = useState<FavoriteOut[]>([]);
  const [favoritesLoading, setFavoritesLoading] = useState(true);

  const [showPasswordForm, setShowPasswordForm] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);

  useEffect(() => {
    setSelectedDiet(user?.dietary_preferences || []);
    setSelectedEquipment(user?.kitchen_equipment || []);
  }, [user]);

  useEffect(() => {
    profileApi.stats().then(setStats).catch(() => setStats(null));
    tagsApi.equipment().then(setEquipmentOptions).catch(() => setEquipmentOptions([]));
    setFavoritesLoading(true);
    favoritesApi
      .list()
      .then(setFavorites)
      .catch(() => setFavorites([]))
      .finally(() => setFavoritesLoading(false));
  }, []);

  const dirty = user
    ? !sameSet(selectedDiet, user.dietary_preferences) || !sameSet(selectedEquipment, user.kitchen_equipment)
    : false;

  function toggleDiet(diet: string) {
    setSaved(false);
    setSelectedDiet((prev) => (prev.includes(diet) ? prev.filter((d) => d !== diet) : [...prev, diet]));
  }

  function toggleEquipment(item: string) {
    setSaved(false);
    setSelectedEquipment((prev) => (prev.includes(item) ? prev.filter((d) => d !== item) : [...prev, item]));
  }

  async function save() {
    setError(null);
    setSaving(true);
    try {
      await profileApi.update({ dietary_preferences: selectedDiet, kitchen_equipment: selectedEquipment });
      await refreshUser();
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not save your preferences.');
    } finally {
      setSaving(false);
    }
  }

  async function removeFavorite(recipeId: string) {
    setFavorites((prev) => prev.filter((f) => f.recipe.id !== recipeId)); // optimistic
    try {
      await favoritesApi.remove(recipeId);
    } catch {
      favoritesApi.list().then(setFavorites).catch(() => {});
    }
  }

  async function submitPasswordChange(e: React.FormEvent) {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSaved(false);
    setPasswordSaving(true);
    try {
      await profileApi.changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setPasswordSaved(true);
    } catch (err) {
      setPasswordError(err instanceof ApiError ? err.message : 'Could not change your password.');
    } finally {
      setPasswordSaving(false);
    }
  }

  function handleLogout() {
    logout();
    navigate('/login', { replace: true });
  }

  if (!user) return null;

  return (
    <div className="bg-surface min-h-screen">
      <MainHeader />
      <main className="pt-32 pb-24 max-w-3xl mx-auto px-5 md:px-8">
        <div className="mb-10">
          <h1 className="font-display text-3xl md:text-5xl text-on-surface">Profile</h1>
          <p className="font-body-md text-on-surface-variant mt-1">Manage your account and dietary preferences.</p>
        </div>

        <section className="bg-surface-container-lowest rounded-[36px] p-8 shadow-sm border border-outline-variant/10 mb-8">
          <div className="flex items-center gap-4 mb-8">
            <div className="w-16 h-16 rounded-full bg-primary flex items-center justify-center text-on-primary shrink-0">
              <UserIcon size={26} />
            </div>
            <div>
              <p className="font-heading text-lg text-on-surface">{user.full_name || 'No name set'}</p>
              <p className="font-body-md text-sm text-on-surface-variant">{user.email}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="font-ui text-[10px] uppercase tracking-widest text-on-surface-variant">Member since</p>
              <p className="font-body-md text-on-surface">{new Date(user.created_at).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })}</p>
            </div>
            <div>
              <p className="font-ui text-[10px] uppercase tracking-widest text-on-surface-variant">Account type</p>
              <p className="font-body-md text-on-surface capitalize">{user.role}</p>
            </div>
            <div>
              <p className="font-ui text-[10px] uppercase tracking-widest text-on-surface-variant">Favorites</p>
              <p className="font-body-md text-on-surface">{stats ? stats.favorites_count : '—'}</p>
            </div>
            <div>
              <p className="font-ui text-[10px] uppercase tracking-widest text-on-surface-variant">Pantry items</p>
              <p className="font-body-md text-on-surface">{stats ? stats.pantry_item_count : '—'}</p>
            </div>
          </div>
        </section>

        <section className="bg-surface-container-lowest rounded-[36px] p-8 shadow-sm border border-outline-variant/10 mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="font-heading text-xl flex items-center gap-2">
              <Heart size={18} className="text-primary" /> Your Favorites
            </h2>
            {favorites.length > 0 && (
              <button onClick={() => navigate('/explore')} className="text-primary font-ui text-xs font-medium">
                Find more
              </button>
            )}
          </div>
          {favoritesLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {[0, 1].map((i) => <div key={i} className="h-24 rounded-2xl bg-surface-container animate-pulse" />)}
            </div>
          ) : favorites.length === 0 ? (
            <div className="text-center py-8">
              <p className="font-body-md text-sm text-on-surface-variant mb-3">
                No favorites yet — tap the heart on any recipe to save it here.
              </p>
              <button
                onClick={() => navigate('/explore')}
                className="text-primary font-ui text-sm font-semibold"
              >
                Browse recipes
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {favorites.map((fav) => (
                <div key={fav.id} className="relative">
                  <RecipeCard
                    recipe={{
                      id: fav.recipe.id,
                      name_en: fav.recipe.name_en,
                      cuisine: fav.recipe.cuisine || 'Unknown',
                      course: fav.recipe.course,
                      image_url: fav.recipe.image_url,
                      servings: fav.recipe.servings,
                      total_time_min: fav.recipe.total_time_min,
                    }}
                  />
                  <button
                    onClick={() => removeFavorite(fav.recipe.id)}
                    aria-label="Remove from favorites"
                    className="absolute top-4 right-4 w-8 h-8 rounded-full bg-black/50 backdrop-blur-md text-white flex items-center justify-center"
                  >
                    <Heart size={14} fill="currentColor" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="bg-surface-container-lowest rounded-[36px] p-8 shadow-sm border border-outline-variant/10 mb-8">
          <h2 className="font-heading text-xl mb-6">Dietary Preferences</h2>
          {error && (
            <div className="mb-4">
              <InlineError message={error} />
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            {DIET_OPTIONS.map((diet) => (
              <label
                key={diet}
                className={`flex items-center gap-3 p-4 rounded-2xl cursor-pointer border transition-colors ${
                  selectedDiet.includes(diet) ? 'border-primary bg-primary-container/10' : 'border-outline-variant/30 hover:bg-surface-container-low'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedDiet.includes(diet)}
                  onChange={() => toggleDiet(diet)}
                  className="w-5 h-5 rounded border-outline accent-[#904d00]"
                />
                <span className="font-body-md text-on-surface text-sm">{diet}</span>
              </label>
            ))}
          </div>

          <h2 className="font-heading text-xl mb-6 mt-8 flex items-center gap-2">
            <Utensils size={18} className="text-primary" /> Kitchen Equipment
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {equipmentOptions.map((item) => (
              <label
                key={item.id}
                className={`flex items-center gap-3 p-4 rounded-2xl cursor-pointer border transition-colors ${
                  selectedEquipment.includes(item.label) ? 'border-primary bg-primary-container/10' : 'border-outline-variant/30 hover:bg-surface-container-low'
                }`}
              >
                <input
                  type="checkbox"
                  checked={selectedEquipment.includes(item.label)}
                  onChange={() => toggleEquipment(item.label)}
                  className="w-5 h-5 rounded border-outline accent-[#904d00]"
                />
                <span className="font-body-md text-on-surface text-sm">{item.label}</span>
              </label>
            ))}
          </div>

          <div className="flex items-center gap-4 mt-6">
            <button
              onClick={save}
              disabled={!dirty || saving}
              className="flex items-center gap-2 bg-primary text-on-primary px-6 py-3 rounded-full font-ui font-semibold shadow-md disabled:opacity-50"
            >
              <Check size={16} /> {saving ? 'Saving…' : 'Save preferences'}
            </button>
            {saved && !dirty && <span className="text-sm text-tertiary font-ui">Saved</span>}
          </div>
        </section>

        <section className="bg-surface-container-lowest rounded-[36px] p-8 shadow-sm border border-outline-variant/10">
          <button
            onClick={() => setShowPasswordForm((v) => !v)}
            className="flex items-center justify-between w-full"
          >
            <h2 className="font-heading text-xl flex items-center gap-2">
              <Lock size={18} className="text-primary" /> Password
            </h2>
            <span className="text-primary font-ui text-xs font-medium">
              {showPasswordForm ? 'Cancel' : 'Change password'}
            </span>
          </button>

          {showPasswordForm && (
            <form onSubmit={submitPasswordChange} className="mt-6 space-y-4">
              {passwordError && <InlineError message={passwordError} />}
              <div>
                <label className="font-ui text-[10px] uppercase tracking-widest text-on-surface-variant block mb-1.5">
                  Current password
                </label>
                <input
                  type="password"
                  required
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full h-12 px-4 rounded-2xl bg-surface-container border border-outline-variant/30 focus:outline-none focus:ring-2 focus:ring-primary-container"
                />
              </div>
              <div>
                <label className="font-ui text-[10px] uppercase tracking-widest text-on-surface-variant block mb-1.5">
                  New password (min. 8 characters)
                </label>
                <input
                  type="password"
                  required
                  minLength={8}
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full h-12 px-4 rounded-2xl bg-surface-container border border-outline-variant/30 focus:outline-none focus:ring-2 focus:ring-primary-container"
                />
              </div>
              <div className="flex items-center gap-4">
                <button
                  type="submit"
                  disabled={passwordSaving}
                  className="flex items-center gap-2 bg-primary text-on-primary px-6 py-3 rounded-full font-ui font-semibold shadow-md disabled:opacity-50"
                >
                  <Check size={16} /> {passwordSaving ? 'Updating…' : 'Update password'}
                </button>
                {passwordSaved && <span className="text-sm text-tertiary font-ui">Password updated</span>}
              </div>
            </form>
          )}
        </section>

        <button
          onClick={handleLogout}
          className="flex items-center gap-2 text-error font-ui font-semibold mt-10 mx-auto"
        >
          <LogOut size={16} /> Log out
        </button>
      </main>
      <MobileBottomNav />
    </div>
  );
}

function sameSet(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const setB = new Set(b);
  return a.every((x) => setB.has(x));
}
