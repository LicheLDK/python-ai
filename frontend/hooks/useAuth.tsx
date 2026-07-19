"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  clearAccessToken,
  getAccessToken,
  getCurrentUser,
  setCurrentUser,
  subscribeAuth,
} from "@/lib/auth";
import * as authApi from "@/services/auth";
import { getMe } from "@/services/users";
import type { UserRead } from "@/types";

interface AuthContextValue {
  user: UserRead | null;
  loading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  refreshSession: () => Promise<boolean>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(getCurrentUser());
  const [loading, setLoading] = useState(true);

  useEffect(() => subscribeAuth(() => setUser(getCurrentUser())), []);

  const refreshSession = useCallback(async () => {
    try {
      if (!getAccessToken()) {
        await authApi.fetchCsrf();
        const data = await authApi.refresh();
        setUser(data.user);
        return true;
      }
      const me = await getMe();
      setCurrentUser(me);
      setUser(me);
      return true;
    } catch {
      clearAccessToken();
      setUser(null);
      return false;
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    const hadTokenAtMount = !!getAccessToken();
    (async () => {
      try {
        if (hadTokenAtMount) {
          const me = await getMe();
          if (!cancelled) {
            setCurrentUser(me);
            setUser(me);
          }
        } else {
          // Try cookie-based refresh (returning visitor).
          await authApi.fetchCsrf();
          const data = await authApi.refresh();
          if (!cancelled) setUser(data.user);
        }
      } catch {
        // Don't wipe a token acquired meanwhile (user logged in while
        // this recovery attempt was still in flight).
        if (!cancelled && !(!hadTokenAtMount && getAccessToken())) {
          clearAccessToken();
          setUser(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: !!user,
      isAdmin: user?.role === "admin",
      refreshSession,
      logout,
    }),
    [user, loading, refreshSession, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
