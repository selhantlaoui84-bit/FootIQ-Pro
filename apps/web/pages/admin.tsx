import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import {
  buildFeatureStore,
  generateShadowPredictions,
  getAdminAlerts,
  getAdminDiagnostics,
  getAdminWorkflowStatus,
  getBackendHealth,
  getDashboardSummary,
  getFeatureQualityReport,
  getFeatureSummary,
  getFeatureStoreJobStatus,
  getModelGovernance,
  getRefreshJobStatus,
  getRefreshStatus,
  refreshData,
  resetStaleJobs,
  trainCandidateModel,
} from '~/lib/api';
import { useAuth } from '~/lib/auth';
import type {
  AdminAlertsReport,
  AdminDiagnosticsResponse,
  AdminWorkflowStatus,
  BuildFeatureStoreResponse,
  DashboardSummary,
  DatasetQualityReport,
  FeatureSummary,
  GenerateShadowPredictionsResponse,
  HealthResponse,
  MatchView,
  ModelGovernanceReport,
  RefreshJobStatus,
  RefreshResponse,
  TrainingReport,
} from '~/lib/mock-data';
import { Layout } from '~/src-layout';

function valueBadge(value?: string | null) {
  const normalized = (value ?? '').toLowerCase();

  if (normalized === 'mock') return 'statusBadge warning';
  if (normalized === 'memory' || normalized === 'mÃ©moire') return 'statusBadge critical';
  if (normalized === 'postgresql' || normalized === 'football-data.org') return 'statusBadge healthy';

  return 'statusBadge info';
}

function formatStorage(value?: string | null) {
  return value === 'memory' ? 'mÃ©moire' : value || 'inconnu';
}

function diagnosticError(diagnostics: AdminDiagnosticsResponse | null) {
  return diagnostics?.backendHealth.status === 'error'
    ? diagnostics.backendHealth.error
    : diagnostics?.refreshStatus.status === 'error'
      ? diagnostics.refreshStatus.error
      : null;
}

function isProbablyStale(job?: RefreshJobStatus | null) {
  if (!job || job.status !== 'running' || !job.started_at) return false;
  return Date.now() - new Date(job.started_at).getTime() > 5 * 60 * 1000;
}

export default function AdminPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [workflowStatus, setWorkflowStatus] = useState<AdminWorkflowStatus | null>(null);
  const [refreshInfo, setRefreshInfo] = useState<RefreshResponse | null>(null);
  const [refreshJob, setRefreshJob] = useState<RefreshJobStatus | null>(null);
  const [refreshJobId, setRefreshJobId] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isTestingConfig, setIsTestingConfig] = useState(false);
  const [diagnostics, setDiagnostics] = useState<AdminDiagnosticsResponse | null>(null);
  const [dashboardSummary, setDashboardSummary] = useState<DashboardSummary | null>(null);
  const [featureSummary, setFeatureSummary] = useState<FeatureSummary | null>(null);
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

  const backendConnected = health?.status === 'ok' || health?.status === 'healthy';
  const configError = useMemo(() => diagnosticError(diagnostics), [diagnostics]);
  const stableRefreshInfo = refreshInfo?.stable_refresh_status
    ? { ...refreshInfo.stable_refresh_status, status: refreshInfo.stable_refresh_status.status ?? refreshInfo.status }
    : refreshInfo;
  const currentRefreshJob = refreshJob ?? refreshInfo?.current_job ?? workflowStatus?.latest_refresh_job;
  const effectiveFeatureSnapshots =
    featureSummary?.snapshots_count ??
    workflowStatus?.feature_store.snapshots_count ??
    dashboardSummary?.feature_snapshots_count ??
    0;
  const effectiveTrainingRows =
    featureSummary?.with_target_count ??
    workflowStatus?.feature_store.training_rows_available ??
    dashboardSummary?.training_rows_available ??
    0;
  const effectiveFeatureStoreReady =
    effectiveFeatureSnapshots > 0 || effectiveTrainingRows > 0 || workflowStatus?.feature_store.ready === true;
  const resolvedRefreshStorage =
    featureSummary?.storage === 'postgresql'
      ? 'postgresql'
      : stableRefreshInfo?.storage === 'postgresql'
        ? 'postgresql'
        : workflowStatus?.refresh.storage === 'postgresql'
          ? 'postgresql'
          : stableRefreshInfo?.storage ?? workflowStatus?.refresh.storage;
  const displayedNextStep =
    effectiveFeatureStoreReady && (!workflowStatus?.next_step || workflowStatus.next_step === 'refresh_data')
      ? 'train_candidate_model'
      : workflowStatus?.next_step ?? 'refresh_data';
  const resolvedRefreshSource = workflowStatus?.refresh.source ?? stableRefreshInfo?.source ?? 'mock';
  const dataImported =
    workflowStatus?.refresh.data_imported ??
    ((workflowStatus?.refresh.storage === 'postgresql' && (workflowStatus?.refresh.matches_imported ?? 0) > 0) ||
      (stableRefreshInfo?.storage === 'postgresql' && (stableRefreshInfo?.matches_imported ?? 0) > 0));
  const candidateModelTrained = workflowStatus?.candidate_model.trained ?? false;
  const refreshJobStale = isProbablyStale(currentRefreshJob);
  const featureStoreJobStale = isProbablyStale(featureStoreJob) || isProbablyStale(workflowStatus?.latest_feature_store_job);

  async function reloadAdminState() {
    const [healthResult, refreshStatus, workflow, featureStore, quality, governance, alerts, dashboard] = await Promise.all([
      getBackendHealth().catch(() => null),
      getRefreshStatus().catch(() => null),
      getAdminWorkflowStatus().catch(() => null),
      getFeatureSummary().catch(() => null),
      getFeatureQualityReport().catch(() => null),
      getModelGovernance().catch(() => null),
      getAdminAlerts().catch(() => null),
      getDashboardSummary().catch(() => null),
    ]);

    setHealth(healthResult);
    if (refreshStatus) {
      setRefreshInfo(refreshStatus);
      if (refreshStatus.current_job?.status === 'running') {
        setRefreshJob(refreshStatus.current_job);
      }
    }
    if (workflow) setWorkflowStatus(workflow);
    if (featureStore) setFeatureSummary(featureStore);
    if (quality) setFeatureQuality(quality);
    if (governance) setModelGovernance(governance);
    if (alerts) setAdminAlerts(alerts);
    if (dashboard) setDashboardSummary(dashboard);
  }

  async function handleDiagnostics() {
    setIsTestingConfig(true);
    setError(null);

    try {
      const result = await getAdminDiagnostics();
      setDiagnostics(result);

      if (result?.refreshStatus.status === 'ok' && result.refreshStatus.data) {
        setRefreshInfo(result.refreshStatus.data as RefreshResponse);
      }

      const message = diagnosticError(result);
      if (message) setError(message);
    } finally {
      setIsTestingConfig(false);
    }
  }

  async function handleReloadState() {
    setError(null);
    await Promise.all([reloadAdminState(), handleDiagnostics()]);
  }

  async function handleResetStaleJobs() {
    setError(null);
    const result = await resetStaleJobs({ force: true });
    if (result.status === 'error') {
      setError(result.detail ?? 'RÃ©initialisation des jobs bloquÃ©s impossible.');
      return;
    }
    await handleReloadState();
  }

  useEffect(() => {
    void reloadAdminState();
    void handleDiagnostics();
  }, []);

  useEffect(() => {
    if (!refreshJobId) return undefined;

    let cancelled = false;

    async function poll() {
      try {
        const job = await getRefreshJobStatus(refreshJobId ?? undefined);
        if (cancelled) return;

        setRefreshJob(job);

        if (job.status === 'success') {
          if (job.result) setRefreshInfo(job.result as RefreshResponse);
          setIsRefreshing(false);
          setRefreshJobId(null);
          await reloadAdminState();
          await handleDiagnostics();
          return;
        }

        if (job.status === 'error') {
          setError(job.error ?? 'Actualisation en erreur.');
          setIsRefreshing(false);
          setRefreshJobId(null);
          await reloadAdminState();
        }
      } catch (pollError) {
        if (cancelled) return;
        setError(pollError instanceof Error ? pollError.message : "Suivi du job d'actualisation indisponible.");
        setIsRefreshing(false);
        setRefreshJobId(null);
      }
    }

    void poll();
    const interval = window.setInterval(poll, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [refreshJobId]);

  useEffect(() => {
    if (!featureStoreJobId) return undefined;

    let cancelled = false;

    async function poll() {
      try {
        const job = await getFeatureStoreJobStatus(featureStoreJobId ?? undefined);
        if (cancelled) return;

        setFeatureStoreJob(job);

        if (job.status === 'success') {
          if (job.result) setFeatureBuildInfo(job.result as BuildFeatureStoreResponse);
          setIsBuildingFeatures(false);
          setFeatureStoreJobId(null);
          await reloadAdminState();
          return;
        }

        if (job.status === 'error') {
          setError(job.error ?? 'Construction du Feature Store en erreur.');
          setIsBuildingFeatures(false);
          setFeatureStoreJobId(null);
        }
      } catch (pollError) {
        if (cancelled) return;
        setError(pollError instanceof Error ? pollError.message : 'Suivi du job Feature Store indisponible.');
        setIsBuildingFeatures(false);
        setFeatureStoreJobId(null);
      }
    }

    void poll();
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

      if (response.status === 'accepted' && response.job_id) {
        setRefreshJobId(response.job_id);
        // Polling useEffect takes over  no reload here to avoid overwriting running job state
        return;
      }

      setRefreshInfo(response);

      if (response.status === 'error') {
        setError(response.detail ?? response.error ?? 'Actualisation impossible.');
        setIsRefreshing(false);
        await Promise.all([reloadAdminState(), handleDiagnostics()]);
        return;
      }

      await Promise.all([reloadAdminState(), handleDiagnostics()]);
      setIsRefreshing(false);
    } catch (refreshError) {
      setError(refreshError instanceof Error ? refreshError.message : 'Actualisation impossible.');
      setIsRefreshing(false);
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
        // Polling useEffect takes over  return early to avoid overwriting running job state
        return;
      }

      await reloadAdminState();
    } catch {
      setError('Construction du Feature Store indisponible pour le moment.');
    } finally {
      if (!acceptedJob) setIsBuildingFeatures(false);
    }
  }

  async function handleTrainCandidate() {
    if (!effectiveFeatureStoreReady) {
      setError("Construisez d'abord le Feature Store avant d'entraîner le modèle.");
      return;
    }

    setIsTraining(true);
    setError(null);

    try {
      const result = await trainCandidateModel({ modelType, limit: trainingLimit });
      setTrainingReport(result);

      if (result.status === 'error') {
        setError(result.detail ?? "Construisez d'abord le Feature Store avant d'entraÃ®ner le modÃ¨le.");
      } else if (result.status === 'blocked') {
        setError(result.reason ?? result.dataset_quality?.recommendation_reason ?? "Construisez d'abord le Feature Store avant d'entraÃ®ner le modÃ¨le.");
      }

      await reloadAdminState();
    } catch {
      setError('Candidate training unavailable for the moment.');
    } finally {
      setIsTraining(false);
    }
  }

  async function handleGenerateShadowPredictions() {
    if (!candidateModelTrained) {
      setError("EntraÃ®nez d'abord le modÃ¨le candidat avant de gÃ©nÃ©rer les prédictions shadow.");
      return;
    }

    setIsGeneratingShadow(true);
    setError(null);

    try {
      const result = await generateShadowPredictions({ limit: shadowLimit, force: shadowForce, view: shadowView });
      setShadowResult(result);

      if (result.status === 'error') {
        setError(result.detail ?? 'GÃ©nÃ©ration des prédictions shadow impossible.');
      }

      await reloadAdminState();
    } catch {
      setError('GÃ©nÃ©ration des prédictions shadow indisponible pour le moment.');
    } finally {
      setIsGeneratingShadow(false);
    }
  }

  return (
    <ProtectedRoute requireAdmin>
      <Layout>
        <section className="pageHeader">
          <p className="eyebrow">Administration</p>
          <h1>Admin FootIQ Pro</h1>
          <p>ContrÃ´le du backend, du refresh football-data.org et du pipeline modÃ¨le.</p>
          <div className="roleStrip">
            <span className="userBadge">{user?.email ?? 'Utilisateur inconnu'}</span>
            <span className={`roleBadge ${isAdmin ? 'admin' : ''}`}>{isAdmin ? 'Admin' : 'User'}</span>
          </div>
          <div className="quickActions">
            <Link className="button secondary" href="/dashboard">Tableau de bord</Link>
            <Link className="button secondary" href="/matches">Matchs</Link>
            <Link className="button secondary" href="/predictions">PrÃ©dictions</Link>
            <Link className="button secondary" href="/performance#model-comparison">Backtesting</Link>
            <Link className="button secondary" href="/performance#feature-store">Feature Store</Link>
          </div>
        </section>

        {error && <section className="banner error">{error}</section>}
        {configError && <section className="banner warning">{configError}</section>}
        {featureSummaryError && <section className="banner warning">Impossible de charger /features/summary : {featureSummaryError}</section>}
        {Object.values(adminLoadErrors).some(Boolean) && (
          <section className="banner warning">
            Erreurs de chargement API admin : {Object.values(adminLoadErrors).filter(Boolean).join(' | ')}
          </section>
        )}

        <section className="card">
          <div className="cardTop">
            <div>
              <p className="eyebrow">tat systÃ¨me</p>
              <h2>Configuration et connexion</h2>
            </div>
            <div className="quickActions">
              <button className="button secondary" type="button" onClick={handleReloadState}>
                Recharger l'Ã©tat
              </button>
              <button className="button secondary" type="button" onClick={handleDiagnostics} disabled={isTestingConfig}>
                {isTestingConfig ? 'Test en cours...' : 'Tester la configuration'}
              </button>
            </div>
          </div>

          <div className="compactDataGrid four">
            <div className="metric">
              <span>Backend</span>
              <strong>{backendConnected ? 'connectÃ©' : 'non connectÃ©'}</strong>
            </div>
            <div className="metric">
              <span>API URL</span>
              <strong>{diagnostics?.hasApiUrl ? 'configurÃ©e' : 'absente'}</strong>
            </div>
            <div className="metric">
              <span>ClÃ© admin</span>
              <strong>{diagnostics?.hasAdminApiKey ? 'configurÃ©e' : 'absente'}</strong>
            </div>
            <div className="metric">
              <span>Host API</span>
              <strong>{diagnostics?.apiUrlHost || 'N/A'}</strong>
            </div>
            <div className="metric">
              <span>Stockage actuel</span>
              <strong><span className={valueBadge(resolvedRefreshStorage)}>{formatStorage(resolvedRefreshStorage)}</span></strong>
            </div>
            <div className="metric">
              <span>Source actuelle</span>
              <strong><span className={valueBadge(resolvedRefreshSource)}>{resolvedRefreshSource}</span></strong>
            </div>
            <div className="metric">
              <span>Matchs importÃ©s</span>
              <strong>{stableRefreshInfo?.matches_imported ?? dashboardSummary?.total_matches ?? 0}</strong>
            </div>
            <div className="metric">
              <span>Alertes</span>
              <strong>{adminAlerts?.alerts_count ?? 0}</strong>
            </div>
            <div className="metric">
              <span>Auto-refresh</span>
              <strong>{diagnostics?.hasCronSecret ? 'actif' : 'inactif'}</strong>
            </div>
            <div className="metric">
              <span>Cron Vercel</span>
              <strong>{diagnostics?.cronConfigured ? 'configurÃ©' : 'non configurÃ©'}</strong>
            </div>
            <div className="metric">
              <span>Hourly refresh</span>
              <strong>{workflowStatus?.cron?.hourly_refresh_last_run?.ran_at ?? 'jamais'}</strong>
            </div>
            <div className="metric">
              <span>Fins de match</span>
              <strong>{workflowStatus?.cron?.match_finished_check_last_run?.ran_at ?? 'jamais'}</strong>
            </div>
          </div>
        </section>

        <section className="card accent">
          <div className="cardTop">
            <div>
              <p className="eyebrow">Actualisation donnÃ©es</p>
              <h2>Refresh football-data.org</h2>
            </div>
            <span className={valueBadge(resolvedRefreshSource)}>{resolvedRefreshSource}</span>
          </div>
          <p>
            Cette action actualise uniquement les donnÃ©es et les prédictions officielles.
            Le Feature Store, le ML et le shadow se lancent ensuite sÃ©parÃ©ment.
          </p>
          {!isAdmin && <div className="banner error">AccÃ¨s admin requis.</div>}
          <button className="button primary" type="button" onClick={handleRefresh} disabled={isRefreshing || !isAdmin}>
            {isRefreshing ? 'Actualisation en cours...' : 'Actualiser les donnÃ©es'}
          </button>
          {currentRefreshJob?.status === 'running' && (
            <div className="banner info">
              Job refresh: {currentRefreshJob.status}
              {currentRefreshJob.duration_ms ? ` Â· DurÃ©e ${currentRefreshJob.duration_ms} ms` : ''}
            </div>
          )}
          {refreshJobStale && (
            <div className="banner warning">
              Ancien job refresh probablement bloqu. Dernier tat stable conserv.
              <button className="button secondary" type="button" onClick={handleResetStaleJobs}>
                RÃ©initialiser les jobs bloquÃ©s
              </button>
            </div>
          )}
          {refreshInfo?.warning && <div className="banner warning">{refreshInfo.warning}</div>}
        </section>

        <section className="card workflowCard">
          <p className="eyebrow">Pipeline modÃ¨le</p>
          <h2>Data, Feature Store, candidat ML et shadow</h2>
          <div className="dataList">
            <span>tape 1 <strong>DonnÃ©es importÃ©es</strong></span>
            <span>tape 2 <strong>Feature Store</strong></span>
            <span>tape 3 <strong>ModÃ¨le candidat</strong></span>
            <span>tape 4 <strong>Prédictions shadow</strong></span>
            <span>tape 5 <strong>Backtesting</strong></span>
          </div>
          <div className="compactDataGrid four">
            <div className="metric"><span>Données actualisées</span><strong>{dataImported ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Source</span><strong>{resolvedRefreshSource}</strong></div>
            <div className="metric"><span>Stockage</span><strong>{formatStorage(resolvedRefreshStorage)}</strong></div>
            <div className="metric"><span>Feature Store prêt</span><strong>{effectiveFeatureStoreReady ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Modèle candidat entraîné</span><strong>{candidateModelTrained ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Prédictions shadow générées</span><strong>{workflowStatus?.shadow_predictions.generated ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Backtesting shadow</span><strong>{workflowStatus?.shadow_backtesting.ready ? 'disponible' : 'indisponible'}</strong></div>
            <div className="metric"><span>Score qualitÃ©</span><strong>{featureQuality?.average_quality_score ?? 0}/100</strong></div>
            <div className="metric"><span>Gouvernance</span><strong>{modelGovernance?.promotion_readiness.level ?? 'unknown'}</strong></div>
            <div className="metric"><span>Prochaine étape</span><strong>{displayedNextStep}</strong></div>
          </div>

          <div className="sectionSplit">
            <article>
              <h3>Feature Store</h3>
              <p>GÃ¨le les variables modÃ¨le prÃ©-match pour prÃ©parer l'entraÃ®nement supervisÃ©.</p>
              <button className="button secondary" type="button" onClick={handleBuildFeatureStore} disabled={isBuildingFeatures || !isAdmin}>
                {isBuildingFeatures ? 'Construction...' : 'Construire le Feature Store'}
              </button>
              {featureStoreJob && <div className="banner info">Statut Feature Store: {featureStoreJob.status}</div>}
              {featureStoreJobStale && (
                <div className="banner warning">
                  Job probablement bloquÃ©.
                  <button className="button secondary" type="button" onClick={handleResetStaleJobs}>
                    RÃ©initialiser les jobs bloquÃ©s
                  </button>
                </div>
              )}
              <div className="dataList">
                <span>Snapshots disponibles <strong>{effectiveFeatureSnapshots}</strong></span>
                <span>Lignes entraÃ®nables <strong>{effectiveTrainingRows}</strong></span>
                <span>Couverture target <strong>{featureSummary?.target_coverage ?? workflowStatus?.feature_store.target_coverage ?? dashboardSummary?.target_coverage ?? 0}%</strong></span>
                <span>Stockage Feature Store <strong>{formatStorage(featureSummary?.storage ?? resolvedRefreshStorage)}</strong></span>
              </div>
              {featureBuildInfo && (
                <div className="dataList">
                  <span>Stockage <strong>{formatStorage(featureBuildInfo.storage)}</strong></span>
                  <span>Source prédictions <strong>{featureBuildInfo.predictions_source ?? 'inconnue'}</strong></span>
                  <span>Matchs disponibles <strong>{featureBuildInfo.matches_available ?? 0}</strong></span>
                  <span>Prédictions disponibles <strong>{featureBuildInfo.predictions_available ?? 0}</strong></span>
                  <span>Matchs terminÃ©s exploitables <strong>{featureBuildInfo.finished_matches_available ?? 0}</strong></span>
                  <span>Matchs terminÃ©s avec score <strong>{featureBuildInfo.finished_with_scores ?? 0}</strong></span>
                  <span>Snapshots crÃ©Ã©s <strong>{featureBuildInfo.feature_snapshots_built ?? 0}</strong></span>
                  <span>Snapshots sauvegardÃ©s <strong>{featureBuildInfo.feature_snapshots_saved ?? 0}</strong></span>
                  <span>Lignes entraÃ®nables <strong>{featureBuildInfo.training_rows_available ?? 0}</strong></span>
                </div>
              )}
              {featureBuildInfo && (featureBuildInfo.feature_snapshots_built ?? 0) === 0 && (
                <div className="banner warning">
                  {featureBuildInfo.reason_if_zero_snapshots ?? "Aucun snapshot Feature Store n'a Ã©tÃ© construit."}
                </div>
              )}
            </article>

            <article>
              <h3>ModÃ¨le candidat</h3>
              <div className="formGrid">
                <label className="formField">
                  <span>Type de modÃ¨le</span>
                  <select value={modelType} onChange={(event) => setModelType(event.target.value)}>
                    <option value="random_forest">random_forest</option>
                    <option value="xgboost">xgboost</option>
                  </select>
                </label>
                <label className="formField">
                  <span>Limite de lignes</span>
                  <input min={1} max={10000} type="number" value={trainingLimit} onChange={(event) => setTrainingLimit(Number(event.target.value))} />
                </label>
              </div>
              {!effectiveFeatureStoreReady && (
                <div className="banner warning">Construisez d'abord le Feature Store avant d'entraîner le modèle.</div>
              )}
              <button className="button primary" type="button" onClick={handleTrainCandidate} disabled={isTraining || !isAdmin || !effectiveFeatureStoreReady}>
                {isTraining ? 'Entraînement...' : 'Entraîner le modèle'}
              </button>
              {trainingReport && (
                <div className="dataList">
                  <span>Statut <strong>{trainingReport.status}</strong></span>
                  <span>PrÃ©cision <strong>{trainingReport.accuracy ?? 0}%</strong></span>
                  <span>Log loss <strong>{trainingReport.log_loss ?? 'N/A'}</strong></span>
                </div>
              )}
            </article>
          </div>

          <div className="sectionSplit">
            <article>
              <h3>Prédictions shadow</h3>
              <div className="formGrid">
                <label className="formField">
                  <span>Limite</span>
                  <input min={1} max={2000} type="number" value={shadowLimit} onChange={(event) => setShadowLimit(Number(event.target.value))} />
                </label>
                <label className="formField">
                  <span>Vue</span>
                  <select value={shadowView} onChange={(event) => setShadowView(event.target.value as MatchView)}>
                    <option value="upcoming"> venir</option>
                    <option value="history">Historique</option>
                    <option value="all">Tous</option>
                  </select>
                </label>
                <label className="formField checkboxField">
                  <span>Forcer la rÃ©gÃ©nÃ©ration</span>
                  <input type="checkbox" checked={shadowForce} onChange={(event) => setShadowForce(event.target.checked)} />
                </label>
              </div>
              {!candidateModelTrained && (
                <div className="banner warning">EntraÃ®nez d'abord le modÃ¨le candidat avant de gÃ©nÃ©rer les prédictions shadow.</div>
              )}
              <button className="button primary" type="button" onClick={handleGenerateShadowPredictions} disabled={isGeneratingShadow || !isAdmin || !candidateModelTrained}>
                {isGeneratingShadow ? 'GÃ©nÃ©ration...' : 'GÃ©nÃ©rer les prédictions shadow'}
              </button>
              {shadowResult && (
                <div className="dataList">
                  <span>GÃ©nÃ©rÃ©es <strong>{shadowResult.shadow_predictions_generated ?? 0}</strong></span>
                  <span>SauvegardÃ©es <strong>{shadowResult.shadow_predictions_saved ?? 0}</strong></span>
                  <span>DÃ©saccords Ã©levÃ©s <strong>{shadowResult.high_disagreement_count ?? 0}</strong></span>
                </div>
              )}
            </article>

            <article>
              <h3>Alertes et gouvernance</h3>
              <div className="dataList">
                <span>SantÃ© opÃ©rationnelle <strong>{adminAlerts?.overall_status ?? 'unknown'}</strong></span>
                <span>Critiques <strong>{adminAlerts?.critical_count ?? 0}</strong></span>
                <span>Promotion automatique <strong>{modelGovernance?.policy.automatic_promotion ? 'oui' : 'non'}</strong></span>
                <span>Production verrouillÃ©e <strong>{modelGovernance?.production_model.locked ? 'oui' : 'non'}</strong></span>
              </div>
              {adminAlerts?.next_best_action && (
                <Link className="button secondary" href={adminAlerts.next_best_action.href}>
                  {adminAlerts.next_best_action.label}
                </Link>
              )}
            </article>
          </div>
        </section>

        <section className="card">
          <div className="cardTop">
            <div>
              <p className="eyebrow">Dernier Ã©tat stable</p>
              <h2>RÃ©sultat import</h2>
            </div>
            <span className={valueBadge(resolvedRefreshStorage)}>{formatStorage(resolvedRefreshStorage)}</span>
          </div>
          <div className="dataList">
            <span>Statut <strong>{stableRefreshInfo?.status ?? 'inconnu'}</strong></span>
            <span>Source <strong>{resolvedRefreshSource}</strong></span>
            <span>Stockage <strong>{formatStorage(resolvedRefreshStorage)}</strong></span>
            <span>Matchs importÃ©s <strong>{stableRefreshInfo?.matches_imported ?? 0}</strong></span>
            <span>quipes importÃ©es <strong>{stableRefreshInfo?.teams_imported ?? 0}</strong></span>
            <span>Prédictions générées <strong>{stableRefreshInfo?.predictions_generated ?? stableRefreshInfo?.predictions_imported ?? 0}</strong></span>
            <span>Prédictions sauvegardées <strong>{stableRefreshInfo?.predictions_saved ?? stableRefreshInfo?.predictions_imported ?? 0}</strong></span>
            <span>Snapshots sauvegardÃ©s <strong>{stableRefreshInfo?.snapshots_saved ?? 0}</strong></span>
            <span>Snapshots features <strong>{stableRefreshInfo?.feature_snapshots_saved ?? 0}</strong></span>
            <span>Lignes entraÃ®nables <strong>{stableRefreshInfo?.training_rows_available ?? 0}</strong></span>
            <span>DerniÃ¨re actualisation <strong>{stableRefreshInfo?.last_refresh_at ?? 'N/A'}</strong></span>
            <span>CompÃ©titions configurÃ©es <strong>{stableRefreshInfo?.configured_competitions?.join(', ') || 'FL1, CL'}</strong></span>
          </div>
          {currentRefreshJob?.status === 'running' && (
            <div className="banner info">
              Job en cours: {currentRefreshJob.job_id ?? 'N/A'} Â· {currentRefreshJob.status}
            </div>
          )}
          {(stableRefreshInfo?.competition_warnings?.length ?? 0) > 0 && (
            <div className="banner warning">{stableRefreshInfo?.competition_warnings?.join(' ')}</div>
          )}
          {(stableRefreshInfo?.predictions_saved ?? stableRefreshInfo?.predictions_imported ?? 0) === 0 &&
            (stableRefreshInfo?.predictions_generated ?? 0) > 0 && (
              <div className="banner warning">Les prédictions sont générées mais non sauvegardées en base.</div>
            )}
          <div className="banner info">
            Le backtesting et les snapshots se mettent Ã  jour depuis les matchs terminÃ©s avec score disponible.
          </div>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}

