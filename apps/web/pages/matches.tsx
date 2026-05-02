import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getMatches } from '~/lib/api';
import { matchHref, statusClass, type Match } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type MatchesProps = {
  matches: Match[];
};

export const getStaticProps: GetStaticProps<MatchesProps> = async () => ({
  props: { matches: await getMatches() },
  revalidate: 120,
});

export default function MatchesPage({ matches }: MatchesProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [competition, setCompetition] = useState('');
  const [sort, setSort] = useState('date');
  const competitions = [...new Set(matches.map((match) => match.competition))].sort();

  useEffect(() => {
    if (typeof router.query.competition === 'string') {
      setCompetition(router.query.competition);
    }
  }, [router.query.competition]);

  const filteredMatches = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const result = matches.filter((match) => {
      const matchesQuery =
        !normalizedQuery ||
        `${match.home_team} ${match.away_team} ${match.competition}`.toLowerCase().includes(normalizedQuery);
      const matchesCompetition = !competition || match.competition === competition;

      return matchesQuery && matchesCompetition;
    });

    return result.sort((a, b) => {
      if (sort === 'confidence') {
        return (b.confidence?.score ?? 0) - (a.confidence?.score ?? 0);
      }

      if (sort === 'competition') {
        return a.competition.localeCompare(b.competition);
      }

      return new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime();
    });
  }, [competition, matches, query, sort]);

  return (
    <ProtectedRoute>
      <Layout>
      <section className="pageHeader">
        <p className="eyebrow">Calendrier predictif</p>
        <h1>Matchs a venir</h1>
        <p>{matches.length} matchs disponibles depuis l'API ou le fallback mock.</p>
      </section>

      <section className="filters">
        <input
          aria-label="Search matches"
          placeholder="Rechercher une equipe..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select aria-label="Competition" value={competition} onChange={(event) => setCompetition(event.target.value)}>
          <option value="">Toutes competitions</option>
          {competitions.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <select aria-label="Sort" value={sort} onChange={(event) => setSort(event.target.value)}>
          <option value="date">Kickoff</option>
          <option value="confidence">Confidence</option>
          <option value="competition">Competition</option>
        </select>
      </section>

      <section className="stack">
        {filteredMatches.length > 0 ? (
          filteredMatches.map((match) => <MatchRow match={match} key={match.id} />)
        ) : (
          <div className="emptyState">Aucun match ne correspond aux filtres.</div>
        )}
      </section>
      </Layout>
    </ProtectedRoute>
  );
}

function MatchRow({ match }: { match: Match }) {
  return (
    <Link className="rowCard clickable-card" href={matchHref(match)}>
      <div>
        <span className="muted">{match.competition}</span>
        <h2>
          {match.home_team} vs {match.away_team}
        </h2>
        <p>{new Date(match.kickoff).toLocaleString('fr-FR', { dateStyle: 'full', timeStyle: 'short' })}</p>
      </div>
      <div className="probGrid">
        <span>
          1 <strong>{match.probabilities?.home ? `${match.probabilities.home}%` : 'N/A'}</strong>
        </span>
        <span>
          N <strong>{match.probabilities?.draw ? `${match.probabilities.draw}%` : 'N/A'}</strong>
        </span>
        <span>
          2 <strong>{match.probabilities?.away ? `${match.probabilities.away}%` : 'N/A'}</strong>
        </span>
      </div>
      <div>
        {match.confidence ? (
          <>
            <span className={`badge status-badge ${statusClass(match.confidence.status)}`}>
              {match.confidence.status}
            </span>
            <strong className="score">{match.confidence.score}</strong>
          </>
        ) : (
          <>
            <span className="badge status-badge moyen">{match.status ?? 'SCHEDULED'}</span>
            <strong className="score">{match.source ?? 'api'}</strong>
          </>
        )}
      </div>
      <span className="button secondary small">Voir analyse</span>
    </Link>
  );
}
