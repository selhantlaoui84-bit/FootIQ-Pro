import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getBackendHealth, getRefreshStatus, refreshData, trainCandidateModel } from '~/lib/api';
import { useAuth } from '~/lib/auth';
import type { HealthResponse, RefreshResponse, TrainingReport } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

export default function AdminPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [refreshInfo, setRefreshInfo] = useState<RefreshResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isTraining, setIsTraining] = useState(false);
  const [modelType, setModelType] = useState('random_forest');
  const [trainingLimit, setTrainingLimit] = useState(5000);
  const [trainingReport, setTrainingReport] = useState<TrainingReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { user, isAdmin } = useAuth();

  useEffect(() => {
    getBackendHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
    getRefreshStatus()
      .then(setRefreshInfo)
      .catch(() => setRefreshInfo(null));
  }, []);

  async function handleRefresh() {
    setIsRefreshing(true);
    setError(null);


    try {
      const result = await refreshData();

      if (!result) {
        setError('Refresh unavailable. Check the admin key or backend.');
        return;
      }

      if (result.status === 'error') {
        setError(result.detail ?? result.error ?? 'Refresh refused.');
        return;
      }

      setRefreshInfo(result);
    } catch {
      setError('Refresh impossible pour le moment.');
    } finally {
      setIsRefreshing(false);
    }
  }

  async function handleTrainCandidate() {
    setIsTraining(true);
    setError(null);

    try {
      const result = await trainCandidateModel({ modelType, limit: trainingLimit });
      setTrainingReport(result);

      if (result.status === 'error') {
        setError(result.detail ?? 'Candidate training failed.');
      }
    } catch {
      setError('Candidate training unavailable for the moment.');
    } finally {
      setIsTraining(false);
    }
  }

  return (
    <ProtectedRoute requireAdmin>
      <Layout>
        <section className="pageHeader">
          <p className="eyebrow">Administration MVP</p>
          <h1>Admin</h1>
          <p>Controle du backend, du refresh football-data.org et de la source active.</p>
          <div className="roleStrip">
            <span className="userBadge">{user?.email ?? 'Unknown user'}</span>
            <span className={`roleBadge ${isAdmin ? 'admin' : ''}`}>{isAdmin ? 'Admin' : 'User'}</span>
          </div>
          <div className="quickActions">
            <Link className="button secondary" href="/dashboard">
              Dashboard
            </Link>
            <Link className="button secondary" href="/matches">
              Matches
            </Link>
            <Link className="button secondary" href="/predictions">
              Predictions
            </Link>
            <Link className="button secondary" href="/performance#model-comparison">
              Backtesting
            </Link>
            <Link className="button secondary" href="/performance#model-comparison">
              Model comparison
            </Link>
            <Link className="button secondary" href="/performance#feature-store">
              Feature Store
            </Link>
          </div>
        </section>

        <section className="sectionSplit">
          <article className="card">
            <h2>Backend health</h2>
            <div className="dataList">
              <span>
                Status <strong>{health?.status ?? (health?.ok ? 'ok' : 'indisponible')}</strong>
              </span>
              <span>
                API URL <strong>{process.env.NEXT_PUBLIC_API_URL ?? 'non configuree'}</strong>
              </span>
            </div>
          </article>

          <article className="card accent">
            <h2>Refresh data</h2>
            <p>Import Ligue 1 et Champions League, avec fallback mock automatique.</p>
            {!isAdmin && <div className="banner error">Admin access required.</div>}
            <button
              className="button primary"
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing || !isAdmin}
            >
              {isRefreshing ? 'Refresh en cours...' : 'Refresh data'}
            </button>
          </article>
        </section>

        {error && <section className="banner error">{error}</section>}

        <section className="card">
          <p className="eyebrow">Machine learning candidate</p>
          <h2>Train Candidate ML Model</h2>
          <p>This trains an offline candidate from the Feature Store. It does not replace production predictions.</p>
          <div className="formGrid">
            <label className="formField">
              <span>Model type</span>
              <select value={modelType} onChange={(event) => setModelType(event.target.value)}>
                <option value="random_forest">random_forest</option>
                <option value="xgboost">xgboost</option>
              </select>
            </label>
            <label className="formField">
              <span>Training row limit</span>
              <input
                min={1}
                max={10000}
                type="number"
                value={trainingLimit}
                onChange={(event) => setTrainingLimit(Number(event.target.value))}
              />
            </label>
          </div>
          <button
            className="button primary"
            type="button"
            onClick={handleTrainCandidate}
            disabled={isTraining || !isAdmin}
          >
            {isTraining ? 'Training...' : 'Train model'}
          </button>

          {trainingReport && (
            <div className="dataList">
              <span>Status <strong>{trainingReport.status}</strong></span>
              <span>Model type <strong>{trainingReport.model_type ?? 'random_forest'}</strong></span>
              <span>Fallback used <strong>{trainingReport.fallback_used ? 'yes' : 'no'}</strong></span>
              <span>Rows used <strong>{trainingReport.rows_used ?? 0}</strong></span>
              <span>Train rows <strong>{trainingReport.train_rows ?? 0}</strong></span>
              <span>Test rows <strong>{trainingReport.test_rows ?? 0}</strong></span>
              <span>Accuracy <strong>{trainingReport.accuracy ?? 0}%</strong></span>
              <span>Log loss <strong>{trainingReport.log_loss ?? 'N/A'}</strong></span>
              <span>Brier 1X2 <strong>{trainingReport.brier_score_1x2 ?? 'N/A'}</strong></span>
              <span>Trained at <strong>{trainingReport.trained_at ?? 'N/A'}</strong></span>
            </div>
          )}
          {trainingReport?.note && <div className="banner info">{trainingReport.note}</div>}
        </section>

        <section className="card">
          <h2>Dernier refresh</h2>
          <div className="dataList">
            <span>
              Status <strong>{refreshInfo?.status ?? 'unknown'}</strong>
            </span>
            <span>
              Source <strong>{refreshInfo?.source ?? 'mock'}</strong>
            </span>
            <span>
              Storage <strong>{refreshInfo?.storage ?? 'memory'}</strong>
            </span>
            <span>
              Matches imported <strong>{refreshInfo?.matches_imported ?? 0}</strong>
            </span>
            <span>
              Teams imported <strong>{refreshInfo?.teams_imported ?? 0}</strong>
            </span>
            <span>
              Predictions imported <strong>{refreshInfo?.predictions_imported ?? 0}</strong>
            </span>
            <span>
              Snapshots saved <strong>{refreshInfo?.snapshots_saved ?? 0}</strong>
            </span>
            <span>
              Feature snapshots <strong>{refreshInfo?.feature_snapshots_saved ?? 0}</strong>
            </span>
            <span>
              Training rows <strong>{refreshInfo?.training_rows_available ?? 0}</strong>
            </span>
            <span>
              Last refresh <strong>{refreshInfo?.last_refresh_at ?? 'N/A'}</strong>
            </span>
          </div>
          <div className="banner info">
            Backtesting and feature snapshots update automatically from finished matches with available scores. See the model report on{' '}
            <Link className="textLink" href="/performance#feature-store">
              Performance
            </Link>
            .
          </div>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}

