import Link from 'next/link';
import { useRouter } from 'next/router';
import { FormEvent, useEffect, useState } from 'react';
import { useAuth } from '~/lib/auth';
import { Layout } from '~/src-layout';

export default function RegisterPage() {
  const router = useRouter();
  const { signUp, authConfigured, isAuthenticated, loading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && isAuthenticated) {
      void router.replace('/dashboard');
    }
  }, [isAuthenticated, loading, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError(null);
    setSuccess(null);

    const result = await signUp(email, password);

    setIsSubmitting(false);

    if (result.error) {
      setError(result.error);
      return;
    }

    setSuccess(
      result.confirmationRequired
        ? 'Compte créé. Vérifie ton email pour confirmer ton inscription.'
        : 'Compte créé. Tu peux maintenant te connecter.',
    );
  }

  return (
    <Layout>
      <section className="authShell">
        <form className="authCard" onSubmit={handleSubmit}>
          <p className="eyebrow">FootIQ Pro</p>
          <h1>Créer un compte</h1>
          <p>Créez un accès pour suivre les analyses, piloter les actualisations et préparer les futures options SaaS.</p>

          {!authConfigured && (
            <div className="banner warning">
              Supabase Auth n'est pas configuré. Ajoutez NEXT_PUBLIC_SUPABASE_URL et NEXT_PUBLIC_SUPABASE_ANON_KEY.
            </div>
          )}
          {error && <div className="banner error">{error}</div>}
          {success && <div className="banner success">{success}</div>}

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
              autoComplete="new-password"
              disabled={!authConfigured || isSubmitting}
              minLength={6}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          <button className="button primary" disabled={!authConfigured || isSubmitting} type="submit">
            {isSubmitting ? 'Création...' : 'Créer le compte'}
          </button>
          <p>
            Déjà inscrit ?{' '}
            <Link className="textLink" href="/login">
              Connexion
            </Link>
          </p>
        </form>
      </section>
    </Layout>
  );
}

