import Link from 'next/link';
import { Layout } from '~/src-layout';

export default function BillingSuccessPage() {
  return (
    <Layout>
      <section className="pageHeader premiumPageIntro">
        <p className="eyebrow">Billing</p>
        <h1>Paiement reçu par Stripe</h1>
        <p>L'activation définitive de l'abonnement dépend du webhook Stripe. Si l'accès n'est pas encore visible, patientez quelques instants puis revenez sur votre profil.</p>
        <div className="quickActions">
          <Link className="button primary" href="/profile">Voir mon abonnement</Link>
          <Link className="button secondary" href="/dashboard">Retour dashboard</Link>
        </div>
      </section>
    </Layout>
  );
}
