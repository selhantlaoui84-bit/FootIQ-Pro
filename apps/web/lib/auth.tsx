import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { authConfigured, supabase } from '~/lib/supabase';

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  loading: boolean;
  authConfigured: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  adminEmail: string;
  signIn: (email: string, password: string) => Promise<{ error?: string }>;
  signUp: (email: string, password: string) => Promise<{ error?: string; confirmationRequired?: boolean }>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const DEFAULT_ADMIN_EMAIL = 'samir.elh@outlook.fr';

function getAdminEmail() {
  return (process.env.NEXT_PUBLIC_ADMIN_EMAIL || DEFAULT_ADMIN_EMAIL).trim().toLowerCase();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(authConfigured);
  const user = session?.user ?? null;
  const adminEmail = getAdminEmail();
  const isAuthenticated = Boolean(user);
  const isAdmin = user?.email?.toLowerCase() === adminEmail;

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }

    let mounted = true;

    supabase.auth
      .getSession()
      .then(({ data }) => {
        if (mounted) {
          setSession(data.session);
        }
      })
      .catch(() => {
        if (mounted) {
          setSession(null);
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false);
        }
      });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setLoading(false);
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      session,
      loading,
      authConfigured,
      isAuthenticated,
      isAdmin,
      adminEmail,
      async signIn(email: string, password: string) {
        if (!supabase) {
          return { error: 'Supabase auth is not configured.' };
        }

        const { error } = await supabase.auth.signInWithPassword({ email, password });

        return error ? { error: error.message } : {};
      },
      async signUp(email: string, password: string) {
        if (!supabase) {
          return { error: 'Supabase auth is not configured.' };
        }

        const { data, error } = await supabase.auth.signUp({ email, password });

        if (error) {
          return { error: error.message };
        }

        return { confirmationRequired: Boolean(data.user && !data.session) };
      },
      async signOut() {
        if (!supabase) {
          setSession(null);
          return;
        }

        await supabase.auth.signOut();
        setSession(null);
      },
    }),
    [adminEmail, isAdmin, isAuthenticated, loading, session, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }

  return context;
}
