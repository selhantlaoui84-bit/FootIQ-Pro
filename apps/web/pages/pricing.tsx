import { useEffect, useMemo, useState } from 'react';
import { createCheckoutSession, getBillingStatus } from '~/lib/api';
import { useAuth } from '~/lib/auth';
import type { BillingStatusResponse } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

const plans = [
  {
    id: 'free',
    name: 'Free',
    price: '0 €',
    features: ['5 prédictions / jour', 'Aperçu dashboard', 'Suivi de paris limité'],
  },
  {
    id: 'premium',
    name: 'Premium',
    price: '19 € / mois',
    features: ['Prédictions complètes', 'Cotes réelles si disponibles', 'Value bets', 'Assistant FootIQ', 'Suivi des paris'],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '49 € / mois',
    features: ['Tout Premium', 'Analyses avancées', 'Backtesting détaillé', 'Fiabilité marchés/compétitions', 'Historique étendu'],
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 'Sur devis',
    features: ['Multi-utilisateur', 'Exports', 'Support prioritaire', 'Limites sur mesure'],
  },
] as const;

export default function PricingPage() {
  const [billing, setBilling] = useState<BillingStatusResponse | null>(null);
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, session } = useAuth();

  useEffect(() => {
    getBillingStatus().then(setBilling).catch(() => setBilling({ status: 'error', billing_configured: false, plans: ['free', 'premium', 'pro'] }));
  }, []);

  const billingReady = Boolean(billing?.billing_configured);
  const title = useMemo(() => (billingReady ? 'Choisissez votre plan' : 'Paiement bientôt disponible'), [billingReady]);

  async function handleUpgrade(plan: 'premium' | 'pro' | 'enterprise') {
    if (!isAuthenticated || !session?.access_token) {
      window.location.href = '/login?next=/pricing';
      return;
    }
    setLoadingPlan(plan);
    setError(null);
    try {
      const response = await createCheckoutSession(plan, 'monthly', session.access_token);
      if (response.status === 'ok' && response.checkout_url) {
        window.location.href = response.checkout_url;
        return;
      }
      setError(response.detail ?? 'Paiement non configuré.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Ouverture du paiement impossible.');
    } finally {
      setLoadingPlan(null);
    }
  }

  return (
    <Layout>
      <section className="pageHeader premiumPageIntro">
        <p className="eyebrow">SaaS</p>
        <h1>Pricing</h1>
        <p>{title}. Les cotes réelles, les value bets et les analyses restent encadrés par le niveau de risque.</p>
      </section>

      {error && <section className="banner warning">{error}</section>}

      <section className="cardsGrid">
        {plans.map((plan) => (
          <article className="card premiumPanel" key={plan.id}>
            <p className="eyebrow">{plan.name}</p>
            <h2>{plan.price}</h2>
            <ul>
              {plan.features.map((feature) => (
                <li key={feature}>{feature}</li>
              ))}
            </ul>
            {plan.id === 'free' ? (
              <button className="button secondary" type="button" disabled>
                Plan actuel possible
              </button>
            ) : billingReady ? (
              <button className="button primary" type="button" onClick={() => handleUpgrade(plan.id)} disabled={loadingPlan === plan.id}>
                {loadingPlan === plan.id ? 'Ouverture...' : `Passer ${plan.name}`}
              </button>
            ) : (
              <button className="button secondary" type="button" disabled>
                Bientôt disponible
              </button>
            )}
          </article>
        ))}
      </section>
    </Layout>
  );
}
