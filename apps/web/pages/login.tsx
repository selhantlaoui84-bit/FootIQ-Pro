import Link from 'next/link';
import { useRouter } from 'next/router';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { useAuth } from '~/lib/auth';
import { Layout } from '~/src-layout';

function safeNextPath(next: unknown): string {
  if (typeof next !== 'string') return '/dashboard';
  if (!next.startsWith('/') || next.startsWith('//')) return '/dashboard';
  return next;
}

export default function LoginPage() {
  const router = useRouter();
  const { signIn, authConfigured, isAuthenticated, isAdmin, loading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRedirecting, setIsRedirecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nextPath = useMemo(() => safeNextPath(router.query.next), [router.query.next]);

  useEffect(() => {
    if (!router.isReady || loading || !isAuthenticated) return;

    if (nextPath.startsWith('/admin') && !isAdmin) {
      setError("Accès admin requis pour ouvrir cette page.");
      return;
    }

    setIsRedirecting(true);
    void router.replace(nextPath);
  }, [isAdmin, isAuthenticated, loading, nextPath, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting || isRedirecting) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const result = await signIn(email.trim(), password);

      if (result.error) {
        setError(result.error);
        return;
      }

      setIsRedirecting(true);
      void router.replace(nextPath);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Connexion impossible.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Layout>
      <section className="authShell">
        <form className="authCard" onSubmit={handleSubmit}>
          <p className="eyebrow">Espace SaaS</p>
          <h1>Connexion</h1>
          <p>Connectez-vous pour accéder au tableau de bord, au profil et aux outils admin.</p>

          {loading && <div className="banner">Vérification de la session...</div>}
          {!authConfigured && (
            <div className="banner warning">
              Supabase Auth n'est pas configuré. Ajoutez NEXT_PUBLIC_SUPABASE_URL et NEXT_PUBLIC_SUPABASE_ANON_KEY.
            </div>
          )}
          {error && <div className="banner error">{error}</div>}

          <label className="field">
            Email
            <input
              autoComplete="email"
              disabled={!authConfigured || isSubmitting || isRedirecting}
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label className="field">
            Mot de passe
            <input
              autoComplete="current-password"
              disabled={!authConfigured || isSubmitting || isRedirecting}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          <button className="button primary" disabled={!authConfigured || isSubmitting || isRedirecting} type="submit">
            {isSubmitting || isRedirecting ? 'Connexion...' : 'Se connecter'}
          </button>
          <p>
            Pas encore de compte ?{' '}
            <Link className="textLink" href="/register">
              Créer un compte
            </Link>
          </p>
        </form>
      </section>
    </Layout>
  );
}
