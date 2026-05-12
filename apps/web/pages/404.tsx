import Link from 'next/link';
import { Card, PageHeader } from '~/components/ui';
import { Layout } from '~/src-layout';

export default function NotFoundPage() {
  return (
    <Layout>
      <PageHeader eyebrow="Erreur 404" title="Page introuvable">
        <p>
          La page demandée n'existe pas ou n'est plus disponible. Les routes FootIQ Pro restent accessibles depuis la
          navigation principale.
        </p>
      </PageHeader>

      <section className="sectionSplit">
        <Card tone="premium">
          <h2>Retour au centre de contrôle</h2>
          <p>Reprenez l'analyse depuis le tableau de bord, les matchs ou les prédictions.</p>
          <div className="quickActions">
            <Link className="button primary" href="/dashboard">
              Tableau de bord
            </Link>
            <Link className="button secondary" href="/matches">
              Matchs
            </Link>
          </div>
        </Card>
        <Card tone="info">
          <h2>Analyse responsable</h2>
          <p>FootIQ Pro fournit des signaux probabilistes. Les résultats restent incertains.</p>
        </Card>
      </section>
    </Layout>
  );
}
