import Link from "next/link";

export default function Home() {
  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-badge">FootIQ Pro Â· Analyse probabiliste</div>

        <h1>Lâ€™intelligence statistique du football europÃ©en.</h1>

        <p className="hero-subtitle">
          FootIQ Pro transforme les donnÃ©es football en probabilitÃ©s lisibles :
          matchs fiables, signaux de risque, confidence index et dÃ©tection des
          matchs piÃ¨ges.
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
          Outil dâ€™analyse statistique et probabiliste. Aucune prÃ©diction ne
          garantit un rÃ©sultat.
        </p>
      </section>

      <section className="grid-3">
        <article className="glass-card">
          <h2>ProbabilitÃ©s claires</h2>
          <p>1N2, over/under, BTTS, score attendu et explication en franÃ§ais.</p>
        </article>

        <article className="glass-card">
          <h2>Confidence Index</h2>
          <p>Un score de fiabilitÃ© pour savoir quand les donnÃ©es parlent vraiment.</p>
        </article>

        <article className="glass-card">
          <h2>Matchs piÃ¨ges</h2>
          <p>DÃ©tection des favoris fragiles, signaux contradictoires et risques cachÃ©s.</p>
        </article>
      </section>
    </main>
  );
}

