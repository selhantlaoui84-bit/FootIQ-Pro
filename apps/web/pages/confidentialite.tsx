import { Card, PageHeader, StatusBanner } from '~/components/ui';
import { Layout } from '~/src-layout';

export default function ConfidentialitePage() {
  return (
    <Layout>
      <PageHeader eyebrow="Confidentialité" title="Politique de confidentialité">
        <p>Cette page résume les principes de protection des données appliqués par FootIQ Pro.</p>
      </PageHeader>

      <section className="grid two">
        <Card>
          <h2>Données traitées</h2>
          <p>FootIQ Pro peut traiter des données de compte, des préférences utilisateur et des informations techniques nécessaires au fonctionnement du service.</p>
        </Card>
        <Card>
          <h2>Sécurité</h2>
          <p>Les routes sensibles passent par des proxys serveur. Les clés d'administration, Stripe et cotes restent côté serveur.</p>
        </Card>
      </section>

      <StatusBanner tone="info">À compléter par le responsable légal avant publication définitive.</StatusBanner>
    </Layout>
  );
}
