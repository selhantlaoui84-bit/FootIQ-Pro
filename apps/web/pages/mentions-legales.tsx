import { Card, PageHeader, StatusBanner } from '~/components/ui';
import { Layout } from '~/src-layout';

export default function MentionsLegalesPage() {
  return (
    <Layout>
      <PageHeader eyebrow="Informations légales" title="Mentions légales">
        <p>FootIQ Pro est une plateforme d'analyse football destinée à l'aide à la décision statistique.</p>
      </PageHeader>

      <section className="grid two">
        <Card>
          <h2>Éditeur</h2>
          <p>À compléter par le responsable légal avant publication définitive.</p>
        </Card>
        <Card>
          <h2>Hébergement</h2>
          <p>À compléter par le responsable légal avant publication définitive.</p>
        </Card>
      </section>

      <StatusBanner tone="warning">
        FootIQ Pro est un outil d'analyse statistique. Aucune prédiction n'assure un résultat, les paris comportent un risque de perte et l'utilisateur reste responsable de ses décisions.
      </StatusBanner>
    </Layout>
  );
}
