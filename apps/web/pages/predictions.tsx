import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import { InfoTooltip } from '~/components/InfoTooltip';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { ProbabilityRing } from '~/components/ui';
import { getPredictions } from '~/lib/api';
import { isAvoidStatus, matchHref, predictions as mockPredictions, statusClass, type ConfidenceStatus, type Prediction } from '~/lib/mock-data';
import { formatCompetitionLabel, formatKickoffFr, formatRecommendationLabel, formatStatusLabel } from '~/lib/ui-text';
import { Layout } from '~/src-layout';

type PredictionsProps = {
  predictions: Prediction[];
  referenceTime: string;
};

export const getStaticProps: GetStaticProps<PredictionsProps> = async () => {
  try {
    return {
      props: {
        predictions: await getPredictions({
          includeHybridEngine: true,
          includeExplainability: true,
          limit: 100,
          view: 'upcoming',
        }),
        referenceTime: new Date().toISOString(),
      },
      revalidate: 120,
    };
  } catch (error) {
    console.error('Predictions ISR fallback:', error);
    return { props: { predictions: mockPredictions, referenceTime: new Date().toISOString() }, revalidate: 120 };
  }
};

export default function PredictionsPage({ predictions, referenceTime }: PredictionsProps) {
  const router = useRouter();
  const [status, setStatus] = useState('');
  const [trapOnly, setTrapOnly] = useState(false);
  const [riskOnly, setRiskOnly] = useState(false);
  const [highConfidence, setHighConfidence] = useState(false);
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (typeof router.query.status === 'string') {
      setStatus(router.query.status === 'avoid' ? 'À ÉVITER' : router.query.status);
    }

    setTrapOnly(router.query.trap === 'true');
  }, [router.query.status, router.query.trap]);

  const filtered = useMemo(() => {
      const referenceStart = new Date(referenceTime);
      referenceStart.setHours(0, 0, 0, 0);

      return predictions
        .filter((prediction) => {
          const kickoffTime = new Date(prediction.kickoff).getTime();
          const isUpcoming = Number.isFinite(kickoffTime) && kickoffTime >= referenceStart.getTime();
          const statusMatches =
            !status ||
            prediction.confidence.status === status ||
            (status === 'À ÉVITER' && isAvoidStatus(prediction.confidence.status));
          const trapMatches = !trapOnly || prediction.flags.trap_match;
          const riskMatches = !riskOnly || prediction.flags.risk;
          const confidenceMatches = !highConfidence || prediction.confidence.score >= 70;
          const queryMatches =
            !query.trim() ||
            `${prediction.home_team} ${prediction.away_team} ${prediction.competition}`
              .toLowerCase()
              .includes(query.trim().toLowerCase());

          return isUpcoming && statusMatches && trapMatches && riskMatches && confidenceMatches && queryMatches;
        })
        .sort((a, b) => {
          const dateDelta = new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime();
          return dateDelta || b.confidence.score - a.confidence.score;
        });
    },
    [highConfidence, predictions, query, referenceTime, riskOnly, status, trapOnly],
  );
  const averageConfidence =
    filtered.length > 0
      ? Math.round(filtered.reduce((total, prediction) => total + prediction.confidence.score, 0) / filtered.length)
      : 0;
  const selectionOfDay = filtered.slice(0, 5);

  return (
    <ProtectedRoute>
      <Layout>
      <section className="pageHeader premiumPageIntro">
        <h1>Prédictions</h1>
        <p>Découvrez les opportunités de paris à forte valeur identifiées par nos modèles quantitatifs.</p>
      </section>

      <section className="filters">
        <input
          aria-label="Rechercher des prédictions"
          placeholder="Rechercher une équipe..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select aria-label="Statut" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">Tous statuts</option>
          {(['FIABLE', 'MOYEN', 'À ÉVITER'] as ConfidenceStatus[]).map((item) => (
            <option key={item} value={item}>
              {formatStatusLabel(item)}
            </option>
          ))}
        </select>
        <label className="filterToggle">
          <input type="checkbox" checked={trapOnly} onChange={(event) => setTrapOnly(event.target.checked)} />
          Matchs pièges
        </label>
        <label className="filterToggle">
          <input type="checkbox" checked={riskOnly} onChange={(event) => setRiskOnly(event.target.checked)} />
          Risque
        </label>
        <label className="filterToggle">
          <input
            type="checkbox"
            checked={highConfidence}
            onChange={(event) => setHighConfidence(event.target.checked)}
          />
          Haute confiance
        </label>
      </section>

      <section className="predictionsPremiumLayout">
        <div className="predictionMetrics">
          <article className="premiumPanel metricShowcase">
            <h2>Top value picks</h2>
            <strong>{filtered.filter((prediction) => prediction.confidence.score >= 65).length}</strong>
            <span>Signaux à confiance élevée</span>
          </article>
          <article className="premiumPanel metricShowcase">
            <h2>Confiance moyenne</h2>
            <ProbabilityRing value={averageConfidence} label="Confiance" />
          </article>
          <article className="premiumPanel metricShowcase">
            <h2>Suivi live</h2>
            <strong>{filtered.length}</strong>
            <span>Matchs à venir exploitables</span>
          </article>
        </div>

        <aside className="premiumPanel dailySelectionPanel">
          <div className="panelHeading">
            <span>Sélection du jour</span>
            <b>{selectionOfDay.length} sélections</b>
          </div>
          {selectionOfDay.map((prediction) => (
            <Link className="dailyPick" href={matchHref(prediction)} key={`daily-${prediction.match_id}`}>
              <span className="signalBall">1N2</span>
              <span>
                <strong>{prediction.home_team} vs {prediction.away_team}</strong>
                <small>{formatRecommendationLabel(prediction.recommendation)}</small>
              </span>
              <em>{prediction.confidence.score}%</em>
            </Link>
          ))}
        </aside>

        <div className="premiumPanel predictionTablePanel">
          <div className="panelHeading">
            <span>Toutes les prédictions ({filtered.length})</span>
          </div>
          <div className="premiumPredictionTable">
            {filtered.length > 0 ? (
              filtered.map((prediction) => <PredictionCard prediction={prediction} key={prediction.match_id} />)
            ) : (
              <div className="emptyState">Aucune prédiction ne correspond aux filtres.</div>
            )}
          </div>
        </div>
      </section>
      </Layout>
    </ProtectedRoute>
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
      <p>{formatKickoffFr(prediction.kickoff)}</p>
      <div className="probGrid">
        <span>
          1 <strong>{prediction.probabilities.home}%</strong>
        </span>
        <span>
          N <strong>{prediction.probabilities.draw}%</strong>
        </span>
        <span>
          2 <strong>{prediction.probabilities.away}%</strong>
        </span>
      </div>
      <div className="confidenceLine confidence-bar">
        <span style={{ width: `${prediction.confidence.score}%` }} />
      </div>
      <div className="dataList compact">
        <span>
          Score probable <strong>{prediction.goals.most_likely_score ?? 'N/A'}</strong>
        </span>
        <span>
          <span className="metricHelp">Risque <InfoTooltip content="Score de risque contextuel. Plus il est élevé, plus le match est difficile à lire." /></span>
          <strong>{prediction.risk_score ?? 'N/A'}</strong>
        </span>
        <span>
          <span className="metricHelp">Écart Elo <InfoTooltip content="Écart de niveau relatif entre les deux équipes selon le système Elo." /></span>
          <strong>{prediction.features?.elo_delta ?? 'N/A'}</strong>
        </span>
      </div>
      {prediction.hybrid_engine && (
        <span className={`decisionBadge ${prediction.hybrid_engine.decision_level}`}>
          {hybridLabel(prediction.hybrid_engine.decision_label)}
        </span>
      )}
      {prediction.explainability && (
        <div className="explainabilityPreview">
          {prediction.explainability.top_positive_factors[0] && (
            <span>
              Favorable <strong>{prediction.explainability.top_positive_factors[0].label}</strong>
            </span>
          )}
          {(prediction.explainability.risk_notes[0] || prediction.explainability.top_negative_factors[0]?.label) && (
            <span>
              Prudence <strong>{prediction.explainability.risk_notes[0] ?? prediction.explainability.top_negative_factors[0]?.label}</strong>
            </span>
          )}
        </div>
      )}
      <p>{prediction.explanation[0]}</p>
      <strong>{formatRecommendationLabel(prediction.recommendation)}</strong>
    </Link>
  );
}


function hybridLabel(label: string) {
  if (label === 'signal_renforce') return 'signal renforcé';
  if (label === 'prudence_confirmee') return 'prudence';
  if (label === 'desaccord_modele') return 'désaccord modèle';
  if (label === 'eviter') return 'à éviter';
  return 'shadow indisponible';
}
