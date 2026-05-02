import type { GetStaticProps } from 'next';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { InfoTooltip } from '~/components/InfoTooltip';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getDashboardSummary, getMatches, getMlStatus, getPredictions } from '~/lib/api';
import { matchHref, statusClass, type DashboardSummary, type Match, type MlStatus, type Prediction } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type DashboardProps = {
  matches: Match[];
  predictions: Prediction[];
  summary: DashboardSummary;
  mlStatus: MlStatus;
};

export const getStaticProps: GetStaticProps<DashboardProps> = async () => {
  const [matches, predictions, summary, mlStatus] = await Promise.all([getMatches(), getPredictions(), getDashboardSummary(), getMlStatus()]);

  return { props: { matches, predictions, summary, mlStatus }, revalidate: 120 };
};

export default function DashboardPage({ matches, predictions, summary, mlStatus }: DashboardProps) {
  const upcoming = [...matches]
    .sort((a, b) => new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime())
    .slice(0, 5);
  const statusDistribution = [
    { label: 'FIABLE', value: summary.reliable_matches_count, href: '/predictions?status=FIABLE' },
    { label: 'MOYEN', value: summary.medium_matches_count, href: '/predictions?status=MOYEN' },
    { label: 'A EVITER', value: summary.avoid_matches_count, href: '/predictions?status=avoid' },
  ];
  const competitions = Object.entries(summary.competitions_breakdown);
  const candidate = mlStatus.latest_candidate;

  return (
    <ProtectedRoute>
      <Layout>
      <section className="commandHero">
        <div>
          <p className="eyebrow">Command center</p>
          <h1>Tableau de bord</h1>
          <p>Lecture dynamique des matchs importés, des risques et de la confiance du modèle.</p>
        </div>
        <div className="heroStats">
          <Stat label="Matchs" value={summary.total_matches} href="/matches" />
          <Stat label="Confiance" value={`${summary.average_confidence}`} href="/performance" />
          <Stat label="Fiables" value={summary.reliable_matches_count} href="/predictions?status=FIABLE" />
          <Stat label="Pièges" value={summary.trap_matches_count} href="/predictions?trap=true" />
        </div>
        <div className="sourceStrip">
          <span>Source: {summary.source}</span>
          <span>Storage: {summary.storage}</span>
          <span>Modèle: {summary.model_version ?? 'elo-poisson-calibrated-v1'}</span>
          <span>
            Actualisation: {summary.last_refresh_at ? new Date(summary.last_refresh_at).toLocaleString('fr-FR') : 'Non lancée'}
          </span>
        </div>
      </section>

      <section className="metrics">
        <Stat label="Matchs à venir" value={summary.upcoming_matches_count} href="/matches" />
        <Stat label="Matchs fiables" value={summary.reliable_matches_count} href="/predictions?status=FIABLE" />
        <Stat
          label="Alertes de risque"
          value={summary.avoid_matches_count + summary.trap_matches_count}
          href="/predictions?trap=true"
        />
        <Stat label="Confiance moyenne" value={summary.average_confidence} href="/performance" />
        <Stat label="Score de risque" value={summary.average_risk_score ?? 0} href="/performance" />
        <Stat label="Équipes" value={summary.teams_count} href="/teams" />
        <Stat label="Prédictions" value={summary.predictions_count} href="/predictions" />
        <Stat label="Compétitions" value={competitions.length} href="/matches" />
      </section>

      <section className="card modelReliabilityBlock">
        <div>
          <p className="eyebrow">État du modèle</p>
          <h2>Fiabilité et comparaison</h2>
          <p>Modèle de production: {summary.current_model_version ?? summary.model_version ?? 'elo-poisson-calibrated-v1'}. Le candidat ML reste en observation.</p>
        </div>
        <div className="compactDataGrid four">
          <Link className="metric clickable-card" href="/performance">
            <span>Matchs évalués</span>
            <strong>{summary.evaluated_matches ?? 0}</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance">
            <span className="metricHelp">Accuracy <InfoTooltip content="Pourcentage de résultats correctement prédits sur l’échantillon évalué." /></span>
            <strong>{summary.result_accuracy ?? 0}%</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance">
            <span className="metricHelp">Brier <InfoTooltip content="Mesure la qualité des probabilités. Plus le score est bas, meilleur est le modèle." /></span>
            <strong>{summary.average_brier_score ?? 0}</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance">
            <span className="metricHelp">Calibration <InfoTooltip content="Mesure si les probabilités annoncées correspondent aux résultats observés." /></span>
            <strong>{summary.calibration_score ?? 0}/100</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance">
            <span>Smoothing</span>
            <strong>{summary.calibration_applied ? 'on' : 'on'}</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance#model-comparison">
            <span>Snapshots</span>
            <strong>{summary.snapshots_count ?? 0}</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance#model-comparison">
            <span>Best Brier</span>
            <strong>{summary.best_model_by_brier ?? 'N/A'}</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance#feature-store">
            <span>Lignes Feature Store</span>
            <strong>{summary.training_rows_available ?? 0}</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance#feature-store">
            <span>Couverture cible</span>
            <strong>{summary.target_coverage ?? 0}%</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance#feature-store">
            <span className="metricHelp">Feature Store <InfoTooltip content="Base de données des variables utilisées par les modèles pour apprendre et comparer les performances." /></span>
            <strong>{summary.feature_store_ready ? 'prêt' : 'en attente'}</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance#candidate-ml">
            <span className="metricHelp">Candidat ML <InfoTooltip content="Modèle supervisé entraîné sur l'historique, actuellement en observation et non utilisé en production." /></span>
            <strong>{summary.ml_candidate_status ?? candidate.status}</strong>
          </Link>
          <Link className="metric clickable-card" href="/performance#candidate-ml">
            <span>Accuracy ML</span>
            <strong>{summary.ml_candidate_accuracy ?? candidate.accuracy ?? 0}%</strong>
          </Link>
        </div>
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
          Admin data
        </Link>
      </section>

      <section className="sectionSplit">
        <Panel title="Matchs les plus fiables" empty="Aucun match fiable disponible.">
          {summary.top_reliable_matches.map((prediction) => (
            <PredictionCard prediction={prediction} key={prediction.match_id} />
          ))}
        </Panel>
        <Panel title="Matchs pièges / alertes de risque" empty="Aucune alerte active.">
          {summary.top_risky_matches.map((prediction) => (
            <PredictionCard prediction={prediction} key={prediction.match_id} />
          ))}
        </Panel>
      </section>

      <section className="sectionSplit">
        <Panel title="Prochaines affiches" empty="Aucun match à venir.">
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



