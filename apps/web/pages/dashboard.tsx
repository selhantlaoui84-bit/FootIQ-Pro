import type { GetStaticProps } from 'next';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getDashboardSummary, getMatches, getPredictions } from '~/lib/api';
import { matchHref, statusClass, type DashboardSummary, type Match, type Prediction } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type DashboardProps = {
  matches: Match[];
  predictions: Prediction[];
  summary: DashboardSummary;
};

export const getStaticProps: GetStaticProps<DashboardProps> = async () => {
  const [matches, predictions, summary] = await Promise.all([getMatches(), getPredictions(), getDashboardSummary()]);

  return { props: { matches, predictions, summary }, revalidate: 120 };
};

export default function DashboardPage({ matches, predictions, summary }: DashboardProps) {
  const upcoming = [...matches]
    .sort((a, b) => new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime())
    .slice(0, 5);
  const statusDistribution = [
    { label: 'FIABLE', value: summary.reliable_matches_count, href: '/predictions?status=FIABLE' },
    { label: 'MOYEN', value: summary.medium_matches_count, href: '/predictions?status=MOYEN' },
    { label: 'A EVITER', value: summary.avoid_matches_count, href: '/predictions?status=avoid' },
  ];
  const competitions = Object.entries(summary.competitions_breakdown);

  return (
    <ProtectedRoute>
      <Layout>
      <section className="commandHero">
        <div>
          <p className="eyebrow">Command center</p>
          <h1>Dashboard</h1>
          <p>Lecture dynamique des matchs importés, des risques et de la confiance modèle.</p>
        </div>
        <div className="heroStats">
          <Stat label="Matchs" value={summary.total_matches} href="/matches" />
          <Stat label="Confidence" value={`${summary.average_confidence}`} href="/performance" />
          <Stat label="Fiables" value={summary.reliable_matches_count} href="/predictions?status=FIABLE" />
          <Stat label="Pièges" value={summary.trap_matches_count} href="/predictions?trap=true" />
        </div>
        <div className="sourceStrip">
          <span>Source: {summary.source}</span>
          <span>Storage: {summary.storage}</span>
          <span>
            Refresh: {summary.last_refresh_at ? new Date(summary.last_refresh_at).toLocaleString('fr-FR') : 'Non lancé'}
          </span>
        </div>
      </section>

      <section className="metrics">
        <Stat label="Upcoming matches" value={summary.upcoming_matches_count} href="/matches" />
        <Stat label="Reliable matches" value={summary.reliable_matches_count} href="/predictions?status=FIABLE" />
        <Stat
          label="Risk alerts"
          value={summary.avoid_matches_count + summary.trap_matches_count}
          href="/predictions?trap=true"
        />
        <Stat label="Average confidence" value={summary.average_confidence} href="/performance" />
        <Stat label="Teams" value={summary.teams_count} href="/teams" />
        <Stat label="Predictions" value={summary.predictions_count} href="/predictions" />
        <Stat label="Competitions" value={competitions.length} href="/matches" />
      </section>

      <section className="quickActions">
        <Link className="button secondary" href="/matches">
          Matchs
        </Link>
        <Link className="button secondary" href="/predictions">
          Prédictions
        </Link>
        <Link className="button secondary" href="/teams">
          Équipes
        </Link>
        <Link className="button primary" href="/admin">
          Refresh admin
        </Link>
      </section>

      <section className="sectionSplit">
        <Panel title="Top reliable matches" empty="Aucun match fiable disponible.">
          {summary.top_reliable_matches.map((prediction) => (
            <PredictionCard prediction={prediction} key={prediction.match_id} />
          ))}
        </Panel>
        <Panel title="Trap matches / risk alerts" empty="Aucune alerte active.">
          {summary.top_risky_matches.map((prediction) => (
            <PredictionCard prediction={prediction} key={prediction.match_id} />
          ))}
        </Panel>
      </section>

      <section className="sectionSplit">
        <Panel title="Upcoming fixtures" empty="Aucun match à venir.">
          {upcoming.map((match) => (
            <Link className="rowMini clickable-card" href={matchHref(match)} key={match.match_id}>
              <span>{match.competition}</span>
              <strong>
                {match.home_team} vs {match.away_team}
              </strong>
              <small>
                {new Date(match.kickoff).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })}
              </small>
            </Link>
          ))}
        </Panel>
        <div className="stack">
          <Distribution title="Status distribution" rows={statusDistribution} total={predictions.length} />
          <Distribution
            title="Competition distribution"
            rows={competitions.map(([label, value]) => ({
              label,
              value,
              href: `/matches?competition=${encodeURIComponent(label)}`,
            }))}
            total={matches.length}
          />
        </div>
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

function PredictionCard({ prediction }: { prediction: Prediction }) {
  return (
    <Link className="card matchCard clickable-card" href={matchHref(prediction)}>
      <div className="cardTop">
        <span>{prediction.competition}</span>
        <span className={`badge status-badge ${statusClass(prediction.confidence.status)}`}>
          {prediction.confidence.status}
        </span>
      </div>
      <h3>
        {prediction.home_team} vs {prediction.away_team}
      </h3>
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
