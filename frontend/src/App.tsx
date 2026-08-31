import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ProtectedRoute } from './components/ProtectedRoute';
import { VerifyEmailBanner } from './components/VerifyEmailBanner';
import { AuthProvider } from './lib/auth';
import BookmarksPage from './pages/BookmarksPage';
import CollectionDetailPage from './pages/CollectionDetailPage';
import DiscoveryPage from './pages/DiscoveryPage';
import ExplorePage from './pages/ExplorePage';
import KitchenModePage from './pages/KitchenModePage';
import LoginPage from './pages/LoginPage';
import PantryAddPage from './pages/PantryAddPage';
import PantryPage from './pages/PantryPage';
import PantryRemovePage from './pages/PantryRemovePage';
import ProfilePage from './pages/ProfilePage';
import RecipeDetailPage from './pages/RecipeDetailPage';
import RegisterPage from './pages/RegisterPage';
import ShoppingListPage from './pages/ShoppingListPage';
import UseItUpPage from './pages/UseItUpPage';
import VerifyEmailPage from './pages/VerifyEmailPage';

export function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <VerifyEmailBanner />
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />

          <Route path="/" element={<ProtectedRoute><DiscoveryPage /></ProtectedRoute>} />
          <Route path="/explore" element={<ProtectedRoute><ExplorePage /></ProtectedRoute>} />
          <Route path="/recipe/:id" element={<ProtectedRoute><RecipeDetailPage /></ProtectedRoute>} />
          <Route path="/recipe/:id/cook" element={<ProtectedRoute><KitchenModePage /></ProtectedRoute>} />
          <Route path="/use-it-up" element={<ProtectedRoute><UseItUpPage /></ProtectedRoute>} />
          <Route path="/pantry" element={<ProtectedRoute><PantryPage /></ProtectedRoute>} />
          <Route path="/pantry-add" element={<ProtectedRoute><PantryAddPage /></ProtectedRoute>} />
          <Route path="/pantry-remove/:id" element={<ProtectedRoute><PantryRemovePage /></ProtectedRoute>} />
          <Route path="/bookmarks" element={<ProtectedRoute><BookmarksPage /></ProtectedRoute>} />
          <Route path="/bookmarks/:collectionId" element={<ProtectedRoute><CollectionDetailPage /></ProtectedRoute>} />
          <Route path="/bookmarks/shopping-lists/:listId" element={<ProtectedRoute><ShoppingListPage /></ProtectedRoute>} />
          <Route path="/profile" element={<ProtectedRoute><ProfilePage /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}