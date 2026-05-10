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
  getCalibrationReport,
  getDashboardSummary,
  getFeatureQualityReport,
  getFeatureSummary,
  getFeatureStoreJobStatus,
  getLearningFeedback,
  getLearningMonitoring,
  getMlShadowBacktesting,
  getModelPromotionAudit,
  getModelVersionsRegistry,
  getShadowPredictionJobStatus,
  getModelGovernance,
  getRefreshJobStatus,
  getRefreshStatus,
  refreshData,
  promoteCandidateModel,
  rollbackProductionModel,
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
  CalibrationReport,
  LearningFeedbackReport,
  LearningMonitoringReport,
  MatchView,
  MlShadowBacktesting,
  ModelGovernanceReport,
  ModelPromotionAuditResponse,
  PromoteCandidateModelResponse,
  RollbackProductionModelResponse,
  ModelVersionsResponse,
  RefreshJobStatus,
  RefreshResponse,
  TrainingReport,
} from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type AdminLoadErrors = {
  refreshStatusError: string | null;
  workflowStatusError: string | null;
  featureSummaryError: string | null;
  alertsError: string | null;
  dashboardSummaryError: string | null;
  qualityReportError: string | null;
  governanceError: string | null;
  learningMonitoringError: string | null;
  shadowBacktestingError: string | null;
  promotionAuditError: string | null;
};

type AdminLoadResult<T> = {
  data: T | null;
  error: string | null;
};

const emptyAdminLoadErrors: AdminLoadErrors = {
  refreshStatusError: null,
  workflowStatusError: null,
  featureSummaryError: null,
  alertsError: null,
  dashboardSummaryError: null,
  qualityReportError: null,
  governanceError: null,
  learningMonitoringError: null,
  shadowBacktestingError: null,
  promotionAuditError: null,
};

const adminLoadErrorLabels: Record<keyof AdminLoadErrors, string> = {
  refreshStatusError: 'Refresh status',
  workflowStatusError: 'Workflow status',
  featureSummaryError: 'Feature summary',
  alertsError: 'Alertes admin',
  dashboardSummaryError: 'Résumé dashboard',
  qualityReportError: 'Rapport qualité',
  governanceError: 'Gouvernance modèle',
  learningMonitoringError: 'Monitoring learning',
  shadowBacktestingError: 'Backtesting shadow',
  promotionAuditError: 'Audit promotion',
};

function valueBadge(value?: string | null) {
  const normalized = (value ?? '').toLowerCase();

  if (normalized === 'mock') return 'statusBadge warning';
  if (normalized === 'memory' || normalized === 'mémoire') return 'statusBadge critical';
  if (normalized === 'postgresql' || normalized === 'football-data.org') return 'statusBadge healthy';

  return 'statusBadge info';
}

function formatStorage(value?: string | null) {
  if (value === 'memory') return 'mémoire';
  return value || 'inconnu';
}

function diagnosticError(diagnostics: AdminDiagnosticsResponse | null) {
  if (diagnostics?.backendHealth.status === 'error') return diagnostics.backendHealth.error;
  if (diagnostics?.refreshStatus.status === 'error') return diagnostics.refreshStatus.error;
  return null;
}

function isProbablyStale(job?: RefreshJobStatus | null) {
  if (!job || job.status !== 'running' || !job.started_at) return false;
  return Date.now() - new Date(job.started_at).getTime() > 5 * 60 * 1000;
}

function runningJob(jobId: string): RefreshJobStatus {
  return {
    job_id: jobId,
    status: 'running',
    started_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    finished_at: null,
    duration_ms: null,
    result: null,
    error: null,
  };
}

async function captureAdminLoad<T>(promise: Promise<T>, fallback: string): Promise<AdminLoadResult<T>> {
  try {
    return { data: await promise, error: null };
  } catch (loadError) {
    return {
      data: null,
      error: loadError instanceof Error ? loadError.message : fallback,
    };
  }
}

function formatDate(value?: string | null) {
  if (!value) return 'N/A';
  return value;
}

function trainingFeatureCount(report?: TrainingReport | null) {
  if (!report) return 0;
  if (typeof report.features_used === 'number') return report.features_used;
  if (Array.isArray(report.features_used)) return report.features_used.length;
  return report.feature_names?.length ?? report.feature_columns?.length ?? 0;
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
  const [adminLoadErrors, setAdminLoadErrors] = useState<AdminLoadErrors>(emptyAdminLoadErrors);
  const [isBuildingFeatures, setIsBuildingFeatures] = useState(false);
  const [featureBuildInfo, setFeatureBuildInfo] = useState<BuildFeatureStoreResponse | null>(null);
  const [featureStoreJob, setFeatureStoreJob] = useState<RefreshJobStatus | null>(null);
  const [featureStoreJobId, setFeatureStoreJobId] = useState<string | null>(null);
  const [featureQuality, setFeatureQuality] = useState<DatasetQualityReport | null>(null);
  const [isTraining, setIsTraining] = useState(false);
  const [modelGovernance, setModelGovernance] = useState<ModelGovernanceReport | null>(null);
  const [learningFeedback, setLearningFeedback] = useState<LearningFeedbackReport | null>(null);
  const [learningMonitoring, setLearningMonitoring] = useState<LearningMonitoringReport | null>(null);
  const [shadowBacktesting, setShadowBacktesting] = useState<MlShadowBacktesting | null>(null);
  const [calibrationReport, setCalibrationReport] = useState<CalibrationReport | null>(null);
  const [modelVersions, setModelVersions] = useState<ModelVersionsResponse | null>(null);
  const [promotionAudit, setPromotionAudit] = useState<ModelPromotionAuditResponse | null>(null);
  const [promotionResult, setPromotionResult] = useState<PromoteCandidateModelResponse | RollbackProductionModelResponse | null>(null);
  const [isPromotingModel, setIsPromotingModel] = useState(false);
  const [isRollingBackModel, setIsRollingBackModel] = useState(false);
  const [adminAlerts, setAdminAlerts] = useState<AdminAlertsReport | null>(null);
  const [modelType, setModelType] = useState('random_forest');
  const [trainingLimit, setTrainingLimit] = useState(5000);
  const [trainingReport, setTrainingReport] = useState<TrainingReport | null>(null);
  const [isGeneratingShadow, setIsGeneratingShadow] = useState(false);
  const [shadowLimit, setShadowLimit] = useState(500);
  const [shadowForce, setShadowForce] = useState(false);
  const [shadowView, setShadowView] = useState<MatchView>('upcoming');
  const [shadowResult, setShadowResult] = useState<GenerateShadowPredictionsResponse | null>(null);
  const [shadowJob, setShadowJob] = useState<RefreshJobStatus | null>(null);
  const [shadowJobId, setShadowJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { user, isAdmin } = useAuth();

  const backendConnected = health?.status === 'ok' || health?.status === 'healthy';
  const configError = useMemo(() => diagnosticError(diagnostics), [diagnostics]);
  const stableRefreshInfo = refreshInfo?.stable_refresh_status
    ? { ...refreshInfo.stable_refresh_status, status: refreshInfo.stable_refresh_status.status ?? refreshInfo.status }
    : refreshInfo;
  const currentRefreshJob = refreshJob ?? refreshInfo?.current_job ?? workflowStatus?.latest_refresh_job;
  const currentFeatureStoreJob = featureStoreJob ?? workflowStatus?.latest_feature_store_job;
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
    effectiveFeatureSnapshots > 0 ||
    effectiveTrainingRows > 0 ||
    workflowStatus?.feature_store?.ready === true;
  const displayedFeatureReady = featureSummaryUnavailable
    ? 'indisponible'
    : effectiveFeatureStoreReady
      ? 'oui'
      : 'non';

  const resolvedRefreshStorage =
    featureSummary?.storage === 'postgresql' ||
    stableRefreshInfo?.storage === 'postgresql' ||
    refreshInfo?.storage === 'postgresql' ||
    workflowStatus?.refresh?.storage === 'postgresql'
      ? 'postgresql'
      : stableRefreshInfo?.storage ?? refreshInfo?.storage ?? workflowStatus?.refresh?.storage ?? 'inconnu';
  const effectiveFeatureStorage =
    featureSummary?.storage ??
    (workflowStatus?.feature_store as { storage?: string } | undefined)?.storage ??
    resolvedRefreshStorage;
  const effectivePipelineStorage =
    effectiveFeatureStorage === 'postgresql' ||
    resolvedRefreshStorage === 'postgresql'
      ? 'postgresql'
      : resolvedRefreshStorage;
  const displayedPipelineStorage = featureSummaryUnavailable ? 'inconnu' : effectivePipelineStorage;
  const displayedFeatureStorage = featureSummaryUnavailable ? 'indisponible' : formatStorage(effectiveFeatureStorage);
  const displayedFeatureSnapshots = featureSummaryUnavailable ? 'indisponible' : effectiveFeatureSnapshots;
  const displayedTrainingRows = featureSummaryUnavailable ? 'indisponible' : effectiveTrainingRows;
  const displayedTargetCoverage = featureSummaryUnavailable ? 'indisponible' : `${featureSummary?.target_coverage ?? 0}%`;
  const stableSnapshotsSaved =
    (stableRefreshInfo?.snapshots_saved ?? 0) > 0
      ? stableRefreshInfo?.snapshots_saved
      : dashboardSummary?.snapshots_count ?? effectiveFeatureSnapshots;
  const stableFeatureSnapshotsSaved =
    (stableRefreshInfo?.feature_snapshots_saved ?? 0) > 0
      ? stableRefreshInfo?.feature_snapshots_saved
      : effectiveFeatureSnapshots;
  const stableTrainingRows =
    (stableRefreshInfo?.training_rows_available ?? 0) > 0
      ? stableRefreshInfo?.training_rows_available
      : effectiveTrainingRows;
  const registeredCandidateRows = modelVersions?.latest_candidate_model?.rows_used ?? 0;
  const trainingSucceeded =
    trainingReport?.status === 'ok' ||
    trainingReport?.status === 'trained' ||
    trainingReport?.status === 'success' ||
    (trainingReport?.rows_used ?? 0) >= 30;
  const candidateModelTrained =
    workflowStatus?.candidate_model?.trained === true ||
    trainingSucceeded ||
    registeredCandidateRows >= 30 ||
    Boolean(modelVersions?.latest_candidate_model?.model_version);
  const displayedNextStep = effectiveFeatureStoreReady
    ? (candidateModelTrained ? 'generate_shadow_predictions' : 'train_candidate_model')
    : (workflowStatus?.next_step ?? 'refresh_data');
  const effectiveNextStep = displayedNextStep;

  const rawRefreshSource = workflowStatus?.refresh?.source ?? stableRefreshInfo?.source ?? 'mock';
  const refreshMatchesImported = stableRefreshInfo?.matches_imported ?? workflowStatus?.refresh?.matches_imported ?? 0;
  const resolvedRefreshSource =
    rawRefreshSource === 'mock' && resolvedRefreshStorage === 'postgresql' && refreshMatchesImported > 0
      ? 'football-data.org'
      : rawRefreshSource;
  const dataImported =
    workflowStatus?.refresh?.data_imported ??
    ((resolvedRefreshStorage === 'postgresql' || workflowStatus?.refresh?.storage === 'postgresql') && refreshMatchesImported > 0);
  const refreshJobStale = isProbablyStale(currentRefreshJob);
  const featureStoreJobStale = isProbablyStale(currentFeatureStoreJob);
  const adminLoadErrorEntries = Object.entries(adminLoadErrors).filter(
    (entry): entry is [keyof AdminLoadErrors, string] => Boolean(entry[1]),
  );
  const promotionEvaluation = modelGovernance?.promotion_evaluation;
  const productionModel = modelVersions?.current_production_model;
  const candidateModel = modelVersions?.latest_candidate_model;
  const promotionAllowed = promotionEvaluation?.promotion_allowed === true;
  const promotionReasons =
    promotionEvaluation?.reasons?.length
      ? promotionEvaluation.reasons
      : modelGovernance?.promotion_readiness.blocking_reasons ?? [];
  const rollbackTarget = modelVersions?.versions.find((item) => item.status === 'archived');

  async function reloadAdminState() {
    const [
      healthResult,
      refreshStatusResult,
      workflowResult,
      featureSummaryResult,
      qualityResult,
      governanceResult,
      feedbackResult,
      monitoringResult,
      shadowBacktestingResult,
      calibrationResult,
      modelVersionsResult,
      promotionAuditResult,
      alertsResult,
      dashboardResult,
    ] = await Promise.all([
      getBackendHealth().catch(() => null),
      captureAdminLoad(getRefreshStatus(), 'Impossible de charger /admin/refresh-status'),
      captureAdminLoad(getAdminWorkflowStatus(), 'Impossible de charger /admin/workflow-status'),
      captureAdminLoad(getFeatureSummary(), 'Impossible de charger /features/summary'),
      captureAdminLoad(getFeatureQualityReport(), 'Impossible de charger /features/quality-report'),
      captureAdminLoad(getModelGovernance(), 'Impossible de charger /models/governance'),
      captureAdminLoad(getLearningFeedback(), 'Impossible de charger /learning/feedback'),
      captureAdminLoad(getLearningMonitoring(), 'Impossible de charger /learning/monitoring'),
      captureAdminLoad(getMlShadowBacktesting(2000), 'Impossible de charger /shadow/backtesting'),
      captureAdminLoad(getCalibrationReport(), 'Impossible de charger /learning/calibration'),
      captureAdminLoad(getModelVersionsRegistry(), 'Impossible de charger /models/versions'),
      captureAdminLoad(getModelPromotionAudit(), 'Impossible de charger /models/promotion-audit'),
      captureAdminLoad(getAdminAlerts(), 'Impossible de charger /admin/alerts'),
      captureAdminLoad(getDashboardSummary(), 'Impossible de charger /dashboard/summary'),
    ]);

    setHealth(healthResult);
    setAdminLoadErrors({
      refreshStatusError: refreshStatusResult.error,
      workflowStatusError: workflowResult.error,
      featureSummaryError: featureSummaryResult.error,
      qualityReportError: qualityResult.error,
      governanceError: governanceResult.error,
      learningMonitoringError: monitoringResult.error,
      shadowBacktestingError: shadowBacktestingResult.error,
      promotionAuditError: promotionAuditResult.error,
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
    if (featureSummaryResult.data) {
      setFeatureSummary(featureSummaryResult.data);
      setFeatureSummaryError(null);
      setAdminLoadErrors((previous) => ({ ...previous, featureSummaryError: null }));
    } else if (featureSummaryResult.error) {
      setFeatureSummaryError(featureSummaryResult.error);
    }
    if (qualityResult.data) setFeatureQuality(qualityResult.data);
    if (governanceResult.data) setModelGovernance(governanceResult.data);
    if (feedbackResult.data) setLearningFeedback(feedbackResult.data);
    if (monitoringResult.data) setLearningMonitoring(monitoringResult.data);
    if (shadowBacktestingResult.data) setShadowBacktesting(shadowBacktestingResult.data);
    if (calibrationResult.data) setCalibrationReport(calibrationResult.data);
    if (modelVersionsResult.data) setModelVersions(modelVersionsResult.data);
    if (promotionAuditResult.data) setPromotionAudit(promotionAuditResult.data);
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
    await handleReloadState();
  }

  useEffect(() => {
    void reloadAdminState();
    void handleDiagnostics();
  }, []);

  useEffect(() => {
    if (!refreshJobId) return undefined;

    let cancelled = false;

    async function pollRefreshJob() {
      try {
        const job = await getRefreshJobStatus(refreshJobId ?? undefined);
        if (cancelled) return;

        if (isProbablyStale(job)) {
          setError('Ancien job refresh probablement bloqué. Dernier état stable conservé.');
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

    void pollRefreshJob();
    const interval = window.setInterval(pollRefreshJob, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [refreshJobId]);

  useEffect(() => {
    if (!featureStoreJobId) return undefined;

    let cancelled = false;

    async function pollFeatureStoreJob() {
      try {
        const job = await getFeatureStoreJobStatus(featureStoreJobId ?? undefined);
        if (cancelled) return;

        setFeatureStoreJob(job);

        if (isProbablyStale(job)) {
          setError('Job Feature Store probablement bloqué.');
          setIsBuildingFeatures(false);
          setFeatureStoreJobId(null);
          return;
        }

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
          await reloadAdminState();
        }
      } catch (pollError) {
        if (cancelled) return;
        setError(pollError instanceof Error ? pollError.message : 'Suivi du job Feature Store indisponible.');
        setIsBuildingFeatures(false);
        setFeatureStoreJobId(null);
      }
    }

    void pollFeatureStoreJob();
    const interval = window.setInterval(pollFeatureStoreJob, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [featureStoreJobId]);

  useEffect(() => {
    if (!shadowJobId) return undefined;

    let cancelled = false;

    async function pollShadowJob() {
      try {
        const job = await getShadowPredictionJobStatus(shadowJobId ?? undefined);
        if (cancelled) return;

        setShadowJob(job);

        if (isProbablyStale(job)) {
          setError('Job de prédictions shadow probablement bloqué.');
          setIsGeneratingShadow(false);
          setShadowJobId(null);
          return;
        }

        if (job.status === 'success') {
          if (job.result) setShadowResult(job.result as GenerateShadowPredictionsResponse);
          setIsGeneratingShadow(false);
          setShadowJobId(null);
          await reloadAdminState();
          return;
        }

        if (job.status === 'error') {
          setError(job.error ?? 'Génération des prédictions shadow en erreur.');
          setIsGeneratingShadow(false);
          setShadowJobId(null);
          await reloadAdminState();
        }
      } catch (pollError) {
        if (cancelled) return;
        setError(pollError instanceof Error ? pollError.message : 'Suivi du job shadow indisponible.');
        setIsGeneratingShadow(false);
        setShadowJobId(null);
      }
    }

    void pollShadowJob();
    const interval = window.setInterval(pollShadowJob, 2000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [shadowJobId]);

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
        setRefreshJob(runningJob(response.job_id));
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

      if (result.status === 'accepted' && result.job_id) {
        acceptedJob = true;
        setFeatureStoreJobId(result.job_id);
        setFeatureStoreJob(runningJob(result.job_id));
        return;
      }

      if (result.status === 'error') {
        setError(result.detail ?? 'Construction du Feature Store impossible.');
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
        setError(`Erreur entraînement : ${result.detail ?? result.errors?.join(' ') ?? "Construisez d'abord le Feature Store avant d'entraîner le modèle."}`);
      } else if (result.status === 'blocked') {
        setError(
          result.reason ??
          result.dataset_quality?.recommendation_reason ??
          "Construisez d'abord le Feature Store avant d'entraîner le modèle.",
        );
      }

      await reloadAdminState();
    } catch {
      setError("L'entraînement du modèle candidat est indisponible pour le moment.");
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
    setShadowJob(null);
    setShadowJobId(null);

    try {
      const result = await generateShadowPredictions({ limit: shadowLimit, force: shadowForce, view: shadowView });
      setShadowResult(result);

      if (result.status === 'accepted' && result.job_id) {
        setShadowJobId(result.job_id);
        setShadowJob(runningJob(result.job_id));
        return;
      }

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

  async function handlePromoteCandidate() {
    const modelVersion = candidateModel?.model_version ?? promotionEvaluation?.candidate_model_version;
    if (!modelVersion) {
      setError('Aucun modèle candidat disponible pour promotion.');
      return;
    }
    if (!promotionAllowed) {
      setError(`Promotion bloquée : ${promotionReasons.join(' ') || 'gouvernance non validée.'}`);
      return;
    }
    const confirmed = window.confirm('Je confirme vouloir promouvoir ce modèle candidat en production.');
    if (!confirmed) return;

    setIsPromotingModel(true);
    setError(null);
    try {
      const result = await promoteCandidateModel({ modelVersion, confirm: true });
      setPromotionResult(result);
      if (result.status !== 'success') {
        setError(result.detail ?? 'Promotion bloquée par la gouvernance.');
      }
      await reloadAdminState();
    } catch (promotionError) {
      setError(promotionError instanceof Error ? promotionError.message : 'Promotion modèle indisponible.');
    } finally {
      setIsPromotingModel(false);
    }
  }

  async function handleRollbackProduction() {
    const targetModelVersion = rollbackTarget?.model_version;
    if (!targetModelVersion) {
      setError('Aucune ancienne production archivée disponible pour rollback.');
      return;
    }
    const confirmed = window.confirm('Je confirme vouloir restaurer cette ancienne version production.');
    if (!confirmed) return;

    setIsRollingBackModel(true);
    setError(null);
    try {
      const result = await rollbackProductionModel({ targetModelVersion, confirm: true });
      setPromotionResult(result);
      if (result.status !== 'success') {
        setError(result.detail ?? 'Rollback production bloqué.');
      }
      await reloadAdminState();
    } catch (rollbackError) {
      setError(rollbackError instanceof Error ? rollbackError.message : 'Rollback production indisponible.');
    } finally {
      setIsRollingBackModel(false);
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
            <div className="metric"><span>Backend</span><strong>{backendConnected ? 'connecté' : 'non connecté'}</strong></div>
            <div className="metric"><span>API URL</span><strong>{diagnostics?.hasApiUrl ? 'configurée' : 'absente'}</strong></div>
            <div className="metric"><span>Clé admin</span><strong>{diagnostics?.hasAdminApiKey ? 'configurée' : 'absente'}</strong></div>
            <div className="metric"><span>Host API</span><strong>{diagnostics?.apiUrlHost || 'N/A'}</strong></div>
            <div className="metric"><span>Stockage actuel</span><strong><span className={valueBadge(displayedPipelineStorage)}>{formatStorage(displayedPipelineStorage)}</span></strong></div>
            <div className="metric"><span>Source actuelle</span><strong><span className={valueBadge(resolvedRefreshSource)}>{resolvedRefreshSource}</span></strong></div>
            <div className="metric"><span>Matchs importés</span><strong>{refreshMatchesImported}</strong></div>
            <div className="metric"><span>Alertes</span><strong>{adminAlerts?.alerts_count ?? 0}</strong></div>
            <div className="metric"><span>Auto-refresh</span><strong>{diagnostics?.hasCronSecret ? 'actif' : 'inactif'}</strong></div>
            <div className="metric"><span>Cron Vercel</span><strong>{diagnostics?.cronConfigured ? 'configuré' : 'non configuré'}</strong></div>
            <div className="metric"><span>Hourly refresh</span><strong>{workflowStatus?.cron?.hourly_refresh_last_run?.ran_at ?? 'jamais'}</strong></div>
            <div className="metric"><span>Fins de match</span><strong>{workflowStatus?.cron?.match_finished_check_last_run?.ran_at ?? 'jamais'}</strong></div>
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
          <p>Actualise les matchs, équipes, résultats et prédictions depuis la source officielle.</p>
          {!isAdmin && <div className="banner error">Accès admin requis.</div>}
          <button className="button primary" type="button" onClick={handleRefresh} disabled={isRefreshing || !isAdmin}>
            {isRefreshing ? 'Actualisation en cours...' : 'Actualiser les données'}
          </button>
          {currentRefreshJob?.status === 'running' && (
            <div className="banner info">
              Job refresh: {currentRefreshJob.status}
              {currentRefreshJob.duration_ms ? `, durée ${currentRefreshJob.duration_ms} ms` : ''}
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
            <span>Étape 1 : <strong>Données importées</strong></span>
            <span>Étape 2 : <strong>Feature Store</strong></span>
            <span>Étape 3 : <strong>Modèle candidat</strong></span>
            <span>Étape 4 : <strong>Prédictions shadow</strong></span>
            <span>Étape 5 : <strong>Backtesting</strong></span>
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
            <div className="metric"><span>Prochaine étape</span><strong>{displayedNextStep}</strong></div>
          </div>

          <div className="sectionSplit">
            <article>
              <h3>Feature Store</h3>
              <p>Gèle les variables modèle pré-match pour préparer l'entraînement supervisé.</p>
              <button className="button secondary" type="button" onClick={handleBuildFeatureStore} disabled={isBuildingFeatures || !isAdmin}>
                {isBuildingFeatures ? 'Construction...' : 'Construire le Feature Store'}
              </button>
              {currentFeatureStoreJob && <div className="banner info">Statut Feature Store : {currentFeatureStoreJob.status}</div>}
              {featureStoreJobStale && (
                <div className="banner warning">
                  Job Feature Store probablement bloqué.
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
                  <span>Source prédictions <strong>{featureBuildInfo.predictions_source ?? 'inconnue'}</strong></span>
                  <span>Matchs disponibles <strong>{featureBuildInfo.matches_available ?? 0}</strong></span>
                  <span>Prédictions disponibles <strong>{featureBuildInfo.predictions_available ?? 0}</strong></span>
                  <span>Matchs terminés exploitables <strong>{featureBuildInfo.finished_matches_available ?? 0}</strong></span>
                  <span>Nouveaux snapshots créés <strong>{featureBuildInfo.feature_snapshots_built ?? 0}</strong></span>
                  <span>Nouveaux snapshots sauvegardés <strong>{featureBuildInfo.feature_snapshots_saved ?? 0}</strong></span>
                </div>
              )}
              {featureBuildInfo && effectiveFeatureSnapshots > 0 && (featureBuildInfo.feature_snapshots_built ?? 0) === 0 && (
                <div className="banner info">
                  Aucun nouveau snapshot créé : le Feature Store contient déjà des snapshots disponibles.
                </div>
              )}
              {featureBuildInfo?.reason_if_zero_snapshots && (
                <div className="banner warning">{featureBuildInfo.reason_if_zero_snapshots}</div>
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
                  <span>Version modèle <strong>{trainingReport.model_version ?? 'N/A'}</strong></span>
                  <span>Type modèle <strong>{trainingReport.model_type ?? modelType}</strong></span>
                  <span>Lignes chargées <strong>{trainingReport.rows_loaded ?? 0}</strong></span>
                  <span>Lignes utilisées <strong>{trainingReport.rows_used ?? 0}</strong></span>
                  <span>Lignes validées <strong>{trainingReport.rows_after_validation ?? trainingReport.rows_used ?? 0}</strong></span>
                  <span>Features utilisées <strong>{trainingFeatureCount(trainingReport)}</strong></span>
                  <span>Précision <strong>{trainingReport.accuracy ?? 'N/A'}</strong></span>
                  <span>Log loss <strong>{trainingReport.log_loss ?? 'N/A'}</strong></span>
                  <span>Brier score <strong>{trainingReport.brier_score ?? trainingReport.brier_score_1x2 ?? 'N/A'}</strong></span>
                  <span>Distribution target <strong>{Object.entries(trainingReport.target_distribution ?? {}).map(([key, value]) => `${key}:${value}`).join(', ') || 'N/A'}</strong></span>
                </div>
              )}
              {(trainingReport?.warnings?.length ?? 0) > 0 && (
                <div className="banner warning">{trainingReport?.warnings?.join(' ')}</div>
              )}
              {(trainingReport?.errors?.length ?? 0) > 0 && (
                <div className="banner error">Erreur entraînement : {trainingReport?.errors?.join(' ')}</div>
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
                  {shadowResult.status === 'accepted' && <span>Job shadow <strong>en cours</strong></span>}
                  <span>Prédictions générées <strong>{shadowResult.shadow_predictions_generated ?? 0}</strong></span>
                  <span>Prédictions sauvegardées <strong>{shadowResult.shadow_predictions_saved ?? 0}</strong></span>
                  <span>Désaccords élevés <strong>{shadowResult.high_disagreement_count ?? 0}</strong></span>
                </div>
              )}
              {shadowJob?.status === 'running' && <div className="banner">Génération shadow en cours...</div>}
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

          <article className="sectionAnchor" id="model-promotion">
            <h3>Promotion modèle</h3>
            <div className="compactDataGrid four">
              <div className="metric"><span>Production actuelle</span><strong>{productionModel?.model_version ?? modelGovernance?.production_model.version ?? 'elo-poisson-calibrated-v1'}</strong></div>
              <div className="metric"><span>Production verrouillée</span><strong>{modelGovernance?.production_model.locked ? 'oui' : 'non'}</strong></div>
              <div className="metric"><span>Candidat actuel</span><strong>{candidateModel?.model_version ?? promotionEvaluation?.candidate_model_version ?? 'N/A'}</strong></div>
              <div className="metric"><span>Statut candidat</span><strong>{candidateModel?.status ?? modelGovernance?.candidate_model.status ?? 'unknown'}</strong></div>
              <div className="metric"><span>Lignes candidat</span><strong>{candidateModel?.rows_used ?? modelGovernance?.candidate_model.rows_used ?? 0}</strong></div>
              <div className="metric"><span>Accuracy candidat</span><strong>{candidateModel?.accuracy ?? modelGovernance?.candidate_model.accuracy ?? 'N/A'}</strong></div>
              <div className="metric"><span>Log loss candidat</span><strong>{candidateModel?.log_loss ?? promotionEvaluation?.metrics?.candidate_log_loss ?? 'N/A'}</strong></div>
              <div className="metric"><span>Brier candidat</span><strong>{candidateModel?.brier_score ?? promotionEvaluation?.metrics?.candidate_brier_score ?? 'N/A'}</strong></div>
              <div className="metric"><span>Readiness</span><strong>{promotionEvaluation?.readiness ?? modelGovernance?.promotion_readiness.level ?? 'unknown'}</strong></div>
              <div className="metric"><span>Promotion autorisée</span><strong>{promotionAllowed ? 'oui' : 'non'}</strong></div>
              <div className="metric"><span>Évaluables requis</span><strong>{promotionEvaluation?.requirements.current_evaluable_predictions ?? 0}/{promotionEvaluation?.requirements.minimum_evaluable_predictions ?? 30}</strong></div>
              <div className="metric"><span>Dernière promotion</span><strong>{learningMonitoring?.last_promotion_at ?? 'N/A'}</strong></div>
            </div>

            {promotionReasons.length > 0 && (
              <div className="banner warning">
                <strong>Raisons de blocage : </strong>{promotionReasons.join(' ')}
              </div>
            )}
            {promotionResult && (
              <div className={promotionResult.status === 'success' ? 'banner info' : 'banner warning'}>
                {promotionResult.status === 'success'
                  ? `Action modèle réussie. Audit ${promotionResult.audit_id ?? 'N/A'}.`
                  : promotionResult.detail ?? 'Action modèle bloquée.'}
              </div>
            )}
            <div className="quickActions">
              <button className="button primary" type="button" onClick={handlePromoteCandidate} disabled={!isAdmin || !promotionAllowed || isPromotingModel}>
                {isPromotingModel ? 'Promotion...' : 'Promouvoir le candidat'}
              </button>
              <button className="button secondary" type="button" onClick={handleRollbackProduction} disabled={!isAdmin || !rollbackTarget || isRollingBackModel}>
                {isRollingBackModel ? 'Rollback...' : `Rollback production${rollbackTarget ? ` vers ${rollbackTarget.model_version}` : ''}`}
              </button>
            </div>

            <h4>Audit récent</h4>
            <div className="dataList">
              {(promotionAudit?.events ?? []).length === 0 ? (
                <span>Aucun événement de promotion <strong>0</strong></span>
              ) : promotionAudit?.events.slice(0, 5).map((event) => (
                <span key={event.id}>{event.action} <strong>{event.result ?? 'unknown'} - {event.new_production_model_version ?? event.candidate_model_version ?? 'N/A'}</strong></span>
              ))}
            </div>
          </article>

          <article className="sectionAnchor" id="shadow-backtesting">
            <h3>Backtesting shadow</h3>
            <div className="compactDataGrid four">
              <div className="metric"><span>Candidat</span><strong>{shadowBacktesting?.candidate_model_version ?? modelVersions?.latest_candidate_model?.model_version ?? 'N/A'}</strong></div>
              <div className="metric"><span>Production</span><strong>{shadowBacktesting?.production_model_version ?? 'elo-poisson-calibrated-v1'}</strong></div>
              <div className="metric"><span>Shadow total</span><strong>{shadowBacktesting?.shadow_predictions_total ?? workflowStatus?.shadow_predictions.count ?? 0}</strong></div>
              <div className="metric"><span>Évaluables</span><strong>{shadowBacktesting?.evaluable_predictions ?? shadowBacktesting?.evaluated_matches ?? 0}</strong></div>
              <div className="metric"><span>En attente</span><strong>{shadowBacktesting?.pending_predictions ?? workflowStatus?.shadow_backtesting.pending_predictions ?? 0}</strong></div>
              <div className="metric"><span>Accuracy candidat</span><strong>{shadowBacktesting?.metrics?.accuracy ?? (shadowBacktesting?.evaluated_matches ? shadowBacktesting.shadow_accuracy : 'N/A')}</strong></div>
              <div className="metric"><span>Log loss candidat</span><strong>{shadowBacktesting?.metrics?.log_loss ?? 'N/A'}</strong></div>
              <div className="metric"><span>Brier candidat</span><strong>{shadowBacktesting?.metrics?.brier_score ?? shadowBacktesting?.shadow_average_brier ?? 'N/A'}</strong></div>
              <div className="metric"><span>ROI théorique</span><strong>{shadowBacktesting?.metrics?.roi_theoretical ?? 'N/A'}</strong></div>
              <div className="metric"><span>Delta accuracy</span><strong>{shadowBacktesting?.comparison?.delta_accuracy ?? 'N/A'}</strong></div>
              <div className="metric"><span>Delta log loss</span><strong>{shadowBacktesting?.comparison?.delta_log_loss ?? 'N/A'}</strong></div>
              <div className="metric"><span>Statut gouvernance</span><strong>{shadowBacktesting?.recommendation?.status ?? shadowBacktesting?.activation_recommendation ?? 'collect_more_data'}</strong></div>
            </div>
            {(shadowBacktesting?.evaluable_predictions ?? shadowBacktesting?.evaluated_matches ?? 0) === 0 ? (
              <div className="banner info">
                Les prédictions shadow sont générées, mais aucun match n'est encore évaluable. Attendez des résultats terminés pour calculer le backtesting.
              </div>
            ) : (
              <div className="metricTable">
                <div className="metricTableRow header">
                  <span>Match</span>
                  <span>Réel</span>
                  <span>Candidat</span>
                  <span>Production</span>
                </div>
                {(shadowBacktesting?.evaluated_match_rows ?? shadowBacktesting?.recent_evaluations ?? []).slice(0, 5).map((item) => (
                  <div className="metricTableRow bucketRow" key={item.match_id}>
                    <span>{item.home_team ?? item.match_id} {item.away_team ? `- ${item.away_team}` : ''}</span>
                    <strong>{item.actual_result}</strong>
                    <strong>{item.shadow_pick ?? 'N/A'}</strong>
                    <strong>{item.production_pick ?? 'N/A'}</strong>
                  </div>
                ))}
              </div>
            )}
            {shadowBacktesting?.recommendation?.reason && (
              <div className="banner warning">{shadowBacktesting.recommendation.reason}</div>
            )}
          </article>
        </section>

        <section className="card sectionAnchor" id="learning-engine">
          <div className="cardTop">
            <div>
              <p className="eyebrow">Auto-learning</p>
              <h2>Feedback, calibration et versions</h2>
            </div>
            <span className="badge">{calibrationReport?.calibration_version ?? 'calibration-buckets-v1'}</span>
          </div>
          <div className="compactDataGrid four">
            <div className="metric"><span>Matchs évalués</span><strong>{learningFeedback?.evaluated_matches ?? 0}</strong></div>
            <div className="metric"><span>Accuracy feedback</span><strong>{learningFeedback?.accuracy ?? 0}%</strong></div>
            <div className="metric"><span>Log loss</span><strong>{learningFeedback?.log_loss ?? 'N/A'}</strong></div>
            <div className="metric"><span>Brier score</span><strong>{learningFeedback?.brier_score ?? 'N/A'}</strong></div>
            <div className="metric"><span>ROI théorique</span><strong>{learningFeedback?.theoretical_roi ?? 'N/A'}</strong></div>
            <div className="metric"><span>Facteur calibration</span><strong>{calibrationReport?.global_calibration_factor ?? 1}</strong></div>
            <div className="metric"><span>Sample calibration</span><strong>{calibrationReport?.sample_size ?? 0}</strong></div>
            <div className="metric"><span>Versions suivies</span><strong>{modelVersions?.versions_count ?? modelVersions?.versions.length ?? 0}</strong></div>
            <div className="metric"><span>Storage versions</span><strong>{modelVersions?.storage ?? learningMonitoring?.storage ?? 'inconnu'}</strong></div>
          </div>

          <div className="sectionSplit">
            <article>
              <h3>Monitoring learning</h3>
              <div className="dataList">
                <span>Statut <strong>{learningMonitoring?.status ?? 'unknown'}</strong></span>
                <span>Stockage <strong>{learningMonitoring?.storage ?? modelVersions?.storage ?? 'inconnu'}</strong></span>
                <span>Feedback <strong>{learningMonitoring?.feedback_status ?? 'unknown'}</strong></span>
                <span>Calibration <strong>{learningMonitoring?.latest_calibration_version ?? calibrationReport?.calibration_version ?? 'N/A'}</strong></span>
                <span>Production <strong>{learningMonitoring?.production_model_version ?? modelVersions?.current_production_model?.model_version ?? 'N/A'}</strong></span>
                <span>Candidat <strong>{learningMonitoring?.latest_candidate_model_version ?? modelVersions?.latest_candidate_model?.model_version ?? 'N/A'}</strong></span>
              </div>
              {(learningMonitoring?.alerts ?? []).length > 0 && (
                <div className="banner warning">{learningMonitoring?.alerts.join(' ')}</div>
              )}
              {learningMonitoring?.next_best_action && (
                <Link className="button secondary" href={learningMonitoring.next_best_action.href}>
                  {learningMonitoring.next_best_action.label}
                </Link>
              )}
            </article>
            <article>
              <h3>Modèle candidat vs production</h3>
              <div className="dataList">
                <span>Production <strong>{modelVersions?.current_production_model?.model_version ?? 'elo-poisson-calibrated-v1'}</strong></span>
                <span>Candidat <strong>{modelVersions?.latest_candidate_model?.model_version ?? 'N/A'}</strong></span>
                <span>Lignes candidat <strong>{modelVersions?.latest_candidate_model?.rows_used ?? 0}</strong></span>
                <span>Accuracy candidat <strong>{modelVersions?.latest_candidate_model?.accuracy ?? 'N/A'}</strong></span>
                <span>Log loss candidat <strong>{modelVersions?.latest_candidate_model?.log_loss ?? 'N/A'}</strong></span>
                <span>Brier candidat <strong>{modelVersions?.latest_candidate_model?.brier_score ?? 'N/A'}</strong></span>
              </div>
            </article>
          </div>

          <div className="sectionSplit">
            <article>
              <h3>Performance par marché</h3>
              <div className="dataList">
                {Object.entries(learningFeedback?.performance_by_market ?? {}).length === 0 ? (
                  <span>Aucune métrique marché disponible <strong>0</strong></span>
                ) : Object.entries(learningFeedback?.performance_by_market ?? {}).map(([market, row]) => (
                  <span key={market}>{market} <strong>{row.accuracy}% / ROI {row.theoretical_roi ?? 'N/A'}</strong></span>
                ))}
              </div>
            </article>
            <article>
              <h3>Erreurs fréquentes</h3>
              <div className="dataList">
                {(learningFeedback?.frequent_errors ?? []).length === 0 ? (
                  <span>Aucune erreur fréquente visible <strong>0</strong></span>
                ) : learningFeedback?.frequent_errors.slice(0, 5).map((item) => (
                  <span key={item.error}>{item.error} <strong>{item.count}</strong></span>
                ))}
              </div>
            </article>
          </div>

          <div className="metricTable">
            <div className="metricTableRow header">
              <span>Bucket confiance</span>
              <span>Prédit</span>
              <span>Réel</span>
              <span>Facteur</span>
            </div>
            {(calibrationReport?.buckets ?? []).map((bucket) => (
              <div className="metricTableRow bucketRow" key={bucket.bucket}>
                <span>{bucket.bucket}</span>
                <strong>{Math.round(bucket.predicted_probability * 100)}%</strong>
                <strong>{Math.round(bucket.observed_success_rate * 100)}%</strong>
                <strong>{bucket.calibration_factor}</strong>
              </div>
            ))}
          </div>

          <div className="banner info">
            Recommandations IA : garder le candidat en shadow tant que les règles de promotion ne sont pas toutes validées.
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
            <span>Snapshots sauvegardés <strong>{stableSnapshotsSaved}</strong></span>
            <span>Snapshots Feature Store <strong>{stableFeatureSnapshotsSaved}</strong></span>
            <span>Lignes entraînables <strong>{stableTrainingRows}</strong></span>
            <span>Dernière actualisation <strong>{formatDate(stableRefreshInfo?.last_refresh_at)}</strong></span>
            <span>Compétitions configurées <strong>{stableRefreshInfo?.configured_competitions?.join(', ') || 'FL1, CL'}</strong></span>
          </div>
          {currentRefreshJob?.status === 'running' && (
            <div className="banner info">
              Job en cours : {currentRefreshJob.job_id ?? 'N/A'}, {currentRefreshJob.status}
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


