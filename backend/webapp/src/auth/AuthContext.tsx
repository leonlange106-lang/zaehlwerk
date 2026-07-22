import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, apiPost, setUnauthorizedHandler } from '../api/client';
import type { AuthStatus, RoleInfo, User } from '../api/types';

interface AuthContextValue {
  status: AuthStatus | null;
  user: User | null;
  isAdmin: boolean;
  roles: RoleInfo[];
  checked: boolean;
  onboardingNeeded: boolean;
  can: (perm: string) => boolean;
  refresh: () => Promise<AuthStatus | null>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [checked, setChecked] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const s = await api<AuthStatus>('/api/auth/status');
      setStatus(s);
      setChecked(true);
      return s;
    } catch {
      const fallback: AuthStatus = {
        mode: 'lokal', authenticated: false, setup_required: false,
        recovery: false, user: null,
      };
      setStatus(fallback);
      setChecked(true);
      return fallback;
    }
  }, []);

  const logout = useCallback(async () => {
    try { await apiPost('/api/auth/logout'); } catch { /* egal */ }
    await refresh();
  }, [refresh]);

  useEffect(() => {
    // Bei 401 irgendwo in der App: Status neu prüfen -> Anmeldemaske.
    setUnauthorizedHandler(() => { void refresh(); });
    void refresh();
  }, [refresh]);

  const value = useMemo<AuthContextValue>(() => {
    const user = status?.user ?? null;
    return {
      status,
      user,
      isAdmin: !!(status?.permissions?.admin || user?.is_admin),
      roles: status?.roles ?? [],
      checked,
      onboardingNeeded: !!(user && user.is_first_login),
      can: (perm: string) => !!status?.permissions?.[perm],
      refresh,
      logout,
    };
  }, [status, checked, refresh, logout]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth muss innerhalb von AuthProvider verwendet werden');
  return ctx;
}
