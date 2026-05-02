import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useState } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getPredictions } from '~/lib/api';
import { isAvoidStatus, matchHref, statusClass, type ConfidenceStatus, type Prediction } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type PredictionsProps = {
  predictions: Prediction[];
};

export const getStaticProps: GetStaticProps<PredictionsProps> = async () => ({
  props: { predictions: await getPredictions() },
  revalidate: 120,
});

export default function PredictionsPage({ predictions }: PredictionsProps) {
  const router = useRouter();
  const [status, setStatus] = useState('');
  const [trapOnly, setTrapOnly] = useState(false);
  const [riskOnly, setRiskOnly] = useState(false);
  const [highConfidence, setHighConfidence] = useState(false);
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (typeof router.query.status === 'string') {
      setStatus(router.query.status === 'avoid' ? 'A EVITER' : router.query.status);
    }

    setTrapOnly(router.query.trap === 'true');
  }, [router.query.status, router.query.trap]);

  const filtered = useMemo(
    () =>
      predictions
        .filter((prediction) => {
          const statusMatches =
            !status ||
            prediction.confidence.status === status ||
            (status === 'A EVITER' && isAvoidStatus(prediction.confidence.status));
          const trapMatches = !trapOnly || prediction.flags.trap_match;
          const riskMatches = !riskOnly || prediction.flags.risk;
          const confidenceMatches = !highConfidence || prediction.confidence.score >= 70;
          const queryMatches =
            !query.trim() ||
            `${prediction.home_team} ${prediction.away_team} ${prediction.competition}`
              .toLowerCase()
              .includes(query.trim().toLowerCase());

          return statusMatches && trapMatches && riskMatches && confidenceMatches && queryMatches;
        })
        .sort((a, b) => b.confidence.score - a.confidence.score),
    [highConfidence, predictions, query, riskOnly, status, trapOnly],
  );

  return (
    <ProtectedRoute>
      <Layout>
      <section className="pageHeader">
        <p className="eyebrow">Catalogue FootIQ</p>
        <h1>Predictions</h1>
        <p>{predictions.length} analyses probabilistes disponibles.</p>
      </section>

      <section className="filters">
        <input
          aria-label="Search predictions"
          placeholder="Rechercher une equipe..."
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select aria-label="Status" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">Tous statuts</option>
          {(['FIABLE', 'MOYEN', 'A EVITER'] as ConfidenceStatus[]).map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <label className="filterToggle">
          <input type="checkbox" checked={trapOnly} onChange={(event) => setTrapOnly(event.target.checked)} />
          Matchs pieges
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

      <section className="grid three">
        {filtered.length > 0 ? (
          filtered.map((prediction) => <PredictionCard prediction={prediction} key={prediction.match_id} />)
        ) : (
          <div className="emptyState">Aucune prediction ne correspond aux filtres.</div>
        )}
      </section>
      </Layout>
    </ProtectedRoute>
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
          Model <strong>{prediction.model_version ?? 'elo-poisson-v1'}</strong>
        </span>
        <span>
          Score <strong>{prediction.goals.most_likely_score ?? 'N/A'}</strong>
        </span>
        <span>
          Risk <strong>{prediction.risk_score ?? 'N/A'}</strong>
        </span>
        <span>
          Elo delta <strong>{prediction.features?.elo_delta ?? 'N/A'}</strong>
        </span>
      </div>
      <p>{prediction.explanation[0]}</p>
    </Link>
  );
}
