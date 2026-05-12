import { Layout } from '~/src-layout';

export default function MentionsLegalesPage() {
  return (
    <Layout>
      <section className="pageHeader">
        <p className="eyebrow">Informations légales</p>
        <h1>Mentions légales</h1>
        <p>FootIQ Pro est une plateforme d'analyse football destinée à l'aide à la décision.</p>
      </section>

      <section className="card">
        <h2>Éditeur</h2>
        <p>FootIQ Pro est exploité comme service numérique d'analyse et de suivi de modèles football.</p>
      </section>

      <section className="card">
        <h2>Responsabilité</h2>
        <p>Les contenus sont probabilistes et ne doivent être utilisés que comme support d'analyse.</p>
      </section>
    </Layout>
  );
}
