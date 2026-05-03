import type { GetStaticPaths, GetStaticProps } from 'next';
import Link from 'next/link';
import { InfoTooltip } from '~/components/InfoTooltip';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getMatch, getPrediction } from '~/lib/api';
import { matches, statusClass, teamNameHref, type Match, type Prediction } from '~/lib/mock-data';
import { formatCompetitionLabel, formatFinishedMatchSummary, formatKickoffFr, formatMatchStatusLabel, formatScore, formatWinnerLabel } from '~/lib/ui-text';
import { Layout } from '~/src-layout';

type MatchDetailProps = {
  match: Match;
  prediction: Prediction;
};

export const getStaticPaths: GetStaticPaths = async () => ({
  paths: matches.map((match) => ({ params: { id: match.slug } })),
  fallback: 'blocking',
});

export const getStaticProps: GetStaticProps<MatchDetailProps> = async ({ params }) => {
  const id = typeof params?.id === 'string' ? params.id : matches[0].slug;
  const [match, prediction] = await Promise.all([getMatch(id), getPrediction(id)]);

  return { props: { match, prediction }, revalidate: 120 };
};

export default function MatchDetailPage({ match, prediction }: MatchDetailProps) {
  const kickoff = prediction.kickoff || match.kickoff;
  const finished = isFinished(match) || isFinished(prediction);
  const homeScore = match.score_full_time_home ?? prediction.score_full_time_home;
  const awayScore = match.score_full_time_away ?? prediction.score_full_time_away;
  const scoreAvailable = homeScore !== undefined && homeScore !== null && awayScore !== undefined && awayScore !== null;
  const summary = formatFinishedMatchSummary({ ...match, ...prediction });
  const winner = formatWinnerLabel({ ...match, ...prediction });
  const shadow = prediction.shadow;
  const hybrid = prediction.hybrid;
  const hybridEngine = prediction.hybrid_engine;
  const explainability = prediction.explainability;

  return (
    <ProtectedRoute>
      <Layout>
        <section className="matchHeader">
          <div>
            <p className="eyebrow">{prediction.competition || match.competition}</p>
            <h1>
              {prediction.home_team} vs {prediction.away_team}
            </h1>
            <p>{formatKickoffFr(kickoff)}</p>
            <div className="cardTop compact">
              <span className={`badge status-badge ${finished ? 'historicalBadge' : ''}`}>{formatMatchStatusLabel(match.status ?? prediction.status)}</span>
              <span className="badge">{formatCompetitionLabel(prediction.competition || match.competition)}</span>
            </div>
          </div>
          {finished && scoreAvailable ? (
            <div className="scoreBlock large">
              <span>{prediction.home_team}</span>
              <strong className="scoreValue">{formatScore({ score_full_time_home: homeScore, score_full_time_away: awayScore })}</strong>
              <span>{prediction.away_team}</span>
              <small>{winner}</small>
            </div>
          ) : (
            <span className={`badge large status-badge ${statusClass(prediction.confidence.status)}`}>{prediction.confidence.status}</span>
          )}
        </section>

        {finished && (
          <section className="card accent">
            <h2 className="metricHelp">
              Contexte historique
              <InfoTooltip content="Les matchs terminés restent utilisés pour l'Elo, la forme, le Feature Store, le backtesting et l'entraînement ML." />
            </h2>
            <div className="matchResultSummary compactStatGrid">
              <span>Date <strong>{formatKickoffFr(kickoff)}</strong></span>
              <span>Compétition <strong>{formatCompetitionLabel(match.competition)}</strong></span>
              <span>Score final <strong>{summary.score}</strong></span>
              <span>Mi-temps <strong>{summary.halftime}</strong></span>
              <span>Résultat <strong>{summary.result1n2}</strong></span>
              <span>Vainqueur <strong>{winner}</strong></span>
              <span>Total buts <strong>{summary.totalGoals ?? 'N/A'}</strong></span>
              <span>Over 2.5 <strong>{summary.over25}</strong></span>
              <span>BTTS <strong>{summary.btts}</strong></span>
            </div>
            <p>La prédiction affichée sert ici de contexte post-match et de matière pour l'évaluation du modèle.</p>
          </section>
        )}

        <section className="grid three">
          <Probability label={prediction.home_team} value={prediction.probabilities.home} />
          <Probability label="Nul" value={prediction.probabilities.draw} />
          <Probability label={prediction.away_team} value={prediction.probabilities.away} />
        </section>

        <section className="sectionSplit">
          <article className="card">
            <h2>Lecture offensive</h2>
            <div className="dataList">
              <span>Score attendu <strong>{prediction.goals.expected_home} - {prediction.goals.expected_away}</strong></span>
              <span>Score probable <strong>{prediction.goals.most_likely_score ?? 'N/A'}</strong></span>
              <span>Over 1.5 <strong>{prediction.goals.over_1_5 ?? 'N/A'}%</strong></span>
              <span>Over 2.5 <strong>{prediction.goals.over_2_5}%</strong></span>
              <span>Over 3.5 <strong>{prediction.goals.over_3_5 ?? 'N/A'}%</strong></span>
              <span>BTTS <strong>{prediction.goals.btts}%</strong></span>
            </div>
          </article>

          <article className="card">
            <h2 className="metricHelp">
              Indice de confiance
              <InfoTooltip content="Indice de confiance du modèle. Il mesure la lisibilité statistique du match, pas une certitude de résultat." />
            </h2>
            <strong className="bigScore">{prediction.confidence.score}/100</strong>
            <div className="confidenceLine tall confidence-bar">
              <span style={{ width: `${prediction.confidence.score}%` }} />
            </div>
            <div className="dataList">
              <span className="metricHelp">Score de risque <InfoTooltip content="Score de risque contextuel. Plus il est élevé, plus le match est difficile à lire." /> <strong>{prediction.risk_score ?? 'N/A'}</strong></span>
              <span className="metricHelp">Score piège <InfoTooltip content="Indique un match potentiellement piégeux malgré un favori apparent." /> <strong>{prediction.trap_match_score ?? 'N/A'}</strong></span>
              <span>Qualité des données <strong>{prediction.features?.data_quality_score ?? 'N/A'}</strong></span>
            </div>
            <p>{prediction.recommendation}</p>
          </article>
        </section>

        <section className="grid three">
          <article className="card">
            <h2>Elo</h2>
            <strong className="bigScore">{prediction.features?.elo_delta ?? 'N/A'}</strong>
            <p>Écart Elo ajusté avec avantage domicile.</p>
            <InfoTooltip content="Écart de niveau relatif entre les deux équipes selon le système Elo." />
          </article>
          <article className="card">
            <h2>Forme</h2>
            <strong className="bigScore">{prediction.features?.form_delta ?? 'N/A'}</strong>
            <p>Différentiel de dynamique récente.</p>
            <InfoTooltip content="Différence de forme récente entre les équipes." />
          </article>
          <article className="card">
            <h2>Attaque / Défense</h2>
            <div className="dataList">
              <span>Écart attaque <strong>{prediction.features?.attack_delta ?? 'N/A'}</strong></span>
              <span>Écart défense <strong>{prediction.features?.defense_delta ?? 'N/A'}</strong></span>
              <span>Risque de nul <strong>{prediction.features?.draw_risk_score ?? 'N/A'}</strong></span>
            </div>
          </article>
        </section>

        {shadow && (
          <section className="card shadowCard">
            <h2 className="metricHelp">
              Comparaison shadow ML
              <InfoTooltip content="Le mode shadow calcule une prédiction ML en parallèle sans remplacer la prédiction officielle Elo/Poisson." />
            </h2>
            <p>{shadow.prediction?.note ?? "Le candidat ML reste non utilisé en production."}</p>
            <div className="comparisonMiniTable">
              <span>Choix production <strong>{translatePick(shadow.comparison?.production_pick)}</strong></span>
              <span>Choix shadow <strong>{translatePick(shadow.comparison?.shadow_pick)}</strong></span>
              <span>Accord <strong>{shadow.comparison?.same_pick === null ? 'N/A' : shadow.comparison?.same_pick ? 'oui' : 'non'}</strong></span>
              <span>Écart confiance <strong>{shadow.comparison?.confidence_delta ?? 'N/A'}</strong></span>
              <span className={`disagreementBadge ${shadow.comparison?.disagreement_level ?? 'unknown'}`}>Désaccord: {shadow.comparison?.disagreement_level ?? 'unknown'}</span>
            </div>
            {shadow.prediction?.probabilities && (
              <div className="probGrid">
                <span>1 <strong>{shadow.prediction.probabilities.home}%</strong></span>
                <span>N <strong>{shadow.prediction.probabilities.draw}%</strong></span>
                <span>2 <strong>{shadow.prediction.probabilities.away}%</strong></span>
              </div>
            )}
          </section>
        )}

        {hybridEngine && (
          <section className="card hybridEngineCard">
            <h2 className="metricHelp">
              Décision hybride v1
              <InfoTooltip content="Le moteur hybride v1 classe le niveau de consensus entre Elo/Poisson et le ML shadow, sans remplacer la prédiction officielle." />
            </h2>
            <h3>{hybridEngine.display_title}</h3>
            <p>{hybridEngine.display_message}</p>
            <div className="comparisonMiniTable">
              <span className="metricHelp">Score de consensus <InfoTooltip content="Mesure le niveau de convergence entre le signal officiel et le ML shadow." /> <strong>{hybridEngine.consensus_score}/100</strong></span>
              <span>Niveau de décision <strong className={`decisionBadge ${hybridEngine.decision_level}`}>{hybridEngine.decision_level}</strong></span>
              <span className="metricHelp">Action recommandée <InfoTooltip content="Action consultative: elle n'active jamais le ML en production." /> <strong>{hybridEngine.action}</strong></span>
              <span>Signal officiel <strong>{translatePick(hybridEngine.production_pick)}</strong></span>
              <span>Signal shadow <strong>{translatePick(hybridEngine.shadow_pick)}</strong></span>
              <span>Accord <strong>{hybridEngine.agreement}</strong></span>
              <span className="metricHelp">Ajustement du risque <InfoTooltip content="Variation consultative du niveau de risque selon le consensus ou le désaccord modèle." /> <strong>{hybridEngine.risk_adjustment}</strong></span>
            </div>
            <ul>{hybridEngine.explanation.map((item) => <li key={item}>{item}</li>)}</ul>
            {hybridEngine.warnings.length > 0 && <div className="banner warning">{hybridEngine.warnings.join(' ')}</div>}
            <div className="banner info">Le modèle officiel reste Elo/Poisson. Le moteur hybride ajoute une lecture de prudence ou de renforcement, sans remplacer la prédiction officielle.</div>
          </section>
        )}

        {hybrid && (
          <section className="card advisoryCard">
            <h2 className="metricHelp">
              Signal hybride
              <InfoTooltip content="Le mode hybride reste consultatif: le modèle officiel demeure Elo/Poisson et le ML shadow sert uniquement à renforcer ou nuancer la lecture." />
            </h2>
            <p>{hybrid.display_message}</p>
            <div className="comparisonMiniTable">
              <span>Label <strong>{hybrid.decision_label}</strong></span>
              <span className="metricHelp">Consensus <InfoTooltip content="Score de consensus entre le modèle officiel et le signal ML shadow. Plus il est haut, plus les signaux convergent." /> <strong>{hybrid.consensus_score}/100</strong></span>
              <span>Accord <strong>{hybrid.agreement}</strong></span>
              <span>Choix officiel <strong>{translatePick(hybrid.production_pick)}</strong></span>
              <span>Choix shadow <strong>{translatePick(hybrid.shadow_pick)}</strong></span>
              <span>Ajustement risque <strong>{hybrid.risk_adjustment}</strong></span>
            </div>
            <ul>{hybrid.explanation.map((item) => <li key={item}>{item}</li>)}</ul>
            <div className="banner info">Le modèle officiel reste Elo/Poisson. Le ML intervient uniquement comme signal d'observation.</div>
          </section>
        )}

        {explainability && (
          <section className="card explainabilityCard">
            <h2 className="metricHelp">
              Pourquoi cette prédiction ?
              <InfoTooltip content="Cette couche transforme les signaux statistiques en facteurs lisibles, sans garantir le résultat." />
            </h2>
            <p>{explainability.summary}</p>
            <div className="dataList">
              <span>Signal officiel <strong>{explainability.official_signal}</strong></span>
              <span className="metricHelp">
                Lecture confiance
                <InfoTooltip content="Lecture qualitative de la confiance du modèle. Elle mesure la lisibilité du match, pas une certitude." />
                <strong>{explainability.confidence_reading}</strong>
              </span>
            </div>

            <FactorGrid title="Facteurs favorables" factors={explainability.top_positive_factors} kind="positive" />
            <FactorGrid title="Points de prudence" factors={explainability.top_negative_factors} kind="negative" />

            {(explainability.risk_notes.length > 0 ||
              explainability.data_quality_notes.length > 0 ||
              explainability.hybrid_notes.length > 0) && (
              <div className="sectionSplit">
                <ExplanationList title="Notes de risque" items={explainability.risk_notes} />
                <ExplanationList title="Qualité des données" items={explainability.data_quality_notes} />
                <ExplanationList title="Lecture hybride" items={explainability.hybrid_notes} />
              </div>
            )}

            <div className="banner info">{explainability.plain_language}</div>
            <div className="notice">{explainability.disclaimer}</div>
          </section>
        )}

        <section className="sectionSplit">
          <article className="card accent">
            <h2>Recommandation FootIQ</h2>
            <strong>{prediction.recommendation}</strong>
            <p>{prediction.main_prediction}</p>
          </article>
          <article className={prediction.flags.trap_match || prediction.flags.risk ? 'card danger' : 'card'}>
            <h2>{prediction.flags.trap_match ? 'Match piège détecté' : 'Alerte de risque'}</h2>
            <p>
              {prediction.flags.trap_match
                ? 'Favori apparent, mais signaux contradictoires.'
                : prediction.flags.risk
                  ? 'Lisibilité réduite, prudence recommandée.'
                  : 'Aucune alerte majeure détectée.'}
            </p>
          </article>
        </section>

        <section className="sectionSplit">
          <article className="card">
            <h2>Explication</h2>
            <ul>{prediction.explanation.slice(0, 3).map((item) => <li key={item}>{item}</li>)}</ul>
          </article>
          <article className="card">
            <h2>Risques</h2>
            <ul>{prediction.risks.map((risk) => <li key={risk}>{risk}</li>)}</ul>
          </article>
        </section>

        <section className="grid three">
          {[prediction.home_team, prediction.away_team].map((team) => (
            <Link className="card clickable-card" href={teamNameHref(team)} key={team}>
              <h3>{team}</h3>
              <p>Voir la fiche équipe et les matchs liés.</p>
            </Link>
          ))}
        </section>

        <section className="notice">{prediction.disclaimer}</section>
        <div className="quickActions">
          <Link className="button secondary" href="/matches">Retour aux matchs</Link>
          <Link className="button secondary" href="/predictions">Retour aux prédictions</Link>
        </div>
      </Layout>
    </ProtectedRoute>
  );
}

function FactorGrid({
  title,
  factors,
  kind,
}: {
  title: string;
  factors: NonNullable<Prediction['explainability']>['top_positive_factors'];
  kind: 'positive' | 'negative' | 'neutral';
}) {
  if (!factors.length) return null;
  return (
    <div>
      <h3 className="metricHelp">
        {title}
        <InfoTooltip content="Les facteurs sont des signaux statistiques: ils orientent la lecture sans établir de causalité." />
      </h3>
      <div className="factorGrid">
        {factors.map((factor) => (
          <article className={`factorCard ${kind}`} key={`${factor.feature}-${factor.label}`}>
            <div className="cardTop compact">
              <strong>{factor.label}</strong>
              <span className={`badge ${factor.impact}`}>{factor.impact}</span>
            </div>
            <span>Valeur: {factor.value ?? 'N/A'}</span>
            <div className="factorStrength">
              <span style={{ width: `${factor.strength}%` }} />
            </div>
            <p>{factor.message}</p>
          </article>
        ))}
      </div>
    </div>
  );
}

function ExplanationList({ title, items }: { title: string; items: string[] }) {
  if (!items.length) return null;
  return (
    <article className="explanationPanel">
      <h3>{title}</h3>
      <ul className="explanationList">{items.map((item) => <li key={item}>{item}</li>)}</ul>
    </article>
  );
}

function Probability({ label, value }: { label: string; value: number }) {
  return (
    <article className="card probability">
      <span className="metricHelp">
        {label}
        <InfoTooltip content="Probabilité estimée par le modèle. Elle exprime une tendance statistique, pas une garantie." />
      </span>
      <strong>{value}%</strong>
      <div className="probabilityBar confidence-bar"><span style={{ width: `${value}%` }} /></div>
    </article>
  );
}

function isFinished(item: { status?: string }) {
  return String(item.status ?? '').toUpperCase() === 'FINISHED';
}

function translatePick(pick: string | null | undefined) {
  if (pick === 'home') return 'Domicile';
  if (pick === 'away') return 'Extérieur';
  if (pick === 'draw') return 'Nul';
  return 'N/A';
}
