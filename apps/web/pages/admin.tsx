import { useEffect, useState } from 'react';
import Link from 'next/link';
import { InfoTooltip } from '~/components/InfoTooltip';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { buildFeatureStore, generateShadowPredictions, getAdminWorkflowStatus, getBackendHealth, getFeatureQualityReport, getFeatureStoreJobStatus, getRefreshJobStatus, getRefreshStatus, refreshData, trainCandidateModel, getModelGovernance, getAdminAlerts,

} from '~/lib/api';
import { useAuth } from '~/lib/auth';
import type { AdminWorkflowStatus, BuildFeatureStoreResponse, DatasetQualityReport, GenerateShadowPredictionsResponse, HealthResponse, MatchView, RefreshJobStatus, RefreshResponse, TrainingReport, ModelGovernanceReport, AdminAlertsReport } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

export default function AdminPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [workflowStatus, setWorkflowStatus] = useState<AdminWorkflowStatus | null>(null);
  const [refreshInfo, setRefreshInfo] = useState<RefreshResponse | null>(null);
  const [refreshJob, setRefreshJob] = useState<RefreshJobStatus | null>(null);
  const [refreshJobId, setRefreshJobId] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isBuildingFeatures, setIsBuildingFeatures] = useState(false);
  const [featureBuildInfo, setFeatureBuildInfo] = useState<BuildFeatureStoreResponse | null>(null);
  const [featureStoreJob, setFeatureStoreJob] = useState<RefreshJobStatus | null>(null);
  const [featureStoreJobId, setFeatureStoreJobId] = useState<string | null>(null);
  const [featureQuality, setFeatureQuality] = useState<DatasetQualityReport | null>(null);
  const [isTraining, setIsTraining] = useState(false);
  const [modelGovernance, setModelGovernance] = useState<ModelGovernanceReport | null>(null);
  const [adminAlerts, setAdminAlerts] = useState<AdminAlertsReport | null>(null);
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
    getFeatureQualityReport()
      .then(setFeatureQuality)
      .catch(() => setFeatureQuality(null));
    getModelGovernance()
      .then(setModelGovernance)
      .catch(() => setModelGovernance(null));
    getAdminAlerts()
      .then(setAdminAlerts)
      .catch(() => setAdminAlerts(null));
  }, []);

  useEffect(() => {
  if (!refreshJobId) {
    return undefined;
  }

  let cancelled = false;

  async function poll() {
    try {
      const job = await getRefreshJobStatus(refreshJobId ?? undefined);

      if (cancelled) return;

      setRefreshJob(job);

      if (job.status === 'success') {
        if (job.result) {
          setRefreshInfo(job.result as RefreshResponse);
        } else {
          getRefreshStatus().then(setRefreshInfo).catch(() => undefined);
        }

        setIsRefreshing(false);
        setRefreshJobId(null);

        getAdminWorkflowStatus().then(setWorkflowStatus).catch(() => undefined);
        getFeatureQualityReport().then(setFeatureQuality).catch(() => undefined);
        getModelGovernance().then(setModelGovernance).catch(() => undefined);
        getAdminAlerts().then(setAdminAlerts).catch(() => undefined);

        return;
      }

      if (job.status === 'error') {
        setError(job.error ?? 'Actualisation en erreur.');
        setIsRefreshing(false);
        setRefreshJobId(null);
      }
    } catch (error) {
      if (cancelled) return;

      setError(error instanceof Error ? error.message : "Suivi du job d'actualisation indisponible.");
      setIsRefreshing(false);
      setRefreshJobId(null);
    }
  }

  poll();
  const interval = window.setInterval(poll, 2000);

  return () => {
    cancelled = true;
    window.clearInterval(interval);
  };
}, [refreshJobId]);

useEffect(() => {
  if (!featureStoreJobId) {
    return undefined;
  }

  let cancelled = false;

  async function poll() {
    try {
      const job = await getFeatureStoreJobStatus(featureStoreJobId ?? undefined);

      if (cancelled) return;

      setFeatureStoreJob(job);

      if (job.status === 'success') {
        if (job.result) {
          setFeatureBuildInfo(job.result as BuildFeatureStoreResponse);
        }

        setIsBuildingFeatures(false);
        setFeatureStoreJobId(null);

        getAdminWorkflowStatus().then(setWorkflowStatus).catch(() => undefined);
        getFeatureQualityReport().then(setFeatureQuality).catch(() => undefined);
        getModelGovernance().then(setModelGovernance).catch(() => undefined);
        getAdminAlerts().then(setAdminAlerts).catch(() => undefined);

        return;
      }

      if (job.status === 'error') {
        setError(job.error ?? 'Construction du Feature Store en erreur.');
        setIsBuildingFeatures(false);
        setFeatureStoreJobId(null);
      }
    } catch (error) {
      if (cancelled) return;

      setError(error instanceof Error ? error.message : 'Suivi du job Feature Store indisponible.');
      setIsBuildingFeatures(false);
      setFeatureStoreJobId(null);
    }
  }

  poll();
  const interval = window.setInterval(poll, 2000);

  return () => {
    cancelled = true;
    window.clearInterval(interval);
  };
}, [featureStoreJobId]);

async function handleRefresh() {
  setIsRefreshing(true);
  setError(null);
  setRefreshJob(null);
  setRefreshJobId(null);

  try {
    const response = await refreshData();
      if (!response) {
    setError('Actualisation impossible.');
    setIsRefreshing(false);
    return;
}
    setRefreshInfo(response);

    if (response.status === 'accepted' && response.job_id) {
      setRefreshJobId(response.job_id);
      return;
    }

    if (response.status === 'error') {
      setError(response.detail ?? response.error ?? 'Actualisation impossible.');
      setIsRefreshing(false);
      return;
    }

    const [refreshStatus, workflow, quality, governance] = await Promise.all([
      getRefreshStatus().catch(() => null),
      getAdminWorkflowStatus().catch(() => null),
      getFeatureQualityReport().catch(() => null),
      getModelGovernance().catch(() => null),
    ]);

    if (refreshStatus) setRefreshInfo(refreshStatus);
    if (workflow) setWorkflowStatus(workflow);
    if (quality) setFeatureQuality(quality);
    if (governance) setModelGovernance(governance);

    setIsRefreshing(false);
  } catch (error) {
    setError(error instanceof Error ? error.message : 'Actualisation impossible.');
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
      } else if (result.status === 'blocked') {
        setError(result.reason ?? result.dataset_quality?.recommendation_reason ?? 'Entraînement bloqué pour éviter une fuite de données.');
      }
      if (result.dataset_quality) {
        setFeatureQuality(result.dataset_quality);


        getAdminWorkflowStatus().then(setWorkflowStatus).catch(() => undefined);
        getFeatureQualityReport().then(setFeatureQuality).catch(() => undefined);
        getModelGovernance().then(setModelGovernance).catch(() => undefined);
        getAdminAlerts().then(setAdminAlerts).catch(() => undefined);
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

      getAdminWorkflowStatus().then(setWorkflowStatus).catch(() => undefined);
      getModelGovernance().then(setModelGovernance).catch(() => undefined);
      getAdminAlerts().then(setAdminAlerts).catch(() => undefined);

      if (result.status === 'error') {
        setError(result.detail ?? 'Génération des prédiction shadow impossible.');
      }
    } catch {
      setError('Génération des prédictions shadow indisponible pour le moment.');
    } finally {
      setIsGeneratingShadow(false);
    }
  }

  async function handleBuildFeatureStore() {
    setIsBuildingFeatures(true);
    setError(null);
    let acceptedJob = false;

    try {
      const result = await buildFeatureStore({ limit: 500, force: false });
      setFeatureBuildInfo(result);

      if (result.status === 'error') {
        setError(result.detail ?? 'Construction du Feature Store impossible.');
      } else if (result.status === 'accepted' && result.job_id) {
        acceptedJob = true;
        setFeatureStoreJobId(result.job_id);
        setFeatureStoreJob({
          job_id: result.job_id,
          status: 'running',
          started_at: new Date().toISOString(),
          finished_at: null,
          duration_ms: null,
          result: null,
          error: null,
        });
        return;
      }
      getFeatureQualityReport().then(setFeatureQuality).catch(() => undefined);
      getAdminAlerts().then(setAdminAlerts).catch(() => undefined);
    } catch {
      setError('Construction du Feature Store indisponible pour le moment.');
    } finally {
      if (!acceptedJob) {
        setIsBuildingFeatures(false);
      }
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
            <Link className="button secondary" href="/performance#hybrid-engine">
              Moteur hybride
            </Link>
          </div>
        </section>

        <section className="card">
  <div className="cardTop">
    <div>
      <p className="eyebrow">Alertes système</p>
      <h2>Santé opérationnelle</h2>
    </div>

    <span className={`statusBadge ${adminAlerts?.overall_status ?? 'warning'}`}>
      {adminAlerts?.overall_status === 'healthy'
        ? 'Sain'
        : adminAlerts?.overall_status === 'critical'
          ? 'Critique'
          : 'Attention'}
    </span>
  </div>

  <div className="compactDataGrid four">
    <div className="metric">
      <span>Total alertes</span>
      <strong>{adminAlerts?.alerts_count ?? 0}</strong>
    </div>

    <div className="metric">
      <span>Critiques</span>
      <strong>{adminAlerts?.critical_count ?? 0}</strong>
    </div>

    <div className="metric">
      <span>Attention</span>
      <strong>{adminAlerts?.warning_count ?? 0}</strong>
    </div>

    <div className="metric">
      <span>Notifications externes</span>
      <strong>{adminAlerts?.policy.external_notifications_enabled ? 'oui' : 'non'}</strong>
    </div>
  </div>

  {adminAlerts?.next_best_action && (
    <div className="nextActionBox">
      <span>Action recommandée</span>
      <strong>{adminAlerts.next_best_action.label}</strong>
      <Link className="button secondary" href={adminAlerts.next_best_action.href}>
        Ouvrir
      </Link>
    </div>
  )}

  <div className="alertGrid">
    {(adminAlerts?.alerts ?? []).map((alert) => (
      <article className={`alertCard ${alert.level}`} key={alert.id}>
        <div className="cardTop">
          <h3>{alert.title}</h3>

          <span className={`statusBadge ${alert.level}`}>
            {alert.level === 'critical'
              ? 'Critique'
              : alert.level === 'warning'
                ? 'Attention'
                : 'Info'}
          </span>
        </div>

        <p>{alert.message}</p>

        <div className="dataList">
          <span>
            Zone <strong>{alert.area}</strong>
          </span>

          <span>
            Bloquant <strong>{alert.blocking ? 'oui' : 'non'}</strong>
          </span>
        </div>

        <p className="mutedText">{alert.recommended_action}</p>

        <Link className="button ghost" href={alert.action_href}>
          Voir l’action
        </Link>
      </article>
    ))}
  </div>
</section>

        <article className="card">
  <p className="eyebrow">Gouvernance modèle</p>
  <h2>Contrôle de promotion</h2>
  <p>
    Le modèle ML candidat ne peut pas être promu automatiquement. Toute promotion nécessite une revue manuelle.
  </p>

  <div className="dataList">
    <span>
      Niveau <strong>{modelGovernance?.promotion_readiness.level ?? 'unknown'}</strong>
    </span>
    <span>
      Score <strong>{modelGovernance?.promotion_readiness.score ?? 0}/100</strong>
    </span>
    <span>
      Blocages <strong>{modelGovernance?.promotion_readiness.blocking_reasons.length ?? 0}</strong>
    </span>
    <span>
      Production verrouillée <strong>{modelGovernance?.production_model.locked ? 'oui' : 'non'}</strong>
    </span>
    <span>
      Promotion automatique <strong>{modelGovernance?.policy.automatic_promotion ? 'oui' : 'non'}</strong>
    </span>
  </div>

  {modelGovernance?.promotion_readiness.next_actions?.[0] && (
    <div className="banner warning">{modelGovernance.promotion_readiness.next_actions[0]}</div>
  )}

  <Link className="button secondary" href="/performance#model-governance">
    Voir la gouvernance complète
  </Link>
</article>

        <section className="card workflowCard">
          <p className="eyebrow">?tat du workflow</p>
          <h2>Pipeline data et modèle</h2>
          <div className="compactDataGrid four">
            <div className="metric"><span>Données actualisées</span><strong>{workflowStatus?.refresh.last_refresh_at ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Feature Store prêt</span><strong>{workflowStatus?.feature_store.ready ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Modèle candidat entraîné</span><strong>{workflowStatus?.candidate_model.trained ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Prédictions shadow générées</span><strong>{workflowStatus?.shadow_predictions.generated ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Backtesting shadow disponible</span><strong>{workflowStatus?.shadow_backtesting.ready ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Feature set</span><strong>{workflowStatus?.feature_engineering?.feature_set_version ?? 'pre-match-advanced-v1'}</strong></div>
            <div className="metric"><span>Couverture avancee</span><strong>{workflowStatus?.feature_engineering?.advanced_feature_coverage ?? 0}%</strong></div>
            <div className="metric"><span>Prochaine étape</span><strong>{workflowStatus?.next_step ?? 'refresh_data'}</strong></div>
          </div>
        <div className="banner info">Le moteur hybride est consultatif : il ne remplace pas le modèle officiel.</div>
        </section>

        <section className="card qualityCard">
          <p className="eyebrow">Anti-leakage</p>
          <h2>
            <span className="metricHelp">
              Qualité du dataset
              <InfoTooltip content="Vérifie que les variables d'entraînement ne contiennent pas d'information disponible uniquement après le match." />
            </span>
          </h2>
          <p>Ce contrôle vérifie que les variables d'entraînement ne contiennent pas d'information post-match comme le score final ou le vainqueur.</p>
          <div className="compactDataGrid four">
            <div className="metric"><span>Lignes contrôlées</span><strong>{featureQuality?.rows_checked ?? 0}</strong></div>
            <div className="metric"><span>Training autorisé</span><strong>{featureQuality?.safe_for_training ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Recommandation</span><strong>{featureQuality?.recommendation ?? 'insufficient_data'}</strong></div>
            <div className="metric"><span>Score qualité</span><strong>{featureQuality?.average_quality_score ?? 0}/100</strong></div>
            <div className="metric"><span>Lignes bloquées</span><strong>{featureQuality?.blocked_rows ?? 0}</strong></div>
            <div className="metric"><span>Alertes</span><strong>{featureQuality?.warning_rows ?? 0}</strong></div>
            <div className="metric"><span>Mode détection</span><strong>{featureQuality?.leakage_detection_mode ?? 'strict_feature_only'}</strong></div>
            <div className="metric"><span>Features observées</span><strong>{featureQuality?.observed_feature_names?.length ?? 0}</strong></div>
            <div className="metric"><span>Feature set</span><strong>{featureQuality?.feature_set_version ?? 'pre-match-advanced-v1'}</strong></div>
            <div className="metric"><span>Couverture avancee</span><strong>{featureQuality?.advanced_feature_coverage?.coverage_percent ?? 0}%</strong></div>
          </div>
          <div className="banner info">
            `risk_score`, `trap_match_score` et `data_quality_score` sont autorisés: ce sont des métriques modèle pré-match, pas des scores finaux.
          </div>
          {(featureQuality?.leakage_features_detected?.length ?? 0) > 0 && (
            <div className="banner error leakageWarning">
              Fuites détectées: {featureQuality?.leakage_features_detected.join(', ')}
            </div>
          )}
          <Link className="textLink" href="/performance#dataset-quality">Voir le rapport qualité complet</Link>
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
          {featureStoreJob && (
            <div className="banner info">
              Statut job Feature Store: {featureStoreJob.status}
              {featureStoreJob.duration_ms ? ` Â· Durée ${featureStoreJob.duration_ms} ms` : ''}
            </div>
          )}
          {featureBuildInfo && (
            <div className="dataList">
              <span>Statut <strong>{featureBuildInfo.status}</strong></span>
              <span>Job <strong>{featureBuildInfo.job_id ?? featureStoreJob?.job_id ?? 'N/A'}</strong></span>
              <span>Stockage <strong>{featureBuildInfo.storage ?? 'mémoire'}</strong></span>
              <span>Snapshots créés <strong>{featureBuildInfo.feature_snapshots_built ?? 0}</strong></span>
              <span>Snapshots sauvegardés <strong>{featureBuildInfo.feature_snapshots_saved ?? 0}</strong></span>
              <span>Durée <strong>{featureBuildInfo.duration_ms ?? featureStoreJob?.duration_ms ?? 0} ms</strong></span>
              <span>Lignes entraînables <strong>{featureBuildInfo.training_rows_available ?? 0}</strong></span>
              <span>Couverture cible <strong>{featureBuildInfo.target_coverage ?? 0}%</strong></span>
              <span>Feature set <strong>{featureBuildInfo.feature_set_version ?? 'pre-match-advanced-v1'}</strong></span>
              <span>Couverture avancee <strong>{featureBuildInfo.advanced_feature_coverage?.coverage_percent ?? 0}%</strong></span>
            </div>
          )}
          <div className="banner info">Les nouvelles variables avancees utilisent uniquement les matchs termines avant le coup d'envoi du match cible.</div>
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
              <span className="metricHelp">Précision <InfoTooltip content="Pourcentage de résultats correctement prédits sur l'échantillon évalué." /> <strong>{trainingReport.accuracy ?? 0}%</strong></span>
              <span className="metricHelp">Log loss <InfoTooltip content="Mesure pénalisant fortement les prédictions confiantes mais incorrectes. Plus bas est meilleur." /> <strong>{trainingReport.log_loss ?? 'N/A'}</strong></span>
              <span>Brier 1X2 <strong>{trainingReport.brier_score_1x2 ?? 'N/A'}</strong></span>
              <span>Entraîné le <strong>{trainingReport.trained_at ?? 'N/A'}</strong></span>
            </div>
          )}
          {trainingReport?.status === 'blocked' && (
            <div className="banner error">
              Entraînement bloqué pour éviter une fuite de données. {trainingReport.reason ?? trainingReport.dataset_quality?.recommendation_reason}
              {' '}<Link className="textLink" href="/performance#dataset-quality">Voir le diagnostic</Link>
            </div>
          )}
          {trainingReport?.warning && <div className="banner warning">{trainingReport.warning}</div>}
          {trainingReport?.note && <div className="banner info">{trainingReport.note}</div>}
        </section>

        <section className="card shadowCard">
          <p className="eyebrow">Mode shadow ML</p>
          <h2>4. Générer les prédictions shadow</h2>
          <p>Calcule les prédictions du modèle ML candidat en parallèle du modèle officiel, sans les activer en production.</p>
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
              <span>Forcer la régénération</span>
              <input type="checkbox" checked={shadowForce} onChange={(event) => setShadowForce(event.target.checked)} />
            </label>
          </div>
          <button className="button primary" type="button" onClick={handleGenerateShadowPredictions} disabled={isGeneratingShadow || !isAdmin}>
            {isGeneratingShadow ? 'Génération...' : 'Générer les prédictions shadow'}
          </button>
          {shadowResult && (
            <div className="dataList">
              <span>Vue <strong>{shadowResult.view ?? shadowView}</strong></span>
              <span>Générées <strong>{shadowResult.shadow_predictions_generated ?? 0}</strong></span>
              <span>Sauvegard?es <strong>{shadowResult.shadow_predictions_saved ?? 0}</strong></span>
              <span>Disponibles <strong>{shadowResult.available_count ?? 0}</strong></span>
              <span>Désaccords <strong>{shadowResult.disagreement_count ?? 0}</strong></span>
              <span>Désaccords élevés <strong>{shadowResult.high_disagreement_count ?? 0}</strong></span>
              <span>Candidat production <strong>{shadowResult.candidate_is_production ? 'oui' : 'non'}</strong></span>
            </div>
          )}
          {shadowResult?.note && <div className="banner info">{shadowResult.note}</div>}
          <p>Après génération des prédictions shadow, consultez le backtesting shadow pour mesurer les désaccords et la qualité du candidat ML.</p>
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
            <span>
              Compétitions configurées <strong>{refreshInfo?.configured_competitions?.join(', ') || 'FL1, CL'}</strong>
            </span>
          </div>
          {(refreshInfo?.competition_warnings?.length ?? 0) > 0 && (
            <div className="banner warning">
              {refreshInfo?.competition_warnings?.join(' ')}
            </div>
          )}
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

