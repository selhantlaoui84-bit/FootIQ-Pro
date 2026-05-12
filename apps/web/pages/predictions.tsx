import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import { InfoTooltip } from '~/components/InfoTooltip';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { TeamIdentity } from '~/components/TeamIdentity';
import { UpgradePrompt } from '~/components/UpgradePrompt';
import { ProbabilityRing } from '~/components/ui';
import { getAssistantPredictions, getMySubscription, getPredictions, getValueBets } from '~/lib/api';
import { canViewValueBets } from '~/lib/feature-access';
import { isAvoidStatus, matchHref, predictions as mockPredictions, statusClass, type BettingAssistantItem, type ConfidenceStatus, type Prediction, type SubscriptionResponse, type ValueBetItem } from '~/lib/mock-data';
import { resolveMatchTeamLogo } from '~/lib/team-logos';
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
  const [valueOnly, setValueOnly] = useState(false);
  const [query, setQuery] = useState('');
  const [assistantItems, setAssistantItems] = useState<Record<string, BettingAssistantItem>>({});
  const [valueItems, setValueItems] = useState<Record<string, ValueBetItem>>({});
  const [subscription, setSubscription] = useState<SubscriptionResponse | null>(null);

  useEffect(() => {
    if (typeof router.query.status === 'string') {
      setStatus(router.query.status === 'avoid' ? 'À ÉVITER' : router.query.status);
    }

    setTrapOnly(router.query.trap === 'true');
    setValueOnly(router.query.filter === 'value');
  }, [router.query.status, router.query.trap, router.query.filter]);

  useEffect(() => {
    let cancelled = false;
    getMySubscription().then((report) => {
      if (!cancelled) setSubscription(report);
    }).catch(() => {
      if (!cancelled) setSubscription(null);
    });
    getAssistantPredictions(100)
      .then((report) => {
        if (cancelled) return;
        setAssistantItems(Object.fromEntries((report.items ?? []).map((item) => [item.match_id, item])));
      })
      .catch(() => {
        if (!cancelled) setAssistantItems({});
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getValueBets({ limit: 100, include_watchlist: true })
      .then((report) => {
        if (!cancelled) setValueItems(Object.fromEntries((report.items ?? []).map((item) => [item.match_id, item])));
      })
      .catch(() => {
        if (!cancelled) setValueItems({});
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
          const value = valueItems[prediction.match_id];
          const valueMatches = !valueOnly || ['strong_value', 'positive_value'].includes(value?.value_status ?? '');
          const confidenceMatches = !highConfidence || prediction.confidence.score >= 70;
          const queryMatches =
            !query.trim() ||
            `${prediction.home_team} ${prediction.away_team} ${prediction.competition}`
              .toLowerCase()
              .includes(query.trim().toLowerCase());

          return isUpcoming && statusMatches && trapMatches && riskMatches && valueMatches && confidenceMatches && queryMatches;
        })
        .sort((a, b) => {
          const dateDelta = new Date(a.kickoff).getTime() - new Date(b.kickoff).getTime();
          return dateDelta || b.confidence.score - a.confidence.score;
        });
    },
    [highConfidence, predictions, query, referenceTime, riskOnly, status, trapOnly, valueItems, valueOnly],
  );
  const averageConfidence =
    filtered.length > 0
      ? Math.round(filtered.reduce((total, prediction) => total + prediction.confidence.score, 0) / filtered.length)
      : 0;
  const selectionOfDay = filtered.slice(0, 5);
  const plan = subscription?.plan ?? 'free';
  const valueAccess = canViewValueBets(plan);
  const visiblePredictions = plan === 'free' ? filtered.slice(0, subscription?.limits?.prediction_view?.limit ?? 5) : filtered;

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
        <label className="filterToggle">
          <input type="checkbox" checked={valueOnly} onChange={(event) => setValueOnly(event.target.checked)} />
          Value Bets
        </label>
      </section>

      <section className="predictionsPremiumLayout">
        {!valueAccess && (
          <UpgradePrompt
            feature="value_bets"
            title="Aperçu Value Bets"
            description="Le plan gratuit affiche un aperçu. Passez Premium pour voir les value bets avancées, l'assistant complet et les détails EV."
          />
        )}
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
              <TeamIdentity
                teamName={prediction.home_team}
                logoUrl={resolveMatchTeamLogo(prediction, 'home')}
                size="sm"
                subtitle={formatRecommendationLabel(prediction.recommendation)}
              />
              <em>{prediction.confidence.score}%</em>
            </Link>
          ))}
        </aside>

        <div className="premiumPanel predictionTablePanel">
          <div className="panelHeading">
            <span>Toutes les prédictions ({filtered.length})</span>
          </div>
          <div className="premiumPredictionTable">
            {visiblePredictions.length > 0 ? (
              visiblePredictions.map((prediction) => <PredictionCard locked={!valueAccess} assistant={{ ...assistantItems[prediction.match_id], ...valueItems[prediction.match_id] }} prediction={prediction} key={prediction.match_id} />)
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

function PredictionCard({ prediction, assistant, locked = false }: { prediction: Prediction; assistant?: Partial<BettingAssistantItem & ValueBetItem>; locked?: boolean }) {
  const calibrationApplied = prediction.calibration?.applied === true || Boolean(prediction.calibration_version);
  const rawProbabilities = prediction.original_probabilities;

  return (
    <Link className="card matchCard clickable-card" href={matchHref(prediction)}>
      <div className="cardTop">
        <span>{formatCompetitionLabel(prediction.competition)}</span>
        <span className={`badge status-badge ${statusClass(prediction.confidence.status)}`}>
          {formatStatusLabel(prediction.confidence.status)}
        </span>
      </div>
      <div className="fixtureTeams">
        <TeamIdentity teamName={prediction.home_team} logoUrl={resolveMatchTeamLogo(prediction, 'home')} size="sm" />
        <span className="versus">vs</span>
        <TeamIdentity
          align="right"
          className="away"
          teamName={prediction.away_team}
          logoUrl={resolveMatchTeamLogo(prediction, 'away')}
          size="sm"
        />
      </div>
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
      {calibrationApplied && (
        <div className="banner info">
          Probabilités calibrées
          {prediction.calibration_version ? ` (${prediction.calibration_version})` : ''}
          {rawProbabilities ? ` - brut 1/N/2 : ${rawProbabilities.home}/${rawProbabilities.draw}/${rawProbabilities.away}%` : ''}
        </div>
      )}
      <div className="dataList compact">
        <span>
          Statut value <strong>{valueLabel(assistant?.value_status)}</strong>
        </span>
        <span>
          Score opportunité <strong>{assistant?.opportunity_score != null ? `${assistant.opportunity_score}/100` : 'Données insuffisantes'}</strong>
        </span>
        <span>
          Niveau <strong>{assistant?.opportunity_level ?? 'Données insuffisantes'}</strong>
        </span>
        <span>
          Assistant <strong>{assistant?.recommendation_label ?? 'Données insuffisantes'}</strong>
        </span>
        <span>
          Cote <strong>{assistant?.odds ? assistant.odds.toFixed(2) : 'Cote réelle non disponible'}</strong>
        </span>
        <span>
          Probabilité bookmaker <strong>{assistant?.implied_probability != null ? `${Math.round(assistant.implied_probability * 100)}%` : 'Non disponible'}</strong>
        </span>
        <span>
          Probabilité modèle <strong>{assistant?.used_probability != null ? `${Math.round(assistant.used_probability * 100)}%` : `${prediction.confidence.score}%`}</strong>
        </span>
        <span>
          Edge <strong>{assistant?.edge != null ? `${Math.round(assistant.edge * 1000) / 10}%` : 'Non calculable'}</strong>
        </span>
        <span>
          Expected value <strong>{assistant?.expected_value != null ? assistant.expected_value.toFixed(3) : 'Non calculable'}</strong>
        </span>
        <span>
          Cote juste <strong>{assistant?.fair_odds != null ? assistant.fair_odds.toFixed(2) : 'Données insuffisantes'}</strong>
        </span>
        <span>
          Cote minimum value <strong>{assistant?.minimum_value_odds != null ? assistant.minimum_value_odds.toFixed(2) : 'Données insuffisantes'}</strong>
        </span>
        <span>
          Value ajustée risque <strong>{assistant?.risk_adjusted_value != null ? assistant.risk_adjusted_value.toFixed(3) : 'Non calculable'}</strong>
        </span>
        <span>
          Risque assistant <strong>{assistant?.risk_level ?? 'unknown'}</strong>
        </span>
      </div>
      {locked && <div className="banner warning">UpgradePrompt : détails value bet avancés réservés Premium.</div>}
      {(assistant?.warnings ?? []).length > 0 && <div className="banner warning">{assistant?.warnings?.join(' ')}</div>}
      <div className="banner info">
        {assistant?.recommendation_reason ?? 'Assistant FootIQ : cote réelle non disponible ou données insuffisantes. Les résultats restent incertains.'}
      </div>
      <div className="cardActions">
        <span className="button secondary">Ajouter à mes paris</span>
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

function valueLabel(status?: string | null) {
  if (status === 'strong_value') return 'Value forte';
  if (status === 'positive_value') return 'Value positive';
  if (status === 'fair_price') return 'Prix correct';
  if (status === 'no_value') return 'Pas de value';
  if (status === 'avoid') return 'À éviter';
  if (status === 'no_real_odds') return 'Cote réelle non disponible';
  if (status === 'insufficient_data') return 'Données insuffisantes';
  return 'Données insuffisantes';
}
