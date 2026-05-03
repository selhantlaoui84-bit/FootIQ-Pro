import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getMatches } from '~/lib/api';
import { matchHref, statusClass, type Match, type MatchView } from '~/lib/mock-data';
import {
  formatCompetitionLabel,
  formatFinishedMatchSummary,
  formatKickoffFr,
  formatMatchStatusLabel,
  formatScore,
  formatStatusLabel,
  formatWinnerLabel,
} from '~/lib/ui-text';
import { Layout } from '~/src-layout';

type MatchesProps = {
  matches: Match[];
};

export const getStaticProps: GetStaticProps<MatchesProps> = async () => ({
  props: { matches: await getMatches() },
  revalidate: 120,
});

const viewLabels: Record<MatchView, string> = {
  upcoming: 'À venir',
  all: 'Tous',
  history: 'Historique',
};

export default function MatchesPage({ matches }: MatchesProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [competition, setCompetition] = useState('');
  const [view, setView] = useState<MatchView>('upcoming');
  const [status, setStatus] = useState('');
  const [sort, setSort] = useState('date');
  const competitions = [...new Set(matches.map((match) => match.competition).filter(Boolean))].sort();

  useEffect(() => {
    if (typeof router.query.competition === 'string') {
      setCompetition(router.query.competition);
    }
    if (router.query.view === 'all' || router.query.view === 'upcoming' || router.query.view === 'history') {
      setView(router.query.view);
    }
  }, [router.query.competition, router.query.view]);

  const filteredMatches = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const result = matches.filter((match) => {
      const finished = isFinished(match);
      const searchHaystack = `${match.home_team} ${match.away_team} ${match.competition} ${match.slug} ${match.match_id}`.toLowerCase();
      const matchesQuery = !normalizedQuery || searchHaystack.includes(normalizedQuery);
      const matchesCompetition = !competition || match.competition === competition;
      const matchesView = view === 'all' || (view === 'history' ? finished : !finished);
      const matchesStatus = !status || (status === 'upcoming' ? !finished : status === 'finished' ? finished : match.status === status);

      return matchesQuery && matchesCompetition && matchesView && matchesStatus;
    });

    return result.sort((a, b) => {
      if (sort === 'confidence') {
        return (b.confidence?.score ?? 0) - (a.confidence?.score ?? 0);
      }

      if (sort === 'competition') {
        return a.competition.localeCompare(b.competition);
      }

      const aDate = new Date(a.kickoff).getTime();
      const bDate = new Date(b.kickoff).getTime();
      return view === 'history' ? bDate - aDate : aDate - bDate;
    });
  }, [competition, matches, query, sort, status, view]);

  const upcomingCount = matches.filter((match) => !isFinished(match)).length;
  const historyCount = matches.filter(isFinished).length;

  return (
    <ProtectedRoute>
      <Layout>
        <section className="pageHeader">
          <p className="eyebrow">Calendrier dynamique</p>
          <h1>Matchs</h1>
          <p>
            Les matchs à venir sont affichés en priorité. L'historique reste consultable avec les scores et les chiffres clés.
          </p>
          <div className="sourceStrip">
            <span>À venir: {upcomingCount}</span>
            <span>Historique: {historyCount}</span>
            <span>Total : {matches.length}</span>
          </div>
        </section>

        <section className="filters searchFilterBar">
          <input
            aria-label="Rechercher des matchs"
            placeholder="Rechercher une équipe, une compétition ou un match..."
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <select aria-label="Vue" value={view} onChange={(event) => setView(event.target.value as MatchView)}>
            {Object.entries(viewLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <select aria-label="Statut" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Tous les statuts</option>
            <option value="upcoming">À venir</option>
            <option value="finished">Terminés</option>
          </select>
          <select aria-label="Compétition" value={competition} onChange={(event) => setCompetition(event.target.value)}>
            <option value="">Toutes compétitions</option>
            {competitions.map((item) => (
              <option key={item} value={item}>
                {formatCompetitionLabel(item)}
              </option>
            ))}
          </select>
          <select aria-label="Tri" value={sort} onChange={(event) => setSort(event.target.value)}>
            <option value="date">Date du match</option>
            <option value="confidence">Confiance</option>
            <option value="competition">Compétition</option>
          </select>
        </section>

        <section className="stack">
          {filteredMatches.length > 0 ? (
            filteredMatches.map((match) => <MatchRow match={match} key={match.id} />)
          ) : view === 'upcoming' ? (
            <div className="emptyState">Aucun match à venir disponible. Utilisez l'historique pour consulter les matchs terminés.</div>
          ) : (
            <div className="emptyState">Aucun match ne correspond aux filtres.</div>
          )}
        </section>
      </Layout>
    </ProtectedRoute>
  );
}

function MatchRow({ match }: { match: Match }) {
  const finished = isFinished(match);
  const scoreAvailable = match.score_full_time_home !== undefined && match.score_full_time_home !== null && match.score_full_time_away !== undefined && match.score_full_time_away !== null;
  const summary = formatFinishedMatchSummary(match);

  return (
    <Link className="rowCard clickable-card fluidCard" href={matchHref(match)}>
      <div>
        <span className="muted">{formatCompetitionLabel(match.competition)}</span>
        <h2>
          {match.home_team} vs {match.away_team}
        </h2>
        <p>{formatKickoffFr(match.kickoff)}</p>
        <div className="cardTop compact">
          <span className={`badge status-badge ${finished ? 'historicalBadge' : ''}`}>
            {formatMatchStatusLabel(match.status)}
          </span>
          {finished && <span className="badge">{formatWinnerLabel(match)}</span>}
        </div>
      </div>

      {finished ? (
        <div className="scoreBlock" aria-label="Score final">
          {scoreAvailable ? (
            <>
              <span className="responsiveText">{match.home_team}</span>
              <strong className="scoreValue">{formatScore(match)}</strong>
              <span className="responsiveText">{match.away_team}</span>
              <div className="matchResultSummary">
                <span>Mi-temps : {summary.halftime}</span>
                <span>Résultat 1N2 : {summary.result1n2}</span>
                <span>Over 2.5 : {summary.over25}</span>
                <span>BTTS : {summary.btts}</span>
              </div>
            </>
          ) : (
            <strong className="scoreValue">Score non disponible</strong>
          )}
        </div>
      ) : (
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
      )}

      <div>
        {match.confidence ? (
          <>
            <span className={`badge status-badge ${statusClass(match.confidence.status)}`}>{formatStatusLabel(match.confidence.status)}</span>
            <strong className="score">{match.confidence.score}</strong>
          </>
        ) : (
          <span className="badge status-badge moyen">{formatMatchStatusLabel(match.status)}</span>
        )}
      </div>
      <span className="button secondary small">Voir analyse</span>
    </Link>
  );
}

function isFinished(match: Match) {
  return String(match.status ?? '').toUpperCase() === 'FINISHED';
}
