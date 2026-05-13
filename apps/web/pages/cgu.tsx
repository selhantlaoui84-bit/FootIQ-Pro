import { Card, PageHeader, StatusBanner } from '~/components/ui';
import { Layout } from '~/src-layout';

export default function CguPage() {
  return (
    <Layout>
      <PageHeader eyebrow="Cadre légal" title="Conditions générales d'utilisation">
        <p>FootIQ Pro est un outil d'aide à l'analyse football. Les résultats restent incertains et l'application ne constitue pas une incitation au jeu.</p>
      </PageHeader>

      <section className="grid two">
        <Card>
          <h2>Utilisation du service</h2>
          <p>Les informations affichées sont fournies à titre analytique. L'utilisateur reste seul responsable de ses décisions.</p>
        </Card>
        <Card>
          <h2>Jeu responsable</h2>
          <p>Ne misez jamais une somme que vous ne pouvez pas vous permettre de perdre. Les paris comportent un risque de perte.</p>
        </Card>
      </section>

      <StatusBanner tone="warning">Aucune prédiction FootIQ Pro n'assure un résultat.</StatusBanner>
    </Layout>
  );
}
