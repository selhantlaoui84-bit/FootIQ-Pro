import Link from 'next/link';
import { useRouter } from 'next/router';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { useAuth } from '~/lib/auth';
import { Layout } from '~/src-layout';

export default function ProfilePage() {
  const router = useRouter();
  const { user, isAdmin, adminEmail, signOut } = useAuth();

  async function handleSignOut() {
    await signOut();
    void router.push('/');
  }

  return (
    <ProtectedRoute>
      <Layout>
        <section className="pageHeader">
          <p className="eyebrow">Compte</p>
          <h1>Profil</h1>
          <p>Votre espace utilisateur FootIQ Pro, prêt pour les futures options SaaS.</p>
        </section>

        <section className="sectionSplit">
          <article className="card">
            <h2>Compte</h2>
            <div className="dataList">
              <span>
                Email <strong>{user?.email ?? 'N/A'}</strong>
              </span>
              <span>
                Rôle <strong>{isAdmin ? 'Admin' : 'Utilisateur'}</strong>
              </span>
              <span>
                Statut <strong>Actif</strong>
              </span>
              <span>
                Offre <strong>Free</strong>
              </span>
              <span>
                Upgrade <strong>Prévu plus tard</strong>
              </span>
            </div>
            <button className="button secondary logoutWide" onClick={handleSignOut} type="button">
              Déconnexion
            </button>
          </article>

          <article className="card accent">
            <h2>Accès rapides</h2>
            <div className="quickActions">
              <Link className="button secondary" href="/dashboard">
                Tableau de bord
              </Link>
              <Link className="button secondary" href="/matches">
                Matchs
              </Link>
              <Link className="button secondary" href="/predictions">
                Prédictions
              </Link>
              {isAdmin ? (
                <Link className="button primary" href="/admin">
                  Admin
                </Link>
              ) : (
                <span className="banner warning">L'accès admin est limité à {adminEmail}.</span>
              )}
            </div>
          </article>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}

