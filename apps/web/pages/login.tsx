import Link from 'next/link';
import { useRouter } from 'next/router';
import { FormEvent, useEffect, useState } from 'react';
import { useAuth } from '~/lib/auth';
import { Layout } from '~/src-layout';

export default function LoginPage() {
  const router = useRouter();
  const { signIn, authConfigured, isAuthenticated, loading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && isAuthenticated) {
      const next = typeof router.query.next === 'string' ? router.query.next : '/dashboard';
      void router.replace(next);
    }
  }, [isAuthenticated, loading, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);

    const result = await signIn(email, password);

    setIsSubmitting(false);

    if (result.error) {
      setError(result.error);
      return;
    }

    const next = typeof router.query.next === 'string' ? router.query.next : '/dashboard';
    void router.push(next);
  }

  return (
    <Layout>
      <section className="authShell">
        <form className="authCard" onSubmit={handleSubmit}>
          <p className="eyebrow">Espace SaaS</p>
          <h1>Connexion</h1>
          <p>Connectez-vous pour accéder au tableau de bord, au profil et aux outils admin.</p>

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
              disabled={!authConfigured || isSubmitting}
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
              disabled={!authConfigured || isSubmitting}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          <button className="button primary" disabled={!authConfigured || isSubmitting} type="submit">
            {isSubmitting ? 'Connexion...' : 'Se connecter'}
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

