import type { GetServerSideProps } from 'next';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getMatches, getPublicDashboardSummary } from '~/lib/api';
import {
  matchHref,
  statusClass,
  type DashboardSummary,
  type Match,
  type Prediction,
} from '~/lib/mock-data';
import {
  formatCompetitionLabel,
  formatKickoffFr,
  formatStatusLabel,
} from '~/lib/ui-text';
import { Layout } from '~/src-layout';

type DashboardProps = {
  matches: Match[];
  predictions: Prediction[];
  summary: DashboardSummary;
};

export const getServerSideProps: GetServerSideProps<DashboardProps> = async () => {
  const [rawMatches, summary] = await Promise.all([
    getMatches({ includeFinished: true }),
    getPublicDashboardSummary(),
  ]);
  const hasOfficialMatches = rawMatches.some((match) => match.source === 'football-data.org');
  const allMatches = hasOfficialMatches
    ? rawMatches.filter((match) => match.source === 'football-data.org')
    : rawMatches;
  const upcoming = [...allMatches]
    .filter((match) => String(match.status ?? '').toUpperCase() !== 'FINISHED')
    .sort((a, b) => new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime());
  const finished = [...allMatches]
    .filter((match) => String(match.status ?? '').toUpperCase() === 'FINISHED')
    .sort((a, b) => new Date(b.kickoff).getTime() - new Date(a.kickoff).getTime());
  const competitionsBreakdown = allMatches.reduce<Record<string, number>>((accumulator, match) => {
    const competition = match.competition || 'Unknown';
    accumulator[competition] = (accumulator[competition] ?? 0) + 1;
    return accumulator;
  }, {});
  const dashboardSummary = {
    ...summary,
    total_matches: allMatches.length || summary.total_matches,
    upcoming_matches_count: upcoming.length,
    historical_matches_count: finished.length,
    competitions_breakdown: competitionsBreakdown,
  };

  return {
    props: {
      matches: [...upcoming.slice(0, 5), ...finished.slice(0, 5)],
      predictions: [],
      summary: dashboardSummary,
    },
  };
};

export default function DashboardPage({ matches, predictions, summary }: DashboardProps) {
  const upcoming = [...matches]
    .filter((match) => String(match.status ?? '').toUpperCase() !== 'FINISHED')
    .sort((a, b) => new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime())
    .slice(0, 5);

  const finished = [...matches]
    .filter((match) => String(match.status ?? '').toUpperCase() === 'FINISHED')
    .sort((a, b) => new Date(b.kickoff).getTime() - new Date(a.kickoff).getTime())
    .slice(0, 5);

  const statusDistribution = [
    { label: 'Fiables', value: summary.reliable_matches_count, href: '/predictions?status=FIABLE' },
    { label: 'Moyens', value: summary.medium_matches_count, href: '/predictions?status=MOYEN' },
    { label: 'À éviter', value: summary.avoid_matches_count, href: '/predictions?status=avoid' },
  ];

  const competitions = Object.entries(summary.competitions_breakdown);

  return (
    <ProtectedRoute>
      <Layout>
        <section className="commandHero">
          <div>
            <p className="eyebrow">Centre de contrôle</p>
            <h1>Tableau de bord</h1>
            <p>
              Les matchs à suivre, les meilleurs signaux, les risques et les scores récents en un seul écran.
            </p>
          </div>

          <div className="heroStats">
            <Stat label="Matchs" value={summary.total_matches} href="/matches" />
            <Stat label="À venir" value={summary.upcoming_matches_count} href="/matches" />
            <Stat label="Fiables" value={summary.reliable_matches_count} href="/predictions?status=FIABLE" />
            <Stat label="À éviter" value={summary.avoid_matches_count} href="/predictions?status=avoid" />
          </div>

          <div className="sourceStrip">
            <span>
              Dernière mise à jour :{' '}
              {summary.last_refresh_at
                ? new Date(summary.last_refresh_at).toLocaleString('fr-FR')
                : 'non disponible'}
            </span>
          </div>
        </section>

        <section className="metrics">
          <Stat label="Matchs à venir" value={summary.upcoming_matches_count} href="/matches" />
          <Stat label="Scores récents" value={summary.historical_matches_count ?? finished.length} href="/matches?view=history" />
          <Stat label="Signaux fiables" value={summary.reliable_matches_count} href="/predictions?status=FIABLE" />
          <Stat
            label="Alertes de risque"
            value={summary.avoid_matches_count + summary.trap_matches_count}
            href="/predictions?trap=true"
          />
          <Stat label="Confiance moyenne" value={`${summary.average_confidence}/100`} href="/predictions" />
          <Stat label="Risque moyen" value={`${summary.average_risk_score ?? 0}/100`} href="/predictions?status=avoid" />
          <Stat label="Équipes" value={summary.teams_count} href="/teams" />
          <Stat label="Compétitions" value={competitions.length} href="/matches" />
        </section>

        <section className="sectionSplit">
          <Panel title="Prochaines affiches" empty="Aucun match à venir.">
            {upcoming.map((match) => (
              <UpcomingMatchCard match={match} key={match.match_id || match.id} />
            ))}
          </Panel>

          <Panel title="Scores récents" empty="Aucun score récent disponible.">
            {finished.map((match) => (
              <FinishedMatchCard match={match} key={match.match_id || match.id} />
            ))}
          </Panel>
        </section>

        <section className="sectionSplit">
          <Panel title="Matchs les plus fiables" empty="Aucun match fiable disponible.">
            {summary.top_reliable_matches.map((prediction) => (
              <PredictionCard prediction={prediction} key={prediction.match_id} />
            ))}
          </Panel>

          <Panel title="Matchs à surveiller" empty="Aucune alerte active.">
            {summary.top_risky_matches.map((prediction) => (
              <PredictionCard prediction={prediction} key={prediction.match_id} />
            ))}
          </Panel>
        </section>

        <section className="sectionSplit">
          <Distribution title="Répartition des signaux" rows={statusDistribution} total={summary.predictions_count} />

          <Distribution
            title="Compétitions suivies"
            rows={competitions.map(([label, value]) => ({
              label: formatCompetitionLabel(label),
              value,
              href: `/matches?competition=${encodeURIComponent(label)}`,
            }))}
            total={matches.length}
          />
        </section>

        <section className="quickActions">
          <Link className="button secondary" href="/matches">
            Voir les matchs
          </Link>
          <Link className="button secondary" href="/matches?view=history">
            Scores récents
          </Link>
          <Link className="button secondary" href="/predictions">
            Voir les prédictions
          </Link>
          <Link className="button secondary" href="/teams">
            Explorer les équipes
          </Link>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}

function Stat({ label, value, href }: { label: string; value: number | string; href: string }) {
  return (
    <Link className="metric clickable-card" href={href}>
      <span>{label}</span>
      <strong>{value}</strong>
    </Link>
  );
}

function Panel({ title, empty, children }: { title: string; empty: string; children: ReactNode }) {
  const items = Array.isArray(children) ? children.filter(Boolean) : children;

  return (
    <div>
      <h2>{title}</h2>
      <div className="stack">
        {Array.isArray(items) && items.length === 0 ? <div className="emptyState">{empty}</div> : items}
      </div>
    </div>
  );
}

function UpcomingMatchCard({ match }: { match: Match }) {
  return (
    <Link className="card matchCard clickable-card" href={matchHref(match)}>
      <div className="cardTop">
        <span>{formatCompetitionLabel(match.competition)}</span>
        <span className="badge">{formatKickoffFr(match.kickoff)}</span>
      </div>

      <h3>
        {match.home_team} vs {match.away_team}
      </h3>

      <div className="compactDataGrid three">
        <div className="miniStat">
          <span>Domicile</span>
          <strong>{typeof match.probabilities?.home === 'number' ? `${match.probabilities.home}%` : 'N/A'}</strong>
        </div>
        <div className="miniStat">
          <span>Nul</span>
          <strong>{typeof match.probabilities?.draw === 'number' ? `${match.probabilities.draw}%` : 'N/A'}</strong>
        </div>
        <div className="miniStat">
          <span>Extérieur</span>
          <strong>{typeof match.probabilities?.away === 'number' ? `${match.probabilities.away}%` : 'N/A'}</strong>
        </div>
      </div>
    </Link>
  );
}

function FinishedMatchCard({ match }: { match: Match }) {
  const homeScore = match.score_full_time_home;
  const awayScore = match.score_full_time_away;
  const totalGoals =
    typeof homeScore === 'number' && typeof awayScore === 'number' ? homeScore + awayScore : null;
  const btts =
    typeof homeScore === 'number' && typeof awayScore === 'number'
      ? homeScore > 0 && awayScore > 0
      : null;
  const over25 = totalGoals !== null ? totalGoals > 2.5 : null;

  return (
    <Link className="card matchCard scoreFirstCard clickable-card" href={matchHref(match)}>
      <div className="cardTop">
        <span>{formatCompetitionLabel(match.competition)}</span>
        <span>{formatKickoffFr(match.kickoff)}</span>
      </div>

      <h3>
        {match.home_team} vs {match.away_team}
      </h3>

      <div className="scoreBlock">
        <span>{match.home_team}</span>
        <strong className="scoreValue">
          {typeof homeScore === 'number' ? homeScore : '-'} - {typeof awayScore === 'number' ? awayScore : '-'}
        </strong>
        <span>{match.away_team}</span>
      </div>

      <div className="matchResultSummary">
        <span>Total buts : {totalGoals ?? 'N/A'}</span>
        <span>Over 2.5 : {over25 === null ? 'N/A' : over25 ? 'oui' : 'non'}</span>
        <span>BTTS : {btts === null ? 'N/A' : btts ? 'oui' : 'non'}</span>
      </div>
    </Link>
  );
}

function PredictionCard({ prediction }: { prediction: Prediction }) {
  return (
    <Link className="card matchCard clickable-card" href={matchHref(prediction)}>
      <div className="cardTop">
        <span>{formatCompetitionLabel(prediction.competition)}</span>
        <span className={`badge status-badge ${statusClass(prediction.confidence.status)}`}>
          {formatStatusLabel(prediction.confidence.status)}
        </span>
      </div>

      <h3>
        {prediction.home_team} vs {prediction.away_team}
      </h3>

      <small>{formatKickoffFr(prediction.kickoff)}</small>

      <div className="confidenceLine confidence-bar">
        <span style={{ width: `${prediction.confidence.score}%` }} />
      </div>

      <p>{prediction.main_prediction}</p>
    </Link>
  );
}

function Distribution({
  title,
  rows,
  total,
}: {
  title: string;
  rows: Array<{ label: string; value: number; href: string }>;
  total: number;
}) {
  return (
    <article className="card">
      <h2>{title}</h2>
      <div className="stack">
        {rows.map((row) => (
          <Link className="distributionRow clickable-card" href={row.href} key={row.label}>
            <span>{row.label}</span>
            <strong>{row.value}</strong>
            <div className="confidenceLine confidence-bar">
              <span style={{ width: `${total > 0 ? Math.round((row.value / total) * 100) : 0}%` }} />
            </div>
          </Link>
        ))}
      </div>
    </article>
  );
}
