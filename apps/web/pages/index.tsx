import Link from "next/link";

export default function Home() {
  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-badge">FootIQ Pro · Analyse probabiliste</div>

        <h1>L’intelligence statistique du football européen.</h1>

        <p className="hero-subtitle">
          FootIQ Pro transforme les données football en probabilités lisibles :
          matchs fiables, signaux de risque, confidence index et détection des
          matchs pièges.
        </p>

        <div className="hero-actions">
          <Link href="/dashboard" className="btn btn-primary">
            Voir le dashboard
          </Link>
          <Link href="/matches" className="btn btn-secondary">
            Explorer les matchs
          </Link>
        </div>

        <p className="disclaimer">
          Outil d’analyse statistique et probabiliste. Aucune prédiction ne
          garantit un résultat.
        </p>
      </section>

      <section className="grid-3">
        <article className="glass-card">
          <h2>Probabilités claires</h2>
          <p>1N2, over/under, BTTS, score attendu et explication en français.</p>
        </article>

        <article className="glass-card">
          <h2>Confidence Index</h2>
          <p>Un score de fiabilité pour savoir quand les données parlent vraiment.</p>
        </article>

        <article className="glass-card">
          <h2>Matchs pièges</h2>
          <p>Détection des favoris fragiles, signaux contradictoires et risques cachés.</p>
        </article>
      </section>
    </main>
  );
}