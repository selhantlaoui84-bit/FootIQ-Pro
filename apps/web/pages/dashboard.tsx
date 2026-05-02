export default function Dashboard() {
  return (
    <main className="page-shell">
      <h1>Dashboard FootIQ</h1>
      <section className="grid-3">
        <article className="glass-card">
          <h2>Matchs fiables</h2>
          <p>12 matchs avec un Confidence Index élevé.</p>
        </article>
        <article className="glass-card">
          <h2>Matchs pièges</h2>
          <p>3 favoris avec signaux contradictoires.</p>
        </article>
        <article className="glass-card">
          <h2>Confiance moyenne</h2>
          <p>74 / 100</p>
        </article>
      </section>
    </main>
  );
}


