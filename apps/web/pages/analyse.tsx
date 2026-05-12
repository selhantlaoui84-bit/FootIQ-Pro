import type { GetServerSideProps } from 'next';
import Link from 'next/link';
import type { CSSProperties } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { TeamIdentity } from '~/components/TeamIdentity';
import { MiniLineChart, RadarChart, TeamComparisonCurve } from '~/components/ui';
import { getAssistantDailyBrief, getMatches, getPredictions, getValueBets } from '~/lib/api';
import {
  matchHref,
  matches as mockMatches,
  predictions as mockPredictions,
  type BettingAssistantResponse,
  type Match,
  type Prediction,
  type ValueBetResponse,
} from '~/lib/mock-data';
import { resolveMatchTeamLogo } from '~/lib/team-logos';
import { formatCompetitionLabel, formatKickoffFr } from '~/lib/ui-text';
import { Layout } from '~/src-layout';

type AnalyseProps = {
  match: Match | null;
  prediction: Prediction | null;
  assistant: BettingAssistantResponse | null;
  valueBets: ValueBetResponse | null;
};

export const getServerSideProps: GetServerSideProps<AnalyseProps> = async () => {
  const [matchesResult, predictionsResult, assistantResult, valueResult] = await Promise.allSettled([
    getMatches({ view: 'upcoming', includeFinished: true }),
    getPredictions({ limit: 80, view: 'upcoming', includeHybridEngine: true, includeExplainability: true }),
    getAssistantDailyBrief(),
    getValueBets({ limit: 12, include_watchlist: true }),
  ]);
  const matches = matchesResult.status === 'fulfilled' ? matchesResult.value : mockMatches;
  const predictions = predictionsResult.status === 'fulfilled' ? predictionsResult.value : mockPredictions;
  const prediction = predictions.find((item) => String(item.status ?? '').toUpperCase() !== 'FINISHED') ?? predictions[0] ?? null;
  const match = matches.find((item) => (item.match_id || item.id) === prediction?.match_id) ?? matches[0] ?? null;

  return {
    props: {
      match,
      prediction,
      assistant: assistantResult.status === 'fulfilled' ? assistantResult.value : null,
      valueBets: valueResult.status === 'fulfilled' ? valueResult.value : null,
    },
  };
};

export default function AnalysePage({ match, prediction, assistant, valueBets }: AnalyseProps) {
  const row = prediction ?? match;
  const homeLogo = resolveMatchTeamLogo(row, 'home');
  const awayLogo = resolveMatchTeamLogo(row, 'away');
  const home = prediction?.home_team ?? match?.home_team ?? 'Domicile';
  const away = prediction?.away_team ?? match?.away_team ?? 'Extérieur';
  const homeProbability = prediction?.probabilities?.home ?? null;
  const drawProbability = prediction?.probabilities?.draw ?? null;
  const awayProbability = prediction?.probabilities?.away ?? null;
  const topValue = valueBets?.items?.[0] ?? null;

  return (
    <ProtectedRoute>
      <Layout>
        <section className="pageHeader premiumPageIntro">
          <p className="eyebrow">Analyse tactique & financière</p>
          <h1>Analyse tactique</h1>
          <p>Lecture match, probabilité FootIQ, value, risque et contexte marché sans cote inventée.</p>
        </section>

        <section className="tacticalCommandGrid">
          <article className="premiumPanel tacticalHeroPanel">
            <div className="cardTop">
              <span>{formatCompetitionLabel(prediction?.competition ?? match?.competition)}</span>
              <Link className="button secondary small" href={row ? matchHref(row) : '/matches'}>Feuille de match</Link>
            </div>
            <div className="tacticalPitch">
              <div className="pitchTeam">
                <TeamIdentity teamName={home} logoUrl={homeLogo} size="lg" />
                <em>{homeProbability == null ? 'N/A' : `${homeProbability}%`}</em>
                <span>Victoire domicile</span>
              </div>
              <div className="pitchVisual">
                <div className="pitchLines" />
                <div className="probRing" style={{ '--ring-value': `${Math.max(0, Math.min(100, drawProbability ?? 0)) * 3.6}deg` } as CSSProperties}>
                  <strong>{drawProbability == null ? 'N/A' : `${drawProbability}%`}</strong>
                  <span>Nul</span>
                </div>
              </div>
              <div className="pitchTeam">
                <TeamIdentity teamName={away} logoUrl={awayLogo} size="lg" align="right" />
                <em>{awayProbability == null ? 'N/A' : `${awayProbability}%`}</em>
                <span>Victoire extérieur</span>
              </div>
            </div>
            <div className="matchMetaStrip">
              <span>Coup d'envoi <strong>{prediction?.kickoff ? formatKickoffFr(prediction.kickoff) : 'Données insuffisantes'}</strong></span>
              <span>Confiance <strong>{prediction?.confidence?.score == null ? 'Données insuffisantes' : `${prediction.confidence.score}/100`}</strong></span>
              <span>Marché <strong>{topValue?.odds_decimal == null ? 'Cote réelle non disponible' : `${topValue.odds_decimal}`}</strong></span>
            </div>
          </article>

          <article className="premiumPanel">
            <h2>Insights IA</h2>
            <div className="dataList compact">
              <span>Assistant <strong>{assistant?.summary.recommended_count ?? 'Données insuffisantes'}</strong></span>
              <span>Value status <strong>{topValue?.value_status ?? 'Cote réelle non disponible'}</strong></span>
              <span>EV <strong>{topValue?.expected_value == null ? 'Non calculable' : topValue.expected_value.toFixed(3)}</strong></span>
              <span>Risque <strong>{topValue?.risk_level ?? prediction?.confidence?.status ?? 'Données insuffisantes'}</strong></span>
            </div>
            <div className="banner warning">Analyse informative : toujours vérifier la cote réelle, la liquidité du marché et le niveau de risque.</div>
          </article>

          <article className="premiumPanel">
            <h2>Comparaison équipes</h2>
            <TeamComparisonCurve
              homeLabel={home}
              awayLabel={away}
              homePoints={[homeProbability ?? 50, prediction?.goals?.expected_home ? prediction.goals.expected_home * 25 : 45, prediction?.confidence?.score ?? 50, 62]}
              awayPoints={[awayProbability ?? 40, prediction?.goals?.expected_away ? prediction.goals.expected_away * 25 : 38, prediction?.risk_score ?? 45, 48]}
            />
          </article>

          <article className="premiumPanel">
            <h2>Radar contexte</h2>
            <RadarChart labels={['Attaque', 'Création', 'Risque', 'Marché', 'Confiance']} />
          </article>

          <article className="premiumPanel">
            <h2>xG et dynamique</h2>
            <MiniLineChart points={[homeProbability ?? 45, prediction?.confidence?.score ?? 55, awayProbability ?? 35, drawProbability ?? 28, prediction?.goals?.over_2_5 ?? 50]} />
            <p>{prediction?.explanation?.[0] ?? 'Données insuffisantes pour générer une lecture tactique détaillée.'}</p>
          </article>

          <article className="premiumPanel">
            <h2>Marchés à surveiller</h2>
            {(valueBets?.items ?? []).slice(0, 5).map((item) => (
              <Link className="marketLine" href={`/matches/${item.match_id}`} key={`${item.match_id}-${item.selection}`}>
                <span>{item.market} · {item.selection}</span>
                <strong>{item.opportunity_score == null ? 'N/A' : `${item.opportunity_score}/100`}</strong>
                <em>{item.expected_value == null ? 'Cote réelle non disponible' : `EV ${item.expected_value.toFixed(3)}`}</em>
              </Link>
            ))}
            {!valueBets?.items?.length && <div className="emptyState compact">Cote réelle non disponible.</div>}
          </article>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}
