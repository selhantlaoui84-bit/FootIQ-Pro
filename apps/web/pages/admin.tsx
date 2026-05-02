import { useEffect, useState } from 'react';
import Link from 'next/link';
import { InfoTooltip } from '~/components/InfoTooltip';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { buildFeatureStore, generateShadowPredictions, getAdminWorkflowStatus, getBackendHealth, getRefreshStatus, refreshData, trainCandidateModel } from '~/lib/api';
import { useAuth } from '~/lib/auth';
import type { AdminWorkflowStatus, BuildFeatureStoreResponse, GenerateShadowPredictionsResponse, HealthResponse, MatchView, RefreshResponse, TrainingReport } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

export default function AdminPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [workflowStatus, setWorkflowStatus] = useState<AdminWorkflowStatus | null>(null);
  const [refreshInfo, setRefreshInfo] = useState<RefreshResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isBuildingFeatures, setIsBuildingFeatures] = useState(false);
  const [featureBuildInfo, setFeatureBuildInfo] = useState<BuildFeatureStoreResponse | null>(null);
  const [isTraining, setIsTraining] = useState(false);
  const [modelType, setModelType] = useState('random_forest');
  const [trainingLimit, setTrainingLimit] = useState(5000);
  const [trainingReport, setTrainingReport] = useState<TrainingReport | null>(null);
  const [isGeneratingShadow, setIsGeneratingShadow] = useState(false);
  const [shadowLimit, setShadowLimit] = useState(500);
  const [shadowForce, setShadowForce] = useState(false);
  const [shadowView, setShadowView] = useState<MatchView>('upcoming');
  const [shadowResult, setShadowResult] = useState<GenerateShadowPredictionsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { user, isAdmin } = useAuth();

  useEffect(() => {
    getBackendHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
    getRefreshStatus()
      .then(setRefreshInfo)
      .catch(() => setRefreshInfo(null));
    getAdminWorkflowStatus()
      .then(setWorkflowStatus)
      .catch(() => setWorkflowStatus(null));
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
      getAdminWorkflowStatus().then(setWorkflowStatus).catch(() => undefined);
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

  async function handleGenerateShadowPredictions() {
    setIsGeneratingShadow(true);
    setError(null);

    try {
      const result = await generateShadowPredictions({ limit: shadowLimit, force: shadowForce, view: shadowView });
      setShadowResult(result);

      if (result.status === 'error') {
        setError(result.detail ?? 'G?n?ration des pr?dictions shadow impossible.');
      }
    } catch {
      setError('G?n?ration des pr?dictions shadow indisponible pour le moment.');
    } finally {
      setIsGeneratingShadow(false);
    }
  }

  async function handleBuildFeatureStore() {
    setIsBuildingFeatures(true);
    setError(null);

    try {
      const result = await buildFeatureStore({ limit: 500, force: false });
      setFeatureBuildInfo(result);

      if (result.status === 'error') {
        setError(result.detail ?? 'Construction du Feature Store impossible.');
      }
    } catch {
      setError('Construction du Feature Store indisponible pour le moment.');
    } finally {
      setIsBuildingFeatures(false);
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
            <span className="userBadge">{user?.email ?? 'Utilisateur inconnu'}</span>
            <span className={`roleBadge ${isAdmin ? 'admin' : ''}`}>{isAdmin ? 'Admin' : 'User'}</span>
          </div>
          <div className="quickActions">
            <Link className="button secondary" href="/dashboard">
              Tableau de bord
            </Link>
            <Link className="button secondary" href="/matches">
              Matchs
            </Link>
            <Link className="button secondary" href="/predictions">
              Prédictions
            </Link>
            <Link className="button secondary" href="/performance#model-comparison">
              Backtesting
            </Link>
            <Link className="button secondary" href="/performance#model-comparison">
              Comparaison modèles
            </Link>
            <Link className="button secondary" href="/performance#feature-store">
              Feature Store
            </Link>
          </div>
        </section>

        <section className="card workflowCard">
          <p className="eyebrow">?tat du workflow</p>
          <h2>Pipeline data et mod?le</h2>
          <div className="compactDataGrid four">
            <div className="metric"><span>Donn?es actualis?es</span><strong>{workflowStatus?.refresh.last_refresh_at ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Feature Store pr?t</span><strong>{workflowStatus?.feature_store.ready ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Mod?le candidat entra?n?</span><strong>{workflowStatus?.candidate_model.trained ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Pr?dictions shadow g?n?r?es</span><strong>{workflowStatus?.shadow_predictions.generated ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Backtesting shadow disponible</span><strong>{workflowStatus?.shadow_backtesting.ready ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Prochaine ?tape</span><strong>{workflowStatus?.next_step ?? 'refresh_data'}</strong></div>
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
            <h2>1. Actualiser les données</h2>
            <p>Cette action actualise uniquement les donn?es et les pr?dictions officielles. Le Feature Store, le ML et le shadow se lancent ensuite s?par?ment.</p>
            {!isAdmin && <div className="banner error">Accès admin requis.</div>}
            <button
              className="button primary"
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing || !isAdmin}
            >
              {isRefreshing ? 'Actualisation en cours...' : 'Actualiser les données'}
            </button>
          </article>
        </section>

        {error && <section className="banner error">{error}</section>}

        <section className="card">
          <p className="eyebrow">Feature Store</p>
          <h2>
            <span className="metricHelp">
              2. Construire le Feature Store
              <InfoTooltip content="Base de données des variables utilisées par les modèles pour apprendre et comparer les performances." />
            </span>
          </h2>
          <p>Gèle les variables modèle par match pour préparer l'entraînement supervisé.</p>
          <button
            className="button secondary"
            type="button"
            onClick={handleBuildFeatureStore}
            disabled={isBuildingFeatures || !isAdmin}
          >
            {isBuildingFeatures ? 'Construction...' : 'Construire le Feature Store'}
          </button>
          {featureBuildInfo && (
            <div className="dataList">
              <span>Statut <strong>{featureBuildInfo.status}</strong></span>
              <span>Stockage <strong>{featureBuildInfo.storage ?? 'mémoire'}</strong></span>
              <span>Snapshots créés <strong>{featureBuildInfo.feature_snapshots_built ?? 0}</strong></span>
              <span>Snapshots sauvegardés <strong>{featureBuildInfo.feature_snapshots_saved ?? 0}</strong></span>
              <span>Lignes entraînables <strong>{featureBuildInfo.training_rows_available ?? 0}</strong></span>
              <span>Couverture cible <strong>{featureBuildInfo.target_coverage ?? 0}%</strong></span>
            </div>
          )}
        </section>

        <section className="card">
          <p className="eyebrow">Modèle supervisé candidat</p>
          <h2>
            <span className="metricHelp">
              3. Entraîner le modèle candidat
              <InfoTooltip content="Modèle supervisé entraîné sur l'historique, actuellement en observation et non utilisé en production." />
            </span>
          </h2>
          <p>Entraîne un candidat hors production depuis le Feature Store. Le modèle Elo/Poisson reste actif.</p>
          <div className="formGrid">
            <label className="formField">
              <span>Type de modèle</span>
              <select value={modelType} onChange={(event) => setModelType(event.target.value)}>
                <option value="random_forest">random_forest</option>
                <option value="xgboost">xgboost</option>
              </select>
            </label>
            <label className="formField">
              <span>Limite de lignes</span>
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
            {isTraining ? 'Entraînement...' : 'Entraîner le modèle'}
          </button>

          {trainingReport && (
            <div className="dataList">
              <span>Statut <strong>{trainingReport.status}</strong></span>
              <span>Type de modèle <strong>{trainingReport.model_type ?? 'random_forest'}</strong></span>
              <span>Fallback utilisé <strong>{trainingReport.fallback_used ? 'oui' : 'non'}</strong></span>
              <span>Lignes utilisées <strong>{trainingReport.rows_used ?? 0}</strong></span>
              <span>Lignes train <strong>{trainingReport.train_rows ?? 0}</strong></span>
              <span>Lignes test <strong>{trainingReport.test_rows ?? 0}</strong></span>
              <span className="metricHelp">Accuracy <InfoTooltip content="Pourcentage de résultats correctement prédits sur l’échantillon évalué." /> <strong>{trainingReport.accuracy ?? 0}%</strong></span>
              <span className="metricHelp">Log loss <InfoTooltip content="Mesure pénalisant fortement les prédictions confiantes mais incorrectes. Plus bas est meilleur." /> <strong>{trainingReport.log_loss ?? 'N/A'}</strong></span>
              <span>Brier 1X2 <strong>{trainingReport.brier_score_1x2 ?? 'N/A'}</strong></span>
              <span>Entraîné le <strong>{trainingReport.trained_at ?? 'N/A'}</strong></span>
            </div>
          )}
          {trainingReport?.note && <div className="banner info">{trainingReport.note}</div>}
        </section>

        <section className="card shadowCard">
          <p className="eyebrow">Mode shadow ML</p>
          <h2>4. G?n?rer les pr?dictions shadow</h2>
          <p>Calcule les pr?dictions du mod?le ML candidat en parall?le du mod?le officiel, sans les activer en production.</p>
          <div className="formGrid">
            <label className="formField">
              <span>Limite</span>
              <input min={1} max={2000} type="number" value={shadowLimit} onChange={(event) => setShadowLimit(Number(event.target.value))} />
            </label>
            <label className="formField">
              <span>Vue</span>
              <select value={shadowView} onChange={(event) => setShadowView(event.target.value as MatchView)}>
                <option value="upcoming">? venir</option>
                <option value="history">Historique</option>
                <option value="all">Tous</option>
              </select>
            </label>
            <label className="formField checkboxField">
              <span>Forcer la r?g?n?ration</span>
              <input type="checkbox" checked={shadowForce} onChange={(event) => setShadowForce(event.target.checked)} />
            </label>
          </div>
          <button className="button primary" type="button" onClick={handleGenerateShadowPredictions} disabled={isGeneratingShadow || !isAdmin}>
            {isGeneratingShadow ? 'G?n?ration...' : 'G?n?rer les pr?dictions shadow'}
          </button>
          {shadowResult && (
            <div className="dataList">
              <span>Vue <strong>{shadowResult.view ?? shadowView}</strong></span>
              <span>G?n?r?es <strong>{shadowResult.shadow_predictions_generated ?? 0}</strong></span>
              <span>Sauvegard?es <strong>{shadowResult.shadow_predictions_saved ?? 0}</strong></span>
              <span>Disponibles <strong>{shadowResult.available_count ?? 0}</strong></span>
              <span>D?saccords <strong>{shadowResult.disagreement_count ?? 0}</strong></span>
              <span>D?saccords ?lev?s <strong>{shadowResult.high_disagreement_count ?? 0}</strong></span>
              <span>Candidat production <strong>{shadowResult.candidate_is_production ? 'oui' : 'non'}</strong></span>
            </div>
          )}
          {shadowResult?.note && <div className="banner info">{shadowResult.note}</div>}
          <p>Apr?s g?n?ration des pr?dictions shadow, consultez le backtesting shadow pour mesurer les d?saccords et la qualit? du candidat ML.</p>
          <Link className="textLink" href="/performance#shadow-backtesting">Voir le backtesting shadow</Link>
        </section>

        <section className="card">
          <h2>Dernier refresh</h2>
          <div className="dataList">
            <span>
              Statut <strong>{refreshInfo?.status ?? 'inconnu'}</strong>
            </span>
            <span>
              Source <strong>{refreshInfo?.source ?? 'mock'}</strong>
            </span>
            <span>
              Stockage <strong>{refreshInfo?.storage ?? 'mémoire'}</strong>
            </span>
            <span>
              Matchs importés <strong>{refreshInfo?.matches_imported ?? 0}</strong>
            </span>
            <span>
              Équipes importées <strong>{refreshInfo?.teams_imported ?? 0}</strong>
            </span>
            <span>
              Prédictions importées <strong>{refreshInfo?.predictions_imported ?? 0}</strong>
            </span>
            <span>
              Snapshots sauvegardés <strong>{refreshInfo?.snapshots_saved ?? 0}</strong>
            </span>
            <span>
              Snapshots features <strong>{refreshInfo?.feature_snapshots_saved ?? 0}</strong>
            </span>
            <span>
              Lignes entraînables <strong>{refreshInfo?.training_rows_available ?? 0}</strong>
            </span>
            <span>
              Dernière actualisation <strong>{refreshInfo?.last_refresh_at ?? 'N/A'}</strong>
            </span>
          </div>
          <div className="banner info">
            Le backtesting et les snapshots se mettent à jour depuis les matchs terminés avec score disponible. Voir le rapport modèle dans{' '}
            <Link className="textLink" href="/performance#shadow-ml">
              Performance
            </Link>
            .
          </div>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}


