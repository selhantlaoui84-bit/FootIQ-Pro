import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { MiniLineChart } from '~/components/ui';
import { createPortalSession, getMySubscription } from '~/lib/api';
import { useAuth } from '~/lib/auth';
import type { SubscriptionResponse } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

export default function ProfilePage() {
  const router = useRouter();
  const { user, isAdmin, isSuperAdmin, role, signOut } = useAuth();
  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null);
  const [billingMessage, setBillingMessage] = useState<string | null>(null);

  useEffect(() => {
    getMySubscription().then(setSubscription).catch(() => setSubscription(null));
  }, []);

  async function handleSignOut() {
    await signOut();
    void router.push('/');
  }

  async function handlePortal() {
    setBillingMessage(null);
    try {
      const response = await createPortalSession();
      if (response.status === 'ok' && response.portal_url) {
        window.location.href = response.portal_url;
        return;
      }
      setBillingMessage(response.detail ?? 'Gestion abonnement indisponible.');
    } catch (error) {
      setBillingMessage(error instanceof Error ? error.message : 'Gestion abonnement indisponible.');
    }
  }

  const plan = subscription?.plan ?? (isAdmin ? 'admin' : 'free');
  const limits = subscription?.limits ?? {};

  return (
    <ProtectedRoute>
      <Layout>
        <section className="pageHeader premiumPageIntro">
          <p className="eyebrow">Compte</p>
          <h1>Profil</h1>
          <p>Votre espace utilisateur FootIQ Pro, portefeuille et préférences de suivi.</p>
        </section>

        <section className="sectionSplit premiumSectionSplit">
          <article className="card">
            <h2>Compte</h2>
            <div className="dataList">
              <span>Email <strong>{user?.email ?? 'N/A'}</strong></span>
              <span>Rôle <strong>{role}</strong></span>
              <span>Statut <strong>Actif</strong></span>
              <span>Offre <strong>{plan}</strong></span>
              <span>Upgrade <strong>{plan === 'free' ? 'Disponible' : 'Actif'}</strong></span>
            </div>
            <button className="button secondary logoutWide" onClick={handleSignOut} type="button">
              Déconnexion
            </button>
          </article>

          <article className="card">
            <h2>Abonnement</h2>
            <div className="dataList">
              <span>Plan actuel <strong>{plan}</strong></span>
              <span>Statut <strong>{subscription?.subscription_status ?? 'free'}</strong></span>
              <span>Période en cours <strong>{subscription?.current_period_end ?? 'Non applicable'}</strong></span>
              <span>Renouvellement <strong>{subscription?.cancel_at_period_end ? 'Annulation prévue' : 'Actif ou gratuit'}</strong></span>
              <span>Prédictions utilisées <strong>{formatLimit(limits.prediction_view)}</strong></span>
              <span>Assistant utilisé <strong>{formatLimit(limits.assistant_request)}</strong></span>
            </div>
            {billingMessage && <p className="banner warning">{billingMessage}</p>}
            <div className="quickActions">
              <Link className="button primary" href="/pricing">Upgrade</Link>
              <button className="button secondary" type="button" onClick={handlePortal}>
                Gérer l'abonnement
              </button>
            </div>
          </article>

          <article className="card accent">
            <MiniLineChart />
            <h2>Accès rapides</h2>
            <div className="quickActions">
              <Link className="button secondary" href="/dashboard">Tableau de bord</Link>
              <Link className="button secondary" href="/matches">Matchs</Link>
              <Link className="button secondary" href="/predictions">Prédictions</Link>
              <Link className="button secondary" href="/pricing">Pricing</Link>
              {isAdmin ? (
                <Link className="button primary" href="/admin">Admin</Link>
              ) : (
                <span className="banner warning">Accès admin réservé aux rôles autorisés.</span>
              )}
              {isSuperAdmin && <Link className="button primary" href="/super-admin">Super Admin</Link>}
            </div>
          </article>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}

function formatLimit(limit?: { used: number; limit: number | null; remaining: number | null }) {
  if (!limit) return 'Données insuffisantes';
  if (limit.limit == null) return `${limit.used} / illimité`;
  return `${limit.used} / ${limit.limit}`;
}
