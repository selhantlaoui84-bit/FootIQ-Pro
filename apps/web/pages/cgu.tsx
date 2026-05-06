import { Layout } from '~/src-layout';

export default function CguPage() {
  return (
    <Layout>
      <section className="pageHeader">
        <p className="eyebrow">Cadre légal</p>
        <h1>Conditions générales d'utilisation</h1>
        <p>FootIQ Pro est un outil d'aide à l'analyse football. Il ne garantit aucun résultat et ne constitue pas une incitation au jeu.</p>
      </section>

      <section className="card">
        <h2>Utilisation du service</h2>
        <p>Les informations affichées sont fournies à titre analytique. L'utilisateur reste seul responsable de ses décisions.</p>
        <p>Les prédictions, scores de confiance, indicateurs de risque, backtests et alertes modèle doivent être interprétés avec prudence.</p>
      </section>

      <section className="card">
        <h2>Jeu responsable</h2>
        <p>FootIQ Pro ne pousse pas au jeu excessif. Ne misez jamais une somme que vous ne pouvez pas vous permettre de perdre.</p>
      </section>
    </Layout>
  );
}
