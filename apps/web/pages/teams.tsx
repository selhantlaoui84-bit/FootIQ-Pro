export default function Teams() {
  return (
    <main className="page-shell">
      <h1>Équipes</h1>
      <section className="grid-3">
        {["PSG", "Marseille", "Lyon", "Monaco", "Lille", "Lens"].map((team) => (
          <article className="glass-card" key={team}>
            <h2>{team}</h2>
            <p>Forme récente, Elo et tendances à venir.</p>
          </article>
        ))}
      </section>
    </main>
  );
}


