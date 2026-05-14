import Link from 'next/link';
import { Layout } from '~/src-layout';

export default function BillingCancelPage() {
  return (
    <Layout>
      <section className="pageHeader premiumPageIntro">
        <p className="eyebrow">Billing</p>
        <h1>Paiement annulé</h1>
        <p>Aucun abonnement n'a été activé. Vous pouvez reprendre le choix d'un plan quand vous le souhaitez.</p>
        <div className="quickActions">
          <Link className="button primary" href="/pricing">Voir les tarifs</Link>
          <Link className="button secondary" href="/dashboard">Retour dashboard</Link>
        </div>
      </section>
    </Layout>
  );
}
