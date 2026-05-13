import { Card, PageHeader, StatusBanner } from '~/components/ui';
import { Layout } from '~/src-layout';

export default function AboutPage() {
  return (
    <Layout>
      <PageHeader eyebrow="Positionnement" title="Analyse probabiliste responsable">
        <p>
          FootIQ Pro aide les fans, analystes, journalistes et créateurs de contenu à comprendre les matchs avec des
          probabilités, pas avec des promesses. La plateforme combine lecture football, discipline de risque et
          supervision IA.
        </p>
      </PageHeader>

      <section className="grid three">
        <Card tone="premium">
          <h2>Lire les matchs</h2>
          <p>Identifier les rencontres où les signaux statistiques convergent clairement.</p>
        </Card>
        <Card tone="warning">
          <h2>Repérer les pièges</h2>
          <p>Détecter les favoris apparents fragilisés par des signaux contradictoires.</p>
        </Card>
        <Card tone="info">
          <h2>Expliquer simplement</h2>
          <p>Présenter les risques, les probabilités et la confiance dans un langage clair.</p>
        </Card>
      </section>

      <StatusBanner tone="premium">
        FootIQ Pro est un outil d'analyse statistique. Aucune prédiction n'assure un résultat, les paris comportent un risque de perte et l'utilisateur reste responsable de ses décisions.
      </StatusBanner>
    </Layout>
  );
}
