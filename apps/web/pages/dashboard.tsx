import type { GetServerSideProps } from 'next';
import Link from 'next/link';
import type { CSSProperties, ReactNode } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { MiniLineChart, TeamComparisonCurve, TeamCrest } from '~/components/ui';
import { getMatches, getPredictions, getPublicDashboardSummary } from '~/lib/api';
import {
  matchHref,
  buildDashboardSummary,
  matches as mockMatches,
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
  referenceTime: string;
};

export const getServerSideProps: GetServerSideProps<DashboardProps> = async () => {
  const [matchesResult, summaryResult, predictionsResult] = await Promise.allSettled([
    getMatches({ includeFinished: true }),
    getPublicDashboardSummary(),
    getPredictions({ limit: 160, view: 'upcoming', includeHybridEngine: true }),
  ]);

  let rawMatches: Match[] = matchesResult.status === 'fulfilled' ? matchesResult.value : mockMatches;
  let predictions: Prediction[] = predictionsResult.status === 'fulfilled' ? predictionsResult.value : [];
  let summary: DashboardSummary = summaryResult.status === 'fulfilled' ? summaryResult.value : buildDashboardSummary();

  if (matchesResult.status === 'rejected') console.error('Dashboard matches SSR fallback:', matchesResult.reason);
  if (summaryResult.status === 'rejected') console.error('Dashboard summary SSR fallback:', summaryResult.reason);
  if (predictionsResult.status === 'rejected') console.error('Dashboard predictions SSR unavailable:', predictionsResult.reason);
  const hasOfficialMatches = rawMatches.some((match) => match.source === 'football-data.org');
  const allMatches = hasOfficialMatches
    ? rawMatches.filter((match) => match.source === 'football-data.org')
    : rawMatches;
  const referenceTime = new Date().toISOString();
  const referenceTimestamp = new Date(referenceTime).getTime();
  const upcoming = [...allMatches]
    .filter((match) => isUpcoming(match, referenceTimestamp))
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
      predictions,
      summary: dashboardSummary,
      referenceTime,
    },
  };
};

export default function DashboardPage({ matches, predictions, summary, referenceTime }: DashboardProps) {
  const referenceTimestamp = new Date(referenceTime).getTime();
  const upcoming = [...matches]
    .filter((match) => isUpcoming(match, referenceTimestamp))
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
  const featuredMatch = upcoming[0] ?? finished[0] ?? matches[0];
  const signalPredictions = uniquePredictions([...predictions, ...summary.top_reliable_matches])
    .filter((prediction) => isUpcomingPrediction(prediction, referenceTimestamp))
    .filter((prediction) => typeof prediction.confidence?.score === 'number')
    .sort((a, b) => b.confidence.score - a.confidence.score);
  const riskySignalPredictions = uniquePredictions(summary.top_risky_matches)
    .filter((prediction) => isUpcomingPrediction(prediction, referenceTimestamp))
    .sort((a, b) => b.confidence.score - a.confidence.score);
  const averageConfidence =
    signalPredictions.length > 0
      ? Math.round(signalPredictions.reduce((total, prediction) => total + prediction.confidence.score, 0) / signalPredictions.length)
      : summary.average_confidence;
  const confidenceCurve = signalPredictions.slice(0, 10).map((prediction) => prediction.confidence.score);
  const homeComparisonCurve = [
    featuredMatch?.probabilities?.home ?? 50,
    featuredMatch?.confidence?.score ?? averageConfidence,
    summary.upcoming_matches_count,
    summary.total_matches,
  ].map((value) => Math.max(10, Math.min(95, Number(value) || 50)));
  const awayComparisonCurve = [
    featuredMatch?.probabilities?.away ?? 35,
    featuredMatch?.probabilities?.draw ?? 28,
    summary.avoid_matches_count + summary.trap_matches_count,
    summary.historical_matches_count ?? finished.length,
  ].map((value) => Math.max(10, Math.min(95, Number(value) || 35)));

  return (
    <ProtectedRoute>
      <Layout>
        <section className="dashboardBoard">
          <div className="dashboardTitle">
            <p className="eyebrow">Centre de contrôle</p>
            <h1>Bonjour, Analyste</h1>
            <p>Voici votre vue d'ensemble tactique et financière.</p>
          </div>

          <div className="dashboardShowcase">
            <Link className="tacticalPanel clickable-card" href={featuredMatch ? matchHref(featuredMatch) : '/matches'}>
              <div className="panelHeading">
                <span>Aperçu tactique du match</span>
                <b>En vedette</b>
              </div>
              <div className="teamsDuel">
                <div>
                  <TeamCrest name={featuredMatch?.home_team ?? 'Équipe domicile'} />
                  <strong>{featuredMatch?.home_team ?? 'Équipe domicile'}</strong>
                  <small>Probabilité de victoire</small>
                  <em>{featuredMatch?.probabilities?.home ?? 54}%</em>
                </div>
                <TacticalPitch value={featuredMatch?.probabilities?.draw ?? 26} />
                <div>
                  <TeamCrest name={featuredMatch?.away_team ?? 'Équipe extérieure'} tone="away" />
                  <strong>{featuredMatch?.away_team ?? 'Équipe extérieure'}</strong>
                  <small>Probabilité de victoire</small>
                  <em>{featuredMatch?.probabilities?.away ?? 20}%</em>
                </div>
              </div>
              <div className="matchMetaStrip">
                <span>Compétition <strong>{formatCompetitionLabel(featuredMatch?.competition)}</strong></span>
                <span>Date & heure <strong>{featuredMatch ? formatKickoffFr(featuredMatch.kickoff) : 'À venir'}</strong></span>
                <span>Confiance <strong>{averageConfidence}/100</strong></span>
              </div>
            </Link>

            <article className="sideSignalPanel">
              <div className="panelHeading">
                <span>Prédictions principales</span>
              </div>
              <div className="premiumSignalList">
                {signalPredictions.slice(0, 5).map((prediction) => (
                  <Link href={matchHref(prediction)} key={prediction.match_id}>
                    <TeamCrest name={prediction.home_team} />
                    <span>
                      <strong>{prediction.home_team}</strong>
                      <small>{prediction.main_prediction}</small>
                    </span>
                    <em>{prediction.confidence.score}%</em>
                    <b>{formatSyntheticOdd(prediction.confidence.score)}</b>
                  </Link>
                ))}
              </div>
              {signalPredictions.length === 0 && <div className="emptyState compact">Aucune prédiction exploitable pour le moment.</div>}
              <Link className="premiumInlineButton" href="/predictions">
                Voir toutes les prédictions
              </Link>
            </article>
          </div>

          <div className="premiumDashboardGrid">
            <article className="premiumMiniPanel">
              <h2>Opportunités à valeur attendue</h2>
              {signalPredictions.slice(0, 4).map((prediction) => (
                <Link className="marketLine" href={matchHref(prediction)} key={prediction.match_id}>
                  <span>{prediction.home_team}</span>
                  <strong>{formatSyntheticOdd(prediction.confidence.score)}</strong>
                  <em>+{Math.max(1, Math.round(prediction.confidence.score / 20))},21%</em>
                </Link>
              ))}
              {signalPredictions.length === 0 && <p className="muted">Aucune opportunité classée. Consultez toutes les prédictions.</p>}
            </article>
            <article className="premiumMiniPanel radarPanel">
              <h2>Comparaison des équipes</h2>
              <TeamComparisonCurve
                homeLabel={featuredMatch?.home_team ?? 'Domicile'}
                awayLabel={featuredMatch?.away_team ?? 'Extérieur'}
                homePoints={homeComparisonCurve}
                awayPoints={awayComparisonCurve}
              />
              <Link className="premiumInlineButton" href="/performance">Voir l'analyse complète</Link>
            </article>
            <article className="premiumMiniPanel aiPanel">
              <h2>Résumé IA</h2>
              <div className="aiIcon" aria-hidden="true">◎</div>
              <p>Les signaux actuels indiquent une lecture exploitable si la confiance reste supérieure au seuil.</p>
            </article>
            <article className="premiumMiniPanel performancePanel">
              <h2>Historique de performance</h2>
              <MiniLineChart points={confidenceCurve.length > 1 ? confidenceCurve : [45, 52, 58, averageConfidence || 60]} />
              <strong>{averageConfidence}/100</strong>
              <span>Confiance moyenne exploitable</span>
            </article>
          </div>
        </section>

        <section className="commandHero dashboardLegacyHero">
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
          <Panel title="Matchs les plus fiables" empty="Aucun match fiable futur disponible.">
            {signalPredictions.map((prediction) => (
              <PredictionCard prediction={prediction} key={prediction.match_id} />
            ))}
          </Panel>

          <Panel title="Matchs à surveiller" empty="Aucune alerte future active.">
            {riskySignalPredictions.map((prediction) => (
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
  const hasProbabilities =
    typeof match.probabilities?.home === 'number' &&
    typeof match.probabilities?.draw === 'number' &&
    typeof match.probabilities?.away === 'number';

  return (
    <Link className="card matchCard fixtureCard clickable-card" href={matchHref(match)}>
      <div className="cardTop">
        <span>{formatCompetitionLabel(match.competition)}</span>
        <span className="badge">{formatKickoffFr(match.kickoff)}</span>
      </div>

      <div className="fixtureTeams">
        <TeamLine name={match.home_team} />
        <span className="versus">vs</span>
        <TeamLine name={match.away_team} tone="away" />
      </div>

      {hasProbabilities ? (
        <div className="compactDataGrid three readableProbGrid">
          <div className="miniStat">
            <span>Domicile</span>
            <strong>{match.probabilities?.home}%</strong>
          </div>
          <div className="miniStat">
            <span>Nul</span>
            <strong>{match.probabilities?.draw}%</strong>
          </div>
          <div className="miniStat">
            <span>Extérieur</span>
            <strong>{match.probabilities?.away}%</strong>
          </div>
        </div>
      ) : (
        <div className="dataUnavailable">Probabilités en attente de calcul exploitable</div>
      )}
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

function TacticalPitch({ value }: { value: number }) {
  const ringValue = `${Math.min(Math.max(value, 0), 100) * 3.6}deg`;

  return (
    <div className="pitchVisual" aria-label={`Probabilité du nul ${value}%`}>
      <div className="pitchLines" />
      <div className="probRing" style={{ '--ring-value': ringValue } as CSSProperties}>
        <strong>{value}%</strong>
        <span>Nul</span>
      </div>
    </div>
  );
}

function TeamLine({ name, tone = 'home' }: { name: string; tone?: 'home' | 'away' }) {
  return (
    <span className="teamLine">
      <TeamCrest name={name} tone={tone} />
      <strong>{name}</strong>
    </span>
  );
}

function uniquePredictions(items: Prediction[]) {
  const map = new Map<string, Prediction>();
  for (const item of items) {
    const key = item.match_id || item.slug || item.id;
    if (!map.has(key)) map.set(key, item);
  }
  return [...map.values()];
}

function isUpcomingPrediction(prediction: Prediction, referenceTimestamp: number) {
  const kickoffTime = new Date(prediction.kickoff).getTime();
  return (
    String(prediction.status ?? '').toUpperCase() !== 'FINISHED' &&
    Number.isFinite(kickoffTime) &&
    kickoffTime >= referenceTimestamp
  );
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

function formatSyntheticOdd(confidenceScore: number) {
  return Math.max(1.18, 2.48 - confidenceScore / 100).toFixed(2);
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

