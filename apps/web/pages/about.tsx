import { Layout } from '~/src-layout';

export default function AboutPage() {
  return (
    <Layout>
      <section className="pageHeader">
        <p className="eyebrow">Positionnement</p>
        <h1>Analyse probabiliste responsable</h1>
        <p>
          FootIQ Pro aide les fans, analystes, journalistes et créateurs de contenu à comprendre les matchs avec des
          probabilités, pas avec des promesses.
        </p>
      </section>

      <section className="grid three">
        <article className="card">
          <h2>Lire les matchs</h2>
          <p>Identifier les rencontres où les signaux statistiques convergent clairement.</p>
        </article>
        <article className="card">
          <h2>Repérer les pièges</h2>
          <p>Détecter les favoris apparents fragilisés par des signaux contradictoires.</p>
        </article>
        <article className="card">
          <h2>Expliquer simplement</h2>
          <p>Présenter les risques, les probabilités et la confiance dans un langage clair.</p>
        </article>
      </section>

      <section className="notice">
        FootIQ Pro est un support d'aide à la décision. Aucune analyse ne garantit un score, un résultat ou un gain.
      </section>
    </Layout>
  );
}
