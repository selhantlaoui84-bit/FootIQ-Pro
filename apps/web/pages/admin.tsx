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
  if (normalized === 'memory' || normalized === 'mémoire') return 'statusBadge critical';
  if (normalized === 'postgresql' || normalized === 'football-data.org') return 'statusBadge healthy';

  return 'statusBadge info';
}

function formatStorage(value?: string | null) {
  return value === 'memory' ? 'mémoire' : value || 'inconnu';
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

type AdminLoadErrors = {
  refreshStatusError: string | null;
  workflowStatusError: string | null;
  featureSummaryError: string | null;
  alertsError: string | null;
  dashboardSummaryError: string | null;
  qualityReportError: string | null;
  governanceError: string | null;
};

const emptyAdminLoadErrors: AdminLoadErrors = {
  refreshStatusError: null,
  workflowStatusError: null,
  featureSummaryError: null,
  alertsError: null,
  dashboardSummaryError: null,
  qualityReportError: null,
  governanceError: null,
};

const adminLoadErrorLabels: Record<keyof AdminLoadErrors, string> = {
  refreshStatusError: 'Refresh status',
  workflowStatusError: 'Workflow status',
  featureSummaryError: 'Feature summary',
  alertsError: 'Alertes admin',
  dashboardSummaryError: 'Résumé dashboard',
  qualityReportError: 'Rapport qualité',
  governanceError: 'Gouvernance modèle',
};

async function captureAdminLoad<T>(promise: Promise<T>, fallback: string): Promise<{ data: T | null; error: string | null }> {
  try {
    return { data: await promise, error: null };
  } catch (loadError) {
    return {
      data: null,
      error: loadError instanceof Error ? loadError.message : fallback,
    };
  }
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
  const [featureSummaryError, setFeatureSummaryError] = useState<string | null>(null);
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
  const [adminLoadErrors, setAdminLoadErrors] = useState<AdminLoadErrors>(emptyAdminLoadErrors);
  const { user, isAdmin } = useAuth();

  const backendConnected = health?.status === 'ok' || health?.status === 'healthy';
  const configError = useMemo(() => diagnosticError(diagnostics), [diagnostics]);
  const stableRefreshInfo = refreshInfo?.stable_refresh_status
    ? { ...refreshInfo.stable_refresh_status, status: refreshInfo.stable_refresh_status.status ?? refreshInfo.status }
    : refreshInfo;
  const currentRefreshJob = refreshJob ?? refreshInfo?.current_job ?? workflowStatus?.latest_refresh_job;
  const featureSummaryUnavailable = Boolean(featureSummaryError && !featureSummary);
  const effectiveFeatureSnapshots =
    featureSummary?.snapshots_count ??
    workflowStatus?.feature_store?.snapshots_count ??
    dashboardSummary?.feature_snapshots_count ??
    0;
  const effectiveTrainingRows =
    featureSummary?.with_target_count ??
    workflowStatus?.feature_store?.training_rows_available ??
    dashboardSummary?.training_rows_available ??
    0;
  const effectiveFeatureStoreReady =
    effectiveFeatureSnapshots > 0 || effectiveTrainingRows > 0 || workflowStatus?.feature_store?.ready === true;
  const effectiveFeatureStorage =
    featureSummary?.storage ??
    workflowStatus?.feature_store?.storage ??
    stableRefreshInfo?.storage ??
    workflowStatus?.refresh?.storage ??
    'inconnu';
  const resolvedRefreshStorage =
    featureSummary?.storage === 'postgresql'
      ? 'postgresql'
      : stableRefreshInfo?.storage === 'postgresql'
        ? 'postgresql'
        : workflowStatus?.refresh.storage === 'postgresql'
          ? 'postgresql'
          : stableRefreshInfo?.storage ?? workflowStatus?.refresh.storage;
  const effectivePipelineStorage =
    effectiveFeatureStorage === 'postgresql' ||
    resolvedRefreshStorage === 'postgresql' ||
    workflowStatus?.refresh?.storage === 'postgresql'
      ? 'postgresql'
      : (resolvedRefreshStorage ?? 'inconnu');
  const effectiveNextStep = effectiveFeatureStoreReady
    ? (workflowStatus?.candidate_model?.trained ? 'generate_shadow_predictions' : 'train_candidate_model')
    : (workflowStatus?.next_step ?? 'refresh_data');
  const displayedPipelineStorage = featureSummaryUnavailable ? 'inconnu' : effectivePipelineStorage;
  const displayedFeatureReady = featureSummaryUnavailable ? 'indisponible' : (effectiveFeatureStoreReady ? 'oui' : 'non');
  const displayedFeatureSnapshots = featureSummaryUnavailable ? 'indisponible' : effectiveFeatureSnapshots;
  const displayedTrainingRows = featureSummaryUnavailable ? 'indisponible' : effectiveTrainingRows;
  const displayedTargetCoverage = featureSummaryUnavailable ? 'indisponible' : `${featureSummary?.target_coverage ?? 0}%`;
  const displayedFeatureStorage = featureSummaryUnavailable ? 'indisponible' : formatStorage(effectiveFeatureStorage);
  const resolvedRefreshSource = workflowStatus?.refresh.source ?? stableRefreshInfo?.source ?? 'mock';
  const dataImported =
    workflowStatus?.refresh.data_imported ??
    ((workflowStatus?.refresh.storage === 'postgresql' && (workflowStatus?.refresh.matches_imported ?? 0) > 0) ||
      (stableRefreshInfo?.storage === 'postgresql' && (stableRefreshInfo?.matches_imported ?? 0) > 0));
  const candidateModelTrained = workflowStatus?.candidate_model.trained ?? false;
  const refreshJobStale = isProbablyStale(currentRefreshJob);
  const featureStoreJobStale = isProbablyStale(featureStoreJob) || isProbablyStale(workflowStatus?.latest_feature_store_job);
  const adminLoadErrorEntries = Object.entries(adminLoadErrors).filter((entry): entry is [keyof AdminLoadErrors, string] => Boolean(entry[1]));

  async function reloadAdminState() {
    const [healthResult, refreshStatusResult, workflowResult, featureStoreResult, qualityResult, governanceResult, alertsResult, dashboardResult] = await Promise.all([
      getBackendHealth().catch(() => null),
      captureAdminLoad(getRefreshStatus(), 'Impossible de charger /admin/refresh-status'),
      captureAdminLoad(getAdminWorkflowStatus(), 'Impossible de charger /admin/workflow-status'),
      captureAdminLoad(getFeatureSummary(), 'Impossible de charger /features/summary'),
      captureAdminLoad(getFeatureQualityReport(), 'Impossible de charger /features/quality-report'),
      captureAdminLoad(getModelGovernance(), 'Impossible de charger /models/governance'),
      captureAdminLoad(getAdminAlerts(), 'Impossible de charger /admin/alerts'),
      captureAdminLoad(getDashboardSummary(), 'Impossible de charger /dashboard/summary'),
    ]);

    setHealth(healthResult);
    setAdminLoadErrors({
      refreshStatusError: refreshStatusResult.error,
      workflowStatusError: workflowResult.error,
      featureSummaryError: featureStoreResult.error,
      qualityReportError: qualityResult.error,
      governanceError: governanceResult.error,
      alertsError: alertsResult.error,
      dashboardSummaryError: dashboardResult.error,
    });

    if (refreshStatusResult.data) {
      setRefreshInfo(refreshStatusResult.data);
      if (refreshStatusResult.data.current_job?.status === 'running' && !refreshJobId) {
        setRefreshJob(refreshStatusResult.data.current_job);
      }
    }
    if (workflowResult.data) setWorkflowStatus(workflowResult.data);
    if (featureStoreResult.data) {
      setFeatureSummary(featureStoreResult.data);
      setFeatureSummaryError(null);
    } else if (featureStoreResult.error) {
      setFeatureSummaryError(featureStoreResult.error);
    }
    if (qualityResult.data) setFeatureQuality(qualityResult.data);
    if (governanceResult.data) setModelGovernance(governanceResult.data);
    if (alertsResult.data) setAdminAlerts(alertsResult.data);
    if (dashboardResult.data) setDashboardSummary(dashboardResult.data);
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
      setError(result.detail ?? 'Réinitialisation des jobs bloqués impossible.');
      return;
    }
    setRefreshJob(null);
    setRefreshJobId(null);
    setFeatureStoreJob(null);
    setFeatureStoreJobId(null);
    const featureStore = await getFeatureSummary().catch(() => null);
    if (featureStore) {
      setFeatureSummary(featureStore);
      setFeatureSummaryError(null);
    } else {
      setFeatureSummaryError('Impossible de charger /features/summary');
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

        if (isProbablyStale(job)) {
          setError('Ancien job refresh probablement bloqué.');
          setRefreshJob(job);
          setIsRefreshing(false);
          setRefreshJobId(null);
          return;
        }

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
          const latestFeatureSummary = await getFeatureSummary().catch(() => null);
          if (latestFeatureSummary) {
            setFeatureSummary(latestFeatureSummary);
            setFeatureSummaryError(null);
          }
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
        setRefreshJob({
          job_id: response.job_id,
          status: 'running',
          started_at: new Date().toISOString(),
          finished_at: null,
          duration_ms: null,
          result: null,
          error: null,
        });
        await handleDiagnostics();
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
        setError(result.detail ?? "Construisez d'abord le Feature Store avant d'entraîner le modèle.");
      } else if (result.status === 'blocked') {
        setError(result.reason ?? result.dataset_quality?.recommendation_reason ?? "Construisez d'abord le Feature Store avant d'entraîner le modèle.");
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
      setError("Entraînez d'abord le modèle candidat avant de générer les prédictions shadow.");
      return;
    }

    setIsGeneratingShadow(true);
    setError(null);

    try {
      const result = await generateShadowPredictions({ limit: shadowLimit, force: shadowForce, view: shadowView });
      setShadowResult(result);

      if (result.status === 'error') {
        setError(result.detail ?? 'Génération des prédictions shadow impossible.');
      }

      await reloadAdminState();
    } catch {
      setError('Génération des prédictions shadow indisponible pour le moment.');
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
          <p>Contrôle du backend, du refresh football-data.org et du pipeline modèle.</p>
          <div className="roleStrip">
            <span className="userBadge">{user?.email ?? 'Utilisateur inconnu'}</span>
            <span className={`roleBadge ${isAdmin ? 'admin' : ''}`}>{isAdmin ? 'Admin' : 'User'}</span>
          </div>
          <div className="quickActions">
            <Link className="button secondary" href="/dashboard">Tableau de bord</Link>
            <Link className="button secondary" href="/matches">Matchs</Link>
            <Link className="button secondary" href="/predictions">Prédictions</Link>
            <Link className="button secondary" href="/performance#model-comparison">Backtesting</Link>
            <Link className="button secondary" href="/performance#feature-store">Feature Store</Link>
          </div>
        </section>

        {error && <section className="banner error">{error}</section>}
        {configError && <section className="banner warning">{configError}</section>}
        {featureSummaryError && <section className="banner error">{featureSummaryError}</section>}
        {adminLoadErrorEntries.length > 0 && (
          <section className="card warningCard">
            <div className="cardTop">
              <div>
                <p className="eyebrow">Erreurs de chargement API admin</p>
                <h2>Certains états n'ont pas pu être rechargés</h2>
              </div>
            </div>
            <div className="dataList">
              {adminLoadErrorEntries.map(([key, message]) => (
                <span key={key}>{adminLoadErrorLabels[key]} <strong>{message}</strong></span>
              ))}
            </div>
          </section>
        )}

        <section className="card">
          <div className="cardTop">
            <div>
              <p className="eyebrow">État système</p>
              <h2>Configuration et connexion</h2>
            </div>
            <div className="quickActions">
              <button className="button secondary" type="button" onClick={handleReloadState}>
                Recharger l'état
              </button>
              <button className="button secondary" type="button" onClick={handleDiagnostics} disabled={isTestingConfig}>
                {isTestingConfig ? 'Test en cours...' : 'Tester la configuration'}
              </button>
            </div>
          </div>

          <div className="compactDataGrid four">
            <div className="metric">
              <span>Backend</span>
              <strong>{backendConnected ? 'connecté' : 'non connecté'}</strong>
            </div>
            <div className="metric">
              <span>API URL</span>
              <strong>{diagnostics?.hasApiUrl ? 'configurée' : 'absente'}</strong>
            </div>
            <div className="metric">
              <span>Clé admin</span>
              <strong>{diagnostics?.hasAdminApiKey ? 'configurée' : 'absente'}</strong>
            </div>
            <div className="metric">
              <span>Host API</span>
              <strong>{diagnostics?.apiUrlHost || 'N/A'}</strong>
            </div>
            <div className="metric">
              <span>Stockage actuel</span>
              <strong><span className={valueBadge(displayedPipelineStorage)}>{formatStorage(displayedPipelineStorage)}</span></strong>
            </div>
            <div className="metric">
              <span>Source actuelle</span>
              <strong><span className={valueBadge(resolvedRefreshSource)}>{resolvedRefreshSource}</span></strong>
            </div>
            <div className="metric">
              <span>Matchs importés</span>
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
              <strong>{diagnostics?.cronConfigured ? 'configuré' : 'non configuré'}</strong>
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
              <p className="eyebrow">Actualisation données</p>
              <h2>Refresh football-data.org</h2>
            </div>
            <span className={valueBadge(resolvedRefreshSource)}>{resolvedRefreshSource}</span>
          </div>
          <p>
            Cette action actualise uniquement les données et les prédictions officielles.
            Le Feature Store, le ML et le shadow se lancent ensuite séparément.
          </p>
          {!isAdmin && <div className="banner error">Accès admin requis.</div>}
          <button className="button primary" type="button" onClick={handleRefresh} disabled={isRefreshing || !isAdmin}>
            {isRefreshing ? 'Actualisation en cours...' : 'Actualiser les données'}
          </button>
          {currentRefreshJob?.status === 'running' && (
            <div className="banner info">
              Job refresh: {currentRefreshJob.status}
              {currentRefreshJob.duration_ms ? ` · Durée ${currentRefreshJob.duration_ms} ms` : ''}
            </div>
          )}
          {refreshJobStale && (
            <div className="banner warning">
              Ancien job refresh probablement bloqué. Dernier état stable conservé.
              <button className="button secondary" type="button" onClick={handleResetStaleJobs}>
                Réinitialiser les jobs bloqués
              </button>
            </div>
          )}
          {refreshInfo?.warning && <div className="banner warning">{refreshInfo.warning}</div>}
        </section>

        <section className="card workflowCard">
          <p className="eyebrow">Pipeline modèle</p>
          <h2>Data, Feature Store, candidat ML et shadow</h2>
          <div className="dataList">
            <span>Étape 1 <strong>Données importées</strong></span>
            <span>Étape 2 <strong>Feature Store</strong></span>
            <span>Étape 3 <strong>Modèle candidat</strong></span>
            <span>Étape 4 <strong>Prédictions shadow</strong></span>
            <span>Étape 5 <strong>Backtesting</strong></span>
          </div>
          <div className="compactDataGrid four">
            <div className="metric"><span>Données actualisées</span><strong>{dataImported ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Source</span><strong>{resolvedRefreshSource}</strong></div>
            <div className="metric"><span>Stockage</span><strong>{formatStorage(displayedPipelineStorage)}</strong></div>
            <div className="metric"><span>Feature Store prêt</span><strong>{displayedFeatureReady}</strong></div>
            <div className="metric"><span>Modèle candidat entraîné</span><strong>{candidateModelTrained ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Prédictions shadow générées</span><strong>{workflowStatus?.shadow_predictions.generated ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Backtesting shadow</span><strong>{workflowStatus?.shadow_backtesting.ready ? 'disponible' : 'indisponible'}</strong></div>
            <div className="metric"><span>Score qualité</span><strong>{featureQuality?.average_quality_score ?? 0}/100</strong></div>
            <div className="metric"><span>Gouvernance</span><strong>{modelGovernance?.promotion_readiness.level ?? 'unknown'}</strong></div>
            <div className="metric"><span>Prochaine étape</span><strong>{effectiveNextStep}</strong></div>
          </div>

          <div className="sectionSplit">
            <article>
              <h3>Feature Store</h3>
              <p>Gèle les variables modèle pré-match pour préparer l'entraînement supervisé.</p>
              <button className="button secondary" type="button" onClick={handleBuildFeatureStore} disabled={isBuildingFeatures || !isAdmin}>
                {isBuildingFeatures ? 'Construction...' : 'Construire le Feature Store'}
              </button>
              {featureStoreJob && <div className="banner info">Statut Feature Store: {featureStoreJob.status}</div>}
              {featureStoreJobStale && (
                <div className="banner warning">
                  Job probablement bloqué.
                  <button className="button secondary" type="button" onClick={handleResetStaleJobs}>
                    Réinitialiser les jobs bloqués
                  </button>
                </div>
              )}
              <div className="dataList">
                <span>Snapshots disponibles <strong>{displayedFeatureSnapshots}</strong></span>
                <span>Lignes entraînables <strong>{displayedTrainingRows}</strong></span>
                <span>Couverture target <strong>{displayedTargetCoverage}</strong></span>
                <span>Stockage Feature Store <strong>{displayedFeatureStorage}</strong></span>
              </div>
              {featureBuildInfo && (
                <div className="dataList">
                  <span>Stockage <strong>{formatStorage(featureBuildInfo.storage)}</strong></span>
                  <span>Source prédictions <strong>{featureBuildInfo.predictions_source ?? 'inconnue'}</strong></span>
                  <span>Matchs disponibles <strong>{featureBuildInfo.matches_available ?? 0}</strong></span>
                  <span>Prédictions disponibles <strong>{featureBuildInfo.predictions_available ?? 0}</strong></span>
                  <span>Matchs terminés exploitables <strong>{featureBuildInfo.finished_matches_available ?? 0}</strong></span>
                  <span>Matchs terminés avec score <strong>{featureBuildInfo.finished_with_scores ?? 0}</strong></span>
                  <span>Nouveaux snapshots créés <strong>{featureBuildInfo.feature_snapshots_built ?? 0}</strong></span>
                  <span>Nouveaux snapshots sauvegardés <strong>{featureBuildInfo.feature_snapshots_saved ?? 0}</strong></span>
                  <span>Nouvelles lignes entraînables <strong>{featureBuildInfo.training_rows_available ?? 0}</strong></span>
                </div>
              )}
              {featureBuildInfo && effectiveFeatureSnapshots > 0 && (featureBuildInfo.feature_snapshots_built ?? 0) === 0 && (
                <div className="banner info">
                  Aucun nouveau snapshot créé : le Feature Store contient déjà des snapshots disponibles.
                </div>
              )}
              {featureBuildInfo && effectiveFeatureSnapshots === 0 && (featureBuildInfo.feature_snapshots_built ?? 0) === 0 && (
                <div className="banner warning">
                  {featureBuildInfo.reason_if_zero_snapshots ?? "Aucun snapshot Feature Store n'a été construit."}
                </div>
              )}
            </article>

            <article>
              <h3>Modèle candidat</h3>
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
                  <span>Précision <strong>{trainingReport.accuracy ?? 0}%</strong></span>
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
                    <option value="upcoming">À venir</option>
                    <option value="history">Historique</option>
                    <option value="all">Tous</option>
                  </select>
                </label>
                <label className="formField checkboxField">
                  <span>Forcer la régénération</span>
                  <input type="checkbox" checked={shadowForce} onChange={(event) => setShadowForce(event.target.checked)} />
                </label>
              </div>
              {!candidateModelTrained && (
                <div className="banner warning">Entraînez d'abord le modèle candidat avant de générer les prédictions shadow.</div>
              )}
              <button className="button primary" type="button" onClick={handleGenerateShadowPredictions} disabled={isGeneratingShadow || !isAdmin || !candidateModelTrained}>
                {isGeneratingShadow ? 'Génération...' : 'Générer les prédictions shadow'}
              </button>
              {shadowResult && (
                <div className="dataList">
                  <span>Générées <strong>{shadowResult.shadow_predictions_generated ?? 0}</strong></span>
                  <span>Sauvegardées <strong>{shadowResult.shadow_predictions_saved ?? 0}</strong></span>
                  <span>Désaccords élevés <strong>{shadowResult.high_disagreement_count ?? 0}</strong></span>
                </div>
              )}
            </article>

            <article>
              <h3>Alertes et gouvernance</h3>
              <div className="dataList">
                <span>Santé opérationnelle <strong>{adminAlerts?.overall_status ?? 'unknown'}</strong></span>
                <span>Critiques <strong>{adminAlerts?.critical_count ?? 0}</strong></span>
                <span>Promotion automatique <strong>{modelGovernance?.policy.automatic_promotion ? 'oui' : 'non'}</strong></span>
                <span>Production verrouillée <strong>{modelGovernance?.production_model.locked ? 'oui' : 'non'}</strong></span>
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
              <p className="eyebrow">Dernier état stable</p>
              <h2>Résultat import</h2>
            </div>
            <span className={valueBadge(displayedPipelineStorage)}>{formatStorage(displayedPipelineStorage)}</span>
          </div>
          <div className="dataList">
            <span>Statut <strong>{stableRefreshInfo?.status ?? 'inconnu'}</strong></span>
            <span>Source <strong>{resolvedRefreshSource}</strong></span>
            <span>Stockage <strong>{formatStorage(displayedPipelineStorage)}</strong></span>
            <span>Matchs importés <strong>{stableRefreshInfo?.matches_imported ?? 0}</strong></span>
            <span>Équipes importées <strong>{stableRefreshInfo?.teams_imported ?? 0}</strong></span>
            <span>Prédictions générées <strong>{stableRefreshInfo?.predictions_generated ?? stableRefreshInfo?.predictions_imported ?? 0}</strong></span>
            <span>Prédictions sauvegardées <strong>{stableRefreshInfo?.predictions_saved ?? stableRefreshInfo?.predictions_imported ?? 0}</strong></span>
            <span>Snapshots sauvegardés <strong>{stableRefreshInfo?.snapshots_saved ?? 0}</strong></span>
            <span>Snapshots features <strong>{stableRefreshInfo?.feature_snapshots_saved ?? 0}</strong></span>
            <span>Lignes entraînables <strong>{stableRefreshInfo?.training_rows_available ?? 0}</strong></span>
            <span>Dernière actualisation <strong>{stableRefreshInfo?.last_refresh_at ?? 'N/A'}</strong></span>
            <span>Compétitions configurées <strong>{stableRefreshInfo?.configured_competitions?.join(', ') || 'FL1, CL'}</strong></span>
          </div>
          {currentRefreshJob?.status === 'running' && (
            <div className="banner info">
              Job en cours: {currentRefreshJob.job_id ?? 'N/A'} · {currentRefreshJob.status}
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
            Le backtesting et les snapshots se mettent à jour depuis les matchs terminés avec score disponible.
          </div>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}
