import Link from "next/link";

const matches = [
  { id: "psg-lyon", home: "PSG", away: "Lyon", confidence: 78 },
  { id: "marseille-rennes", home: "Marseille", away: "Rennes", confidence: 42 },
];

export default function Matches() {
  return (
    <main className="page-shell">
      <h1>Matchs à venir</h1>
      <div className="grid-3">
        {matches.map((match) => (
          <article className="glass-card" key={match.id}>
            <h2>{match.home} vs {match.away}</h2>
            <p>Confidence Index : {match.confidence}/100</p>
            <Link className="btn btn-secondary" href={`/matches/${match.id}`}>
              Voir analyse
            </Link>
          </article>
        ))}
      </div>
    </main>
  );
}


