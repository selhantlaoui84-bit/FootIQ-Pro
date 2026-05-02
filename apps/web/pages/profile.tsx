import Link from 'next/link';
import { useRouter } from 'next/router';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { useAuth } from '~/lib/auth';
import { Layout } from '~/src-layout';

export default function ProfilePage() {
  const router = useRouter();
  const { user, signOut } = useAuth();

  async function handleSignOut() {
    await signOut();
    void router.push('/');
  }

  return (
    <ProtectedRoute>
      <Layout>
        <section className="pageHeader">
          <p className="eyebrow">Compte</p>
          <h1>Profile</h1>
          <p>Ton espace utilisateur FootIQ Pro, prêt pour les futures options SaaS.</p>
        </section>

        <section className="sectionSplit">
          <article className="card">
            <h2>Account</h2>
            <div className="dataList">
              <span>
                Email <strong>{user?.email ?? 'N/A'}</strong>
              </span>
              <span>
                Status <strong>Active</strong>
              </span>
              <span>
                Plan <strong>Free</strong>
              </span>
              <span>
                Upgrade <strong>Coming later</strong>
              </span>
            </div>
            <button className="button secondary logoutWide" onClick={handleSignOut} type="button">
              Sign out
            </button>
          </article>

          <article className="card accent">
            <h2>Quick access</h2>
            <div className="quickActions">
              <Link className="button secondary" href="/dashboard">
                Dashboard
              </Link>
              <Link className="button secondary" href="/matches">
                Matches
              </Link>
              <Link className="button secondary" href="/predictions">
                Predictions
              </Link>
              <Link className="button primary" href="/admin">
                Admin
              </Link>
            </div>
          </article>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}
