import type { GetServerSideProps } from 'next';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { TeamIdentity } from '~/components/TeamIdentity';
import { MiniLineChart, TacticalPitch } from '~/components/ui';
import { getMatches } from '~/lib/api';
import { matchHref, matches as mockMatches, statusClass, type Match, type MatchView } from '~/lib/mock-data';
import { resolveMatchTeamLogo } from '~/lib/team-logos';
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
  referenceTime: string;
};

const viewLabels: Record<MatchView, string> = {
  upcoming: 'À venir',
  all: 'Tous',
  history: 'Historique',
};

export const getServerSideProps: GetServerSideProps<MatchesProps> = async () => {
  let rawMatches: Match[] = [];
  try {
    rawMatches = await getMatches({ includeFinished: true });
  } catch (error) {
    console.error('Matches SSR fallback:', error);
    rawMatches = mockMatches;
  }
  const hasOfficialMatches = rawMatches.some((match) => match.source === 'football-data.org');
  const matches = hasOfficialMatches
    ? rawMatches.filter((match) => match.source === 'football-data.org')
    : rawMatches;

  return {
    props: {
      matches: matches.map(compactMatch),
      referenceTime: new Date().toISOString(),
    },
  };
};

export default function MatchesPage({ matches, referenceTime }: MatchesProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [competition, setCompetition] = useState('');
  const [view, setView] = useState<MatchView>('upcoming');
  const [status, setStatus] = useState('');
  const [sort, setSort] = useState('date');
  const referenceTimestamp = new Date(referenceTime).getTime();
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
      const upcoming = isUpcoming(match, referenceTimestamp);
      const historical = finished || isPastKickoff(match, referenceTimestamp);
      const searchHaystack = `${match.home_team} ${match.away_team} ${match.competition} ${match.slug} ${match.match_id}`.toLowerCase();
      const matchesQuery = !normalizedQuery || searchHaystack.includes(normalizedQuery);
      const matchesCompetition = !competition || match.competition === competition;
      const matchesView = view === 'all' || (view === 'history' ? historical : upcoming);
      const matchesStatus = !status || (status === 'upcoming' ? upcoming : status === 'finished' ? finished : match.status === status);

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
  }, [competition, matches, query, referenceTimestamp, sort, status, view]);

  const upcomingCount = matches.filter((match) => isUpcoming(match, referenceTimestamp)).length;
  const historyCount = matches.filter((match) => isFinished(match) || isPastKickoff(match, referenceTimestamp)).length;
  const featuredMatch = filteredMatches[0] ?? matches[0];
  const recentFinished = matches.filter((match) => isFinished(match)).slice(0, 4);

  return (
    <ProtectedRoute>
      <Layout>
        <section className="pageHeader premiumPageIntro">
          <h1>Matchs</h1>
          <p>Suivez les rencontres, les signaux clés et les opportunités à venir.</p>
          <div className="sourceStrip">
            <span>À venir : {upcomingCount}</span>
            <span>Historique : {historyCount}</span>
            <span>Total : {matches.length}</span>
            <span>Source : football-data.org</span>
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

        <section className="matchesPremiumLayout">
          <div className="premiumPanel matchTablePanel">
            <div className="panelHeading">
              <span>Aujourd'hui - sélection FootIQ</span>
              <b>{filteredMatches.length} matchs</b>
            </div>
            <div className="premiumMatchTable">
              {filteredMatches.length > 0 ? (
                filteredMatches.slice(0, 10).map((match) => <MatchRow match={match} key={match.id} />)
              ) : view === 'upcoming' ? (
                <div className="emptyState">Aucun match à venir disponible. Utilisez l'historique pour consulter les matchs terminés.</div>
              ) : (
                <div className="emptyState">Aucun match ne correspond aux filtres.</div>
              )}
            </div>
          </div>

          {featuredMatch && (
            <aside className="premiumPanel featuredMatchPanel">
              <div className="panelHeading">
                <span>Match en vedette</span>
                <b>{formatCompetitionLabel(featuredMatch.competition)}</b>
              </div>
              <Link className="featuredPitchLink" href={matchHref(featuredMatch)}>
                <TacticalPitch
                  compact
                  home={featuredMatch.home_team}
                  away={featuredMatch.away_team}
                  homeValue={featuredMatch.probabilities?.home ?? 54}
                  drawValue={featuredMatch.probabilities?.draw ?? 26}
                  awayValue={featuredMatch.probabilities?.away ?? 20}
                />
                <span className="premiumInlineButton">Voir l'analyse complète</span>
              </Link>
            </aside>
          )}

          <article className="premiumPanel calendarPanel">
            <div className="panelHeading">
              <span>Calendrier tactique</span>
            </div>
            {filteredMatches.slice(0, 4).map((match) => (
              <Link className="compactFixture" href={matchHref(match)} key={`calendar-${match.id}`}>
                <span>{formatKickoffFr(match.kickoff)}</span>
                <strong>{match.home_team} vs {match.away_team}</strong>
              </Link>
            ))}
          </article>

          <article className="premiumPanel alertsPanel">
            <div className="panelHeading">
              <span>Résultats récents</span>
            </div>
            {recentFinished.length > 0 ? (
              recentFinished.map((match) => (
                <Link className="compactFixture" href={matchHref(match)} key={`recent-${match.id}`}>
                  <strong>{match.home_team} vs {match.away_team}</strong>
                  <span>{formatScore(match)}</span>
                </Link>
              ))
            ) : (
              <MiniLineChart />
            )}
          </article>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}

function MatchRow({ match }: { match: Match }) {
  const finished = isFinished(match);
  const scoreAvailable =
    match.score_full_time_home !== undefined &&
    match.score_full_time_home !== null &&
    match.score_full_time_away !== undefined &&
    match.score_full_time_away !== null;
  const summary = formatFinishedMatchSummary(match);
  const hasProbabilities =
    typeof match.probabilities?.home === 'number' &&
    typeof match.probabilities?.draw === 'number' &&
    typeof match.probabilities?.away === 'number';

  return (
    <Link className="rowCard clickable-card fluidCard matchListRow" href={matchHref(match)}>
      <div>
        <span className="muted">{formatCompetitionLabel(match.competition)}</span>
        <div className="fixtureTeams">
          <TeamLine name={match.home_team} logoUrl={resolveMatchTeamLogo(match, 'home')} />
          <span className="versus">vs</span>
          <TeamLine name={match.away_team} logoUrl={resolveMatchTeamLogo(match, 'away')} tone="away" />
        </div>
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
      ) : hasProbabilities ? (
        <div className="probGrid readableProbGrid">
          <span>
            1 <strong>{match.probabilities?.home}%</strong>
          </span>
          <span>
            N <strong>{match.probabilities?.draw}%</strong>
          </span>
          <span>
            2 <strong>{match.probabilities?.away}%</strong>
          </span>
        </div>
      ) : (
        <div className="dataUnavailable">Probabilités en attente</div>
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

function compactMatch(match: Match): Match {
  const {
    raw_json: _rawJson,
    ...rest
  } = match as Match & { raw_json?: unknown };

  return rest;
}

function TeamLine({ name, tone = 'home', logoUrl }: { name: string; tone?: 'home' | 'away'; logoUrl?: string | null }) {
  return (
    <TeamIdentity
      align={tone === 'away' ? 'right' : 'left'}
      className={`teamLine ${tone === 'away' ? 'away' : ''}`}
      logoUrl={logoUrl}
      teamName={name}
      size="sm"
    />
  );
}

function isFinished(match: Match) {
  return String(match.status ?? '').toUpperCase() === 'FINISHED';
}

function isPastKickoff(match: Match, referenceTimestamp: number) {
  const kickoffTimestamp = new Date(match.kickoff).getTime();
  return Number.isFinite(kickoffTimestamp) && kickoffTimestamp < referenceTimestamp;
}

function isUpcoming(match: Match, referenceTimestamp: number) {
  return !isFinished(match) && !isPastKickoff(match, referenceTimestamp);
}
