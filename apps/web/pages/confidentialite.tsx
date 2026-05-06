import { Layout } from '~/src-layout';

export default function ConfidentialitePage() {
  return (
    <Layout>
      <section className="pageHeader">
        <p className="eyebrow">Confidentialité</p>
        <h1>Politique de confidentialité</h1>
        <p>Cette page résume les principes de protection des données appliqués par FootIQ Pro.</p>
      </section>

      <section className="card">
        <h2>Données traitées</h2>
        <p>FootIQ Pro peut traiter des données de compte, des préférences utilisateur et des informations techniques nécessaires au fonctionnement du service.</p>
        <p>Les clés d'administration et les secrets serveur ne sont jamais exposés côté navigateur.</p>
      </section>

      <section className="card">
        <h2>Sécurité</h2>
        <p>Les routes administratives passent par des proxys serveur et les actions sensibles sont protégées par une clé d'administration côté serveur.</p>
      </section>
    </Layout>
  );
}
