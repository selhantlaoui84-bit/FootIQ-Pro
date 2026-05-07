import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Session, User } from '@supabase/supabase-js';
import { authConfigured, supabase } from '~/lib/supabase';

type AuthContextValue = {
  user: User | null;
  session: Session | null;
  isLoading: boolean;
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

function getAdminEmails() {
  return (process.env.NEXT_PUBLIC_ADMIN_EMAIL || DEFAULT_ADMIN_EMAIL)
    .split(',')
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(authConfigured);
  const user = session?.user ?? null;
  const adminEmails = useMemo(() => getAdminEmails(), []);
  const adminEmail = adminEmails[0] ?? DEFAULT_ADMIN_EMAIL;
  const isAuthenticated = Boolean(user);
  const isAdmin = user?.email ? adminEmails.includes(user.email.trim().toLowerCase()) : false;

  useEffect(() => {
    if (!supabase) {
      setIsLoading(false);
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
          setIsLoading(false);
        }
      });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      if (!mounted) return;
      setSession(nextSession);
      setIsLoading(false);
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
      isLoading,
      loading: isLoading,
      authConfigured,
      isAuthenticated,
      isAdmin,
      adminEmail,
      async signIn(email: string, password: string) {
        if (!supabase) {
          return { error: 'Supabase auth is not configured.' };
        }

        const { data, error } = await supabase.auth.signInWithPassword({ email, password });

        if (error) {
          return { error: error.message };
        }

        setSession(data.session);
        setIsLoading(false);
        return {};
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
    [adminEmail, isAdmin, isAuthenticated, isLoading, session, user],
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
