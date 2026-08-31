import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { ApiError, authApi, getToken, setToken } from './api';
import type { UserOut } from './types';

interface AuthContextValue {
  user: UserOut | null;
  /** true while we're checking an existing token on first load */
  initializing: boolean;
  /** set once login() completes for a token whose user turns out not to be
   * an admin, so the login screen can show a clear reason instead of just
   * silently refusing. */
  lastError: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [initializing, setInitializing] = useState(true);
  const [lastError, setLastError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setInitializing(false);
      return;
    }
    authApi
      .me()
      .then((u) => {
        // The backend already blocks non-admins from every /api/admin/*
        // call via require_admin -- this is a client-side mirror of that
        // check so a non-admin never even sees the shell of the panel.
        if (u.role !== 'admin') {
          setToken(null);
          setUser(null);
          return;
        }
        setUser(u);
      })
      .catch(() => {
        // Expired/invalid token -- request() already cleared it.
        setUser(null);
      })
      .finally(() => setInitializing(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setLastError(null);
    const res = await authApi.login(email, password);
    if (res.user.role !== 'admin') {
      // Don't keep the token around for a valid-but-non-admin account.
      setLastError('This account does not have admin access.');
      throw new ApiError(403, 'This account does not have admin access.');
    }
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, initializing, lastError, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}
