import { useRouter } from "next/router";

export default function MatchDetail() {
  const router = useRouter();
  const { id } = router.query;

  return (
    <main className="page-shell">
      <h1>Analyse du match</h1>
      <section className="hero">
        <div className="hero-badge">Match ID : {id}</div>
        <h1>PSG vs Lyon</h1>
        <p className="hero-subtitle">
          PSG 61% · Nul 23% · Lyon 16%
        </p>
        <p>Score attendu : 2.1 - 1.2</p>
        <p>Confidence Index : 78 / 100 · FIABLE</p>
        <p className="disclaimer">
          Modèle probabiliste. Aucune garantie de résultat.
        </p>
      </section>
    </main>
  );
}


