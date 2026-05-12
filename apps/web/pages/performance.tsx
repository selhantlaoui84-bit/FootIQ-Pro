import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { InfoTooltip } from '~/components/InfoTooltip';
import { TeamIdentity } from '~/components/TeamIdentity';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import {
  getBacktesting,
  getAssistantDailyBrief,
  getUserBetSummary,
  getCalibrationReport,
  getFeatureQualityReport,
  getFeatureSummary,
  getLearningFeedback,
  getLearningMonitoring,
  getMlFeatureImportance,
  getHybridEngineSummary,
  getHybridSummary,
  getExplainabilitySummary,
  getMlComparison,
  getMlStatus,
  getMlShadowBacktesting,
  getMlShadowSummary,
  getModelComparison,
  getModels,
  getModelGovernance,
  getModelVersionsRegistry,
  getPipelineJobs,
  getPipelineStatus,
  getPerformance,
  getValueBets,
} from '~/lib/api';
import type {
  BacktestingReport,
  BettingAssistantResponse,
  UserBetSummary,
  ValueBetResponse,
  CalibrationReport,
  DatasetQualityReport,
  FeatureImportanceRow,
  FeatureSummary,
  GovernanceGate,
  HybridEngineSummary,
  ExplainabilitySummary,
  HybridSummary,
  MlComparison,
  MlStatus,
  MlShadowSummary,
  MlShadowBacktesting,
  ModelGovernanceReport,
  ModelComparison,
  ModelVersionsResponse,
  LearningFeedbackReport,
  LearningMonitoringReport,
  ModelsMetadata,
  PerformanceMetrics,
  PipelineJobsResponse,
  PipelineStatus,
  TrainingReport,
} from '~/lib/mock-data';
import {
  mockBacktestingReport,
  mockCalibrationReport,
  mockExplainabilitySummary,
  mockFeatureQualityReport,
  mockFeatureSummary,
  mockHybridEngineSummary,
  mockHybridSummary,
  mockMlComparison,
  mockMlFeatureImportance,
  mockMlShadowBacktesting,
  mockMlShadowSummary,
  mockMlStatus,
  mockModelComparison,
  mockModelGovernance,
  mockModelVersionsResponse,
  mockLearningFeedbackReport,
  mockLearningMonitoringReport,
  mockModelsMetadata,
  mockPipelineJobs,
  mockPipelineStatus,
  performanceMetrics,
} from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type PerformanceProps = {
  performance: PerformanceMetrics;
  backtesting: BacktestingReport;
  models: ModelsMetadata;
  comparison: ModelComparison;
  featureSummary: FeatureSummary;
  featureQuality: DatasetQualityReport;
  mlStatus: MlStatus;
  mlComparison: MlComparison;
  modelGovernance: ModelGovernanceReport;
  shadowSummary: MlShadowSummary;
  shadowBacktesting: MlShadowBacktesting;
  hybridSummary: HybridSummary;
  hybridEngineSummary: HybridEngineSummary;
  explainabilitySummary: ExplainabilitySummary;
  featureImportance: FeatureImportanceRow[];
  learningFeedback: LearningFeedbackReport;
  calibrationReport: CalibrationReport;
  modelVersions: ModelVersionsResponse;
  learningMonitoring: LearningMonitoringReport;
};

type LearningPageState = Pick<
  PerformanceProps,
  | 'featureSummary'
  | 'featureQuality'
  | 'shadowBacktesting'
  | 'modelGovernance'
  | 'learningFeedback'
  | 'calibrationReport'
  | 'modelVersions'
  | 'learningMonitoring'
>;

type PipelinePageState = {
  pipelineStatus: PipelineStatus;
  pipelineJobs: PipelineJobsResponse;
};

export const getStaticProps: GetStaticProps<PerformanceProps> = async () => {
  const fallback = {
    performance: performanceMetrics,
    backtesting: mockBacktestingReport,
    models: mockModelsMetadata,
    comparison: mockModelComparison,
    featureSummary: mockFeatureSummary,
    featureQuality: mockFeatureQualityReport,
    mlStatus: mockMlStatus,
    mlComparison: mockMlComparison,
    shadowSummary: mockMlShadowSummary,
    shadowBacktesting: mockMlShadowBacktesting,
    hybridSummary: mockHybridSummary,
    hybridEngineSummary: mockHybridEngineSummary,
    explainabilitySummary: mockExplainabilitySummary,
    featureImportance: mockMlFeatureImportance,
    modelGovernance: mockModelGovernance,
    learningFeedback: mockLearningFeedbackReport,
    calibrationReport: mockCalibrationReport,
    modelVersions: mockModelVersionsResponse,
    learningMonitoring: mockLearningMonitoringReport,
  };

  const load = async <T,>(label: string, promise: Promise<T>, fallbackValue: T): Promise<T> => {
    try {
      return await promise;
    } catch (error) {
      console.error(`Performance ISR fallback for ${label}:`, error);
      return fallbackValue;
    }
  };

  const [
    performance,
    backtesting,
    models,
    comparison,
    featureSummary,
    featureQuality,
    mlStatus,
    mlComparison,
    shadowSummary,
    shadowBacktesting,
    hybridSummary,
    hybridEngineSummary,
    explainabilitySummary,
    featureImportance,
    modelGovernance,
    learningFeedback,
    calibrationReport,
    modelVersions,
    learningMonitoring,
  ] = await Promise.all([
    load('performance', getPerformance(), fallback.performance),
    load('backtesting', getBacktesting(), fallback.backtesting),
    load('models', getModels(), fallback.models),
    load('comparison', getModelComparison(), fallback.comparison),
    load('featureSummary', Promise.resolve(fallback.featureSummary), fallback.featureSummary),
    load('featureQuality', Promise.resolve(fallback.featureQuality), fallback.featureQuality),
    load('mlStatus', getMlStatus(), fallback.mlStatus),
    load('mlComparison', getMlComparison(), fallback.mlComparison),
    load('shadowSummary', getMlShadowSummary(), fallback.shadowSummary),
    load('shadowBacktesting', Promise.resolve(fallback.shadowBacktesting), fallback.shadowBacktesting),
    load('hybridSummary', getHybridSummary(), fallback.hybridSummary),
    load('hybridEngineSummary', getHybridEngineSummary(), fallback.hybridEngineSummary),
    load('explainabilitySummary', getExplainabilitySummary(200, 'upcoming'), fallback.explainabilitySummary),
    load('featureImportance', getMlFeatureImportance(), fallback.featureImportance),
    load('modelGovernance', Promise.resolve(fallback.modelGovernance), fallback.modelGovernance),
    load('learningFeedback', Promise.resolve(fallback.learningFeedback), fallback.learningFeedback),
    load('calibrationReport', Promise.resolve(fallback.calibrationReport), fallback.calibrationReport),
    load('modelVersions', Promise.resolve(fallback.modelVersions), fallback.modelVersions),
    load('learningMonitoring', Promise.resolve(fallback.learningMonitoring), fallback.learningMonitoring),
  ]);

  return {
    props: {
      performance,
      backtesting,
      models,
      comparison,
      featureSummary,
      featureQuality,
      mlStatus,
      mlComparison,
      shadowSummary,
      shadowBacktesting,
      hybridSummary,
      hybridEngineSummary,
      explainabilitySummary,
      featureImportance,
      modelGovernance,
      learningFeedback,
      calibrationReport,
      modelVersions,
      learningMonitoring,
    },
    revalidate: 120,
  };
};

export default function PerformancePage({
  performance,
  backtesting,
  models,
  comparison,
  featureSummary: initialFeatureSummary,
  featureQuality: initialFeatureQuality,
  mlStatus,
  mlComparison,
  shadowSummary,
  shadowBacktesting: initialShadowBacktesting,
  hybridSummary,
  hybridEngineSummary,
  explainabilitySummary,
  featureImportance,
  modelGovernance: initialModelGovernance,
  learningFeedback: initialLearningFeedback,
  calibrationReport: initialCalibrationReport,
  modelVersions: initialModelVersions,
  learningMonitoring: initialLearningMonitoring,
}: PerformanceProps) {
  const [learningState, setLearningState] = useState<LearningPageState>({
    featureSummary: initialFeatureSummary,
    featureQuality: initialFeatureQuality,
    shadowBacktesting: initialShadowBacktesting,
    modelGovernance: initialModelGovernance,
    learningFeedback: initialLearningFeedback,
    calibrationReport: initialCalibrationReport,
    modelVersions: initialModelVersions,
    learningMonitoring: initialLearningMonitoring,
  });
  const [pipelineState, setPipelineState] = useState<PipelinePageState>({
    pipelineStatus: mockPipelineStatus,
    pipelineJobs: mockPipelineJobs,
  });

  useEffect(() => {
    let active = true;

    async function loadLearningState() {
      const [
        featureSummaryResult,
        featureQualityResult,
        shadowBacktestingResult,
        modelGovernanceResult,
        learningFeedbackResult,
        calibrationResult,
        modelVersionsResult,
        monitoringResult,
        pipelineStatusResult,
        pipelineJobsResult,
      ] = await Promise.allSettled([
        getFeatureSummary(),
        getFeatureQualityReport(1000),
        getMlShadowBacktesting(2000),
        getModelGovernance(),
        getLearningFeedback(),
        getCalibrationReport(),
        getModelVersionsRegistry(),
        getLearningMonitoring(),
        getPipelineStatus(),
        getPipelineJobs(8),
      ]);

      if (!active) return;

      setLearningState((current) => ({
        featureSummary: valueOrCurrent(featureSummaryResult, current.featureSummary),
        featureQuality: valueOrCurrent(featureQualityResult, current.featureQuality),
        shadowBacktesting: valueOrCurrent(shadowBacktestingResult, current.shadowBacktesting),
        modelGovernance: valueOrCurrent(modelGovernanceResult, current.modelGovernance),
        learningFeedback: valueOrCurrent(learningFeedbackResult, current.learningFeedback),
        calibrationReport: valueOrCurrent(calibrationResult, current.calibrationReport),
        modelVersions: valueOrCurrent(modelVersionsResult, current.modelVersions),
        learningMonitoring: valueOrCurrent(monitoringResult, current.learningMonitoring),
      }));
      setPipelineState((current) => ({
        pipelineStatus: valueOrCurrent(pipelineStatusResult, current.pipelineStatus),
        pipelineJobs: valueOrCurrent(pipelineJobsResult, current.pipelineJobs),
      }));
    }

    void loadLearningState();

    return () => {
      active = false;
    };
  }, []);

  const {
    featureSummary,
    featureQuality,
    shadowBacktesting,
    modelGovernance,
    learningFeedback,
    calibrationReport,
    modelVersions,
    learningMonitoring,
  } = learningState;

  return (
    <ProtectedRoute>
      <Layout>
        <AnalysisCommandCenter
          performance={performance}
          models={models}
          featureSummary={featureSummary}
          featureQuality={featureQuality}
          shadowBacktesting={shadowBacktesting}
          modelGovernance={modelGovernance}
          learningFeedback={learningFeedback}
          calibrationReport={calibrationReport}
          modelVersions={modelVersions}
          learningMonitoring={learningMonitoring}
          pipelineStatus={pipelineState.pipelineStatus}
          pipelineJobs={pipelineState.pipelineJobs}
        />
      </Layout>
    </ProtectedRoute>
  );

  /*
  const report = {
    ...backtesting,
    model_version: performance.current_model_version ?? performance.model_version ?? models.current_model_version ?? backtesting.model_version,
    evaluated_matches: performance.evaluated_matches ?? backtesting.evaluated_matches,
    result_accuracy: performance.result_accuracy ?? backtesting.result_accuracy,
    over_2_5_accuracy: performance.over_2_5_accuracy ?? backtesting.over_2_5_accuracy,
    btts_accuracy: performance.btts_accuracy ?? backtesting.btts_accuracy,
    average_brier_score: performance.average_brier_score ?? backtesting.average_brier_score,
    calibration_score: performance.calibration_score ?? backtesting.calibration_score,
    confidence_buckets: performance.confidence_buckets ?? backtesting.confidence_buckets,
    competition_breakdown: performance.competition_breakdown ?? backtesting.competition_breakdown,
    previous_model_version: performance.previous_model_version ?? backtesting.previous_model_version,
    comparison_note: performance.model_comparison_note ?? performance.comparison_note ?? comparison.note ?? backtesting.comparison_note,
    calibration_applied: performance.calibration_applied ?? backtesting.calibration_applied,
    note: performance.note ?? backtesting.note,
  };
  const productionEvaluated = Number(learningFeedback.evaluated_matches ?? report.evaluated_matches ?? 0);
  const productionAccuracy = productionEvaluated > 0 ? `${learningFeedback.accuracy ?? report.result_accuracy}%` : 'Données insuffisantes';

  const items = [
    ['Modèle', report.model_version],
    ['Modèle précédent', report.previous_model_version ?? 'elo-poisson-v1'],
    ['Calibration', report.calibration_applied ? 'active' : 'active'],
    ['Prédictions suivies', performance.predictions_tracked ?? performance.tracked],
    ['Matchs évalués', productionEvaluated || 'Données insuffisantes'],
    ['Précision résultat', productionAccuracy],
    ['Précision over 2.5', `${report.over_2_5_accuracy}%`],
    ['Précision BTTS', `${report.btts_accuracy}%`],
    ['Score Brier moyen', report.average_brier_score],
    ['Score de calibration', `${report.calibration_score}/100`],
  ];
  const competitions = Object.entries(report.competition_breakdown ?? {});
  const modelRows = Object.entries(performance.model_versions ?? comparison.model_versions ?? {});
  const bestByBrier = performance.best_model_by_brier ?? comparison.best_model_by_brier;
  const bestByAccuracy = performance.best_model_by_accuracy ?? comparison.best_model_by_accuracy;
  const performanceSnapshots = Number(performance.feature_snapshots_count ?? performance.snapshots_count ?? 0);
  const summarySnapshots = Number(featureSummary.snapshots_count ?? 0);
  const performanceTrainableRows = Number(performance.training_rows_available ?? 0);
  const summaryTrainableRows = Number(featureSummary.with_target_count ?? 0);
  const featureStore = {
    ...featureSummary,
    snapshots_count: Math.max(performanceSnapshots, summarySnapshots),
    with_target_count: Math.max(performanceTrainableRows, summaryTrainableRows),
    target_coverage: Math.max(Number(performance.target_coverage ?? 0), Number(featureSummary.target_coverage ?? 0)),
  };
  const featureStoreReady = performance.feature_store_ready ?? featureStore.snapshots_count > 0;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://footiq-pro-production.up.railway.app';
  const candidate = performance.ml_candidate ?? mlStatus.latest_candidate;
  const hybrid = performance.hybrid_summary ?? hybridSummary;
  const hybridEngine = performance.hybrid_engine_summary ?? hybridEngineSummary;
  const explainability = performance.explainability_summary ?? explainabilitySummary;
  const rawDatasetQuality = performance.dataset_quality ?? featureQuality;
  const datasetQuality = buildEffectiveDatasetQuality(rawDatasetQuality, featureStore);
  const candidateImportance = candidate.feature_importance?.length ? candidate.feature_importance : featureImportance;
  const latestCandidate = modelVersions.latest_candidate_model;
  const candidateVersion = latestCandidate?.model_version ?? learningMonitoring.latest_candidate_model_version ?? candidate.model_version;
  const candidateRowsUsed = latestCandidate?.rows_used ?? candidate.rows_used;
  const candidateFeaturesUsed = latestCandidate?.features_used ?? candidate.features_used;
  const candidateAccuracy = latestCandidate?.accuracy ?? candidate.accuracy;
  const candidateLogLoss = latestCandidate?.log_loss ?? candidate.log_loss;
  const candidateBrier = latestCandidate?.brier_score ?? candidate.brier_score ?? candidate.brier_score_1x2;
  const shadowEvaluable = Number(shadowBacktesting.evaluable_predictions ?? shadowBacktesting.evaluated_matches ?? 0);
  const shadowPending = Number(shadowBacktesting.pending_predictions ?? 0);
  const shadowInvalid = Number(shadowBacktesting.invalid_predictions ?? 0);
  const shadowTotal = Number(shadowBacktesting.shadow_predictions_total ?? 0);
  const shadowHasMetrics = shadowEvaluable > 0;
  const shadowRecommendation = shadowBacktesting.recommendation?.reason ?? shadowBacktesting.recommendation_reason;
  const pipelineBadge =
    shadowTotal > 0 && shadowEvaluable === 0
      ? 'Shadow en observation'
      : shadowEvaluable < (shadowBacktesting.recommendation?.minimum_required ?? 30)
        ? 'Données insuffisantes'
        : 'Revue possible';
  const unavailableMetric = shadowTotal > 0 ? 'En attente de résultats' : 'Données insuffisantes';

  const governance = performance.model_governance ?? modelGovernance;
  const effectiveGovernanceGates = buildEffectiveGovernanceGates({
    gates: governance.governance_gates,
    featureStore,
    datasetQuality,
    candidate,
    shadowSummary: performance.ml_shadow_summary ?? shadowSummary,
    shadowBacktesting,
    hybridEngine,
  });
  const effectiveBlockingReasons = governance.promotion_readiness.blocking_reasons.filter((reason) => {
    const normalized = reason.toLowerCase();
    if (normalized.includes('dataset') && effectiveGovernanceGates.dataset_quality?.passed) return false;
    if (normalized.includes('entraîn') && effectiveGovernanceGates.training?.passed) return false;
    if (normalized.includes('shadow') && effectiveGovernanceGates.shadow_backtesting?.passed) return false;
    if (normalized.includes('hybride') && effectiveGovernanceGates.hybrid_review?.passed) return false;
    return true;
  });
  const effectiveNextActions =
    effectiveBlockingReasons.length === 0
      ? [
          'Validation simulée disponible : relancer un contrôle qualité puis promouvoir manuellement si les métriques production sont satisfaisantes.',
        ]
      : governance.promotion_readiness.next_actions;
  const gateLabels: Record<string, string> = {
  dataset_quality: 'Qualité dataset',
  training: 'Entraînement',
  shadow_backtesting: 'Backtesting shadow',
  monitoring: 'Monitoring',
  hybrid_review: 'Revue hybride',
};

  return (
    <ProtectedRoute>
      <Layout>
        <section className="pageHeader premiumPageIntro">
          <p className="eyebrow">Analyse modèle</p>
          <h1>Analyse</h1>
          <p>Suivi intelligent du modèle, du backtesting shadow et de la gouvernance.</p>
          <div className="sourceStrip">
            <span>{pipelineBadge}</span>
            <span>Production : {learningMonitoring.production_model_version ?? governance.production_model.version}</span>
            <span>Candidat : {candidateVersion ?? 'non entraîné'}</span>
          </div>
        </section>

        <section className="analyticsShowcase dataOnlyShowcase">
          <article className="premiumPanel">
            <div className="panelHeading">
              <span>Précision résultat</span>
            </div>
            <strong className="landingMetric">{productionAccuracy}</strong>
            <DataBar label="Calibration" value={report.calibration_score} max={100} suffix="/100" />
          </article>
          <article className="premiumPanel">
            <div className="panelHeading">
              <span>Couverture Feature Store</span>
            </div>
            <strong className="landingMetric">{featureStore.target_coverage ?? 0}%</strong>
            <DataBar label="Lignes entraînables" value={featureStore.with_target_count} max={Math.max(featureStore.snapshots_count, 1)} />
          </article>
          <article className="premiumPanel">
            <div className="panelHeading">
              <span>Backtesting shadow</span>
            </div>
            <strong className="landingMetric">{shadowHasMetrics ? shadowEvaluable : unavailableMetric}</strong>
            <span className="muted">{shadowTotal} shadow, {shadowPending} en attente</span>
          </article>
        </section>

        <section className="metrics">
          {items.map(([label, value]) => (
            <Link className="metric clickable-card" href={label === 'Prédictions suivies' ? '/predictions' : '/performance'} key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </Link>
          ))}
        </section>


        <section className="sectionSplit sectionAnchor" id="model-comparison">
          <article className="card accent">
            <p className="eyebrow">Modèle actuel</p>
            <h2>{models.current_model_version}</h2>
            <div className="dataList">
              <span>Précédent <strong>{models.previous_model_version}</strong></span>
              <span>Famille <strong>{models.family}</strong></span>
              <span>Calibration <strong>{models.calibration ? 'active' : 'inactive'}</strong></span>
              <span>Snapshots <strong>{featureStore.snapshots_count ?? 0}</strong></span>
            </div>
            <p>{models.description}</p>
          </article>
          <article className="card">
            <h2>Meilleur modèle</h2>
            <div className="dataList">
              <span>Meilleur Brier <strong>{bestByBrier ?? 'N/A'}</strong></span>
              <span>Meilleure précision <strong>{bestByAccuracy ?? 'N/A'}</strong></span>
            </div>
            <p>Un snapshot conserve ce que le modèle pensait avant évaluation. Cela permet une comparaison juste dans le temps.</p>
          </article>
        </section>

        <section className="card">
          <h2>Comparaison des modèles</h2>
          {modelRows.length === 0 ? (
            <div className="emptyState">Aucun snapshot de prédiction disponible. Lancez une actualisation admin avec PostgreSQL actif.</div>
          ) : (
            <div className="metricTable">
              <div className="metricTableRow header">
                <span>Modèle</span>
                <span>Snapshots</span>
                <span>Précision</span>
                <span>Brier</span>
              </div>
              {modelRows.map(([modelVersion, row]) => (
                <div className="metricTableRow bucketRow" key={modelVersion}>
                  <span>{modelVersion}</span>
                  <strong>{row.snapshots}</strong>
                  <strong>{row.result_accuracy}%</strong>
                  <strong>{row.average_brier_score}</strong>
                </div>
              ))}
            </div>
          )}
        </section>


<section className="card sectionAnchor" id="model-governance">
  <div className="cardTop">
    <div>
      <p className="eyebrow">Gouvernance des modèles</p>
      <h2>Registre et critères de promotion</h2>
    </div>
    <span className={`badge readinessScore ${governance.promotion_readiness.level}`}>
      {governance.promotion_readiness.level}
    </span>
  </div>

  <p>
    Cette gouvernance empêche toute bascule automatique du ML vers la production. Le modèle officiel reste verrouillé
    tant que les critères ne sont pas validés manuellement.
  </p>

  <div className="compactDataGrid four">
    <div className="metric">
      <span>Modèle production</span>
      <strong>{governance.production_model.version}</strong>
    </div>
    <div className="metric">
      <span>Production verrouillée</span>
      <strong>{governance.production_model.locked ? 'oui' : 'non'}</strong>
    </div>
    <div className="metric">
      <span>Modèle candidat</span>
      <strong>{governance.candidate_model.version ?? 'N/A'}</strong>
    </div>
    <div className="metric">
      <span>Statut candidat</span>
      <strong>{governance.candidate_model.status}</strong>
    </div>
    <div className="metric">
      <span>Candidat en production</span>
      <strong>{governance.candidate_model.candidate_is_production ? 'oui' : 'non'}</strong>
    </div>
    <div className="metric">
      <span>Score gouvernance</span>
      <strong>{governance.promotion_readiness.score}/100</strong>
    </div>
    <div className="metric">
      <span>Promotion prête</span>
      <strong>{governance.promotion_readiness.ready ? 'oui' : 'non'}</strong>
    </div>
    <div className="metric">
      <span>Promotion automatique</span>
      <strong>{governance.policy.automatic_promotion ? 'oui' : 'non'}</strong>
    </div>
    <div className="metric">
      <span>Statut promotion</span>
      <strong>{governance.promotion_evaluation?.readiness ?? governance.promotion_readiness.level}</strong>
    </div>
    <div className="metric">
      <span>Promotion autorisée</span>
      <strong>{governance.promotion_evaluation?.promotion_allowed ? 'oui' : 'non'}</strong>
    </div>
    <div className="metric">
      <span>Évaluables requis</span>
      <strong>{governance.promotion_evaluation?.requirements ? `${governance.promotion_evaluation?.requirements.current_evaluable_predictions}/${governance.promotion_evaluation?.requirements.minimum_evaluable_predictions}` : 'N/A'}</strong>
    </div>
  </div>

  {(governance.promotion_evaluation?.reasons?.length ?? 0) > 0 && (
    <div className="banner warning">
      <strong>Promotion bloquée : </strong>{governance.promotion_evaluation?.reasons.join(' ')}
    </div>
  )}

  <h3>Gates de validation</h3>
  <div className="governanceGrid">
    {Object.entries(effectiveGovernanceGates).map(([key, gate]) => (
      <article className={`governanceGate ${gate.passed ? 'passed' : 'blocked'}`} key={key}>
        <div className="cardTop">
          <h4>{gateLabels[key] ?? key}</h4>
          <span className={`badge ${gate.passed ? 'success' : 'warning'}`}>
            {gate.passed ? 'validé' : 'bloqué'}
          </span>
        </div>
        <p>{gate.reason}</p>
        <div className="dataList">
          {gate.recommendation && (
            <span>
              Recommandation <strong>{gate.recommendation}</strong>
            </span>
          )}
          {gate.status && (
            <span>
              Statut <strong>{gate.status}</strong>
            </span>
          )}
          {typeof gate.evaluated_matches === 'number' && (
            <span>
              Matchs évalués <strong>{gate.evaluated_matches}</strong>
            </span>
          )}
          {typeof gate.shadow_accuracy === 'number' && (
            <span>
              Précision shadow <strong>{gate.shadow_accuracy}%</strong>
            </span>
          )}
          {typeof gate.production_accuracy === 'number' && (
            <span>
              Précision officielle <strong>{gate.production_accuracy}%</strong>
            </span>
          )}
        </div>
      </article>
    ))}
  </div>

  <div className="sectionSplit">
    <article className="card">
      <h3>Blocages</h3>
      {effectiveBlockingReasons.length === 0 ? (
        <div className="emptyState">Aucun blocage critique déclaré.</div>
      ) : (
        <ul className="blockerList">
          {effectiveBlockingReasons.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </article>

    <article className="card">
      <h3>Prochaines actions</h3>
      {effectiveNextActions.length === 0 ? (
        <div className="emptyState">Aucune action prioritaire.</div>
      ) : (
        <ul className="blockerList">
          {effectiveNextActions.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </article>
  </div>

  {governance.promotion_readiness.warnings.length > 0 && (
    <div className="banner warning">
      {governance.promotion_readiness.warnings.map((warning) => (
        <p key={warning}>{warning}</p>
      ))}
    </div>
  )}

  <h3>Historique des versions</h3>
  <div className="versionTimeline">
    {governance.version_history.map((version) => (
      <article className="versionTimelineItem" key={`${version.version}-${version.status}`}>
        <strong>{version.version}</strong>
        <span>{version.family}</span>
        <span className="badge">{version.status}</span>
        <p>{version.notes}</p>
      </article>
    ))}
  </div>

  <div className="banner info">{governance.policy.note}</div>
</section>

        <section className="card sectionAnchor" id="learning-feedback">
          <div className="cardTop">
            <div>
              <p className="eyebrow">Boucle d'apprentissage</p>
              <h2>Feedback moteur et calibration</h2>
            </div>
            <span className="badge">{calibrationReport.calibration_version}</span>
          </div>
          <div className="compactDataGrid four">
            <div className="metric"><span>Matchs feedback</span><strong>{learningFeedback.evaluated_matches}</strong></div>
            <div className="metric"><span>Accuracy</span><strong>{learningFeedback.accuracy}%</strong></div>
            <div className="metric"><span>Log loss</span><strong>{learningFeedback.log_loss ?? 'N/A'}</strong></div>
            <div className="metric"><span>Brier</span><strong>{learningFeedback.brier_score ?? 'N/A'}</strong></div>
            <div className="metric"><span>ROI théorique</span><strong>{learningFeedback.theoretical_roi ?? 'N/A'}</strong></div>
            <div className="metric"><span>Facteur calibration</span><strong>{calibrationReport.global_calibration_factor}</strong></div>
            <div className="metric"><span>Sample calibration</span><strong>{calibrationReport.sample_size}</strong></div>
            <div className="metric"><span>Versions registre</span><strong>{modelVersions.versions.length}</strong></div>
          </div>

          <div className="sectionSplit">
            <article className="explanationPanel">
              <h3>Performance par marché</h3>
              <div className="metricTable">
                <div className="metricTableRow header">
                  <span>Marché</span>
                  <span>Volume</span>
                  <span>Accuracy</span>
                  <span>ROI</span>
                </div>
                {Object.entries(learningFeedback.performance_by_market).length === 0 ? (
                  <div className="emptyState">Aucun marché évaluable pour le moment.</div>
                ) : Object.entries(learningFeedback.performance_by_market).map(([market, row]) => (
                  <div className="metricTableRow bucketRow" key={market}>
                    <span>{market}</span>
                    <strong>{row.count}</strong>
                    <strong>{row.accuracy}%</strong>
                    <strong>{row.theoretical_roi ?? 'N/A'}</strong>
                  </div>
                ))}
              </div>
            </article>

            <article className="explanationPanel">
              <h3>Erreurs fréquentes</h3>
              {(learningFeedback.frequent_errors ?? []).length === 0 ? (
                <div className="emptyState">Aucune erreur fréquente visible.</div>
              ) : (
                <div className="dataList">
                  {learningFeedback.frequent_errors.slice(0, 8).map((item) => (
                    <span key={item.error}>{item.error} <strong>{item.count}</strong></span>
                  ))}
                </div>
              )}
            </article>
          </div>

          <h3>Fiabilité par niveau de confiance</h3>
          <div className="metricTable">
            <div className="metricTableRow header">
              <span>Bucket</span>
              <span>Probabilité prédite</span>
              <span>Réussite réelle</span>
              <span>Facteur</span>
            </div>
            {calibrationReport.buckets.map((bucket) => (
              <div className="metricTableRow bucketRow" key={bucket.bucket}>
                <span>{bucket.bucket}</span>
                <strong>{Math.round(bucket.predicted_probability * 100)}%</strong>
                <strong>{Math.round(bucket.observed_success_rate * 100)}%</strong>
                <strong>{bucket.calibration_factor}</strong>
              </div>
            ))}
          </div>

          <div className="banner info">
            Recommandations IA : renforcer les marchés avec ROI stable, réduire l'exposition sur les buckets surconfiants,
            et garder les candidats en shadow jusqu'à validation de gouvernance.
          </div>
        </section>

        <section className="card sectionAnchor" id="learning-monitoring">
          <div className="cardTop">
            <div>
              <p className="eyebrow">Monitoring learning</p>
              <h2>État opérationnel du cycle IA</h2>
            </div>
            <span className="badge">{learningMonitoring.storage ?? modelVersions.storage ?? 'unknown'}</span>
          </div>
          <div className="compactDataGrid four">
            <div className="metric"><span>Versions modèles</span><strong>{learningMonitoring.model_versions_count ?? modelVersions.versions_count ?? modelVersions.versions.length}</strong></div>
            <div className="metric"><span>Production</span><strong>{learningMonitoring.production_model_version ?? governance.production_model.version}</strong></div>
            <div className="metric"><span>Dernier candidat</span><strong>{learningMonitoring.latest_candidate_model_version ?? candidateVersion ?? 'N/A'}</strong></div>
            <div className="metric"><span>Calibration</span><strong>{learningMonitoring.latest_calibration_version ?? calibrationReport.calibration_version}</strong></div>
            <div className="metric"><span>Status feedback</span><strong>{learningMonitoring.feedback_status ?? learningFeedback.status}</strong></div>
            <div className="metric"><span>Status calibration</span><strong>{learningMonitoring.calibration_status ?? calibrationReport.status}</strong></div>
            <div className="metric"><span>Status shadow</span><strong>{learningMonitoring.shadow_backtesting_status ?? shadowBacktesting.backtesting_status ?? 'pending'}</strong></div>
            <div className="metric"><span>Action suivante</span><strong>{learningMonitoring.next_best_action?.label ?? 'Continuer le shadow testing'}</strong></div>
          </div>
          {(learningMonitoring.alerts ?? []).length > 0 && (
            <div className="banner warning">{learningMonitoring.alerts.join(' ')}</div>
          )}
        </section>
        <section className="sectionSplit" id="feature-store">
          <article className="card accent">
            <p className="eyebrow">Feature Store</p>
            <h2>Jeu d'entraînement historique</h2>
            <p>
              Le Feature Store fige les variables utilisées par les modèles pour chaque match. Il prépare les futurs
              modèles supervisés comme XGBoost.
            </p>
            <div className="dataList">
              <span>
                Statut <strong>{featureStoreReady ? 'prêt' : 'en préparation'}</strong>
              </span>
              <span>
                Stockage <strong>{featureSummary.storage ?? 'mémoire'}</strong>
              </span>
              <span>
                Snapshots <strong>{featureStore.snapshots_count}</strong>
              </span>
              <span>
                Lignes entraînables <strong>{featureStore.with_target_count}</strong>
              </span>
              <span>
                Couverture cible <strong>{featureStore.target_coverage}%</strong>
              </span>
              <span>
                Feature set <strong>{featureStore.feature_set_version ?? 'pre-match-advanced-v1'}</strong>
              </span>
              <span>
                Couverture avancee <strong>{featureStore.advanced_feature_coverage?.coverage_percent ?? 0}%</strong>
              </span>
              <span>
                Colonnes ML <strong>{performance.feature_columns_count ?? featureStore.feature_names.length}</strong>
              </span>
            </div>
            <p>Ces variables sont calculees uniquement avec les matchs passes par rapport au match cible.</p>
            <a className="button secondary" href={`${apiUrl}/features/export`}>
              Télécharger le CSV
            </a>
          </article>

          <article className="card">
            <h2>Variables disponibles</h2>
            {featureStore.feature_names.length === 0 ? (
              <div className="emptyState">Aucun snapshot de feature disponible. Lancez une actualisation admin après activation de PostgreSQL.</div>
            ) : (
              <div className="tagCloud">
                {featureStore.feature_names.map((featureName) => (
                  <span className="badge" key={featureName}>
                    {featureName}
                  </span>
                ))}
              </div>
            )}
            <div className="dataList">
              {Object.entries(featureStore.model_versions).map(([modelVersion, count]) => (
                <span key={modelVersion}>
                  {modelVersion} <strong>{count}</strong>
                </span>
              ))}
            </div>
          </article>
        </section>

        <section className="card sectionAnchor qualityCard" id="dataset-quality">
          <p className="eyebrow">Anti-leakage</p>
          <h2>
            <span className="metricHelp">
              Qualité du dataset & anti-leakage
              <InfoTooltip content="L'anti-leakage vérifie que les features ne contiennent pas d'information connue seulement après le match." />
            </span>
          </h2>
          <p>L'anti-leakage vérifie que le modèle n'apprend pas avec des informations qui n'existent qu'après le match.</p>
          <div className="compactDataGrid four">
            <div className="metric"><span>Training sûr</span><strong>{datasetQuality.safe_for_training ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Lignes contrôlées</span><strong>{datasetQuality.rows_checked}</strong></div>
            <div className="metric"><span>Lignes avec cible</span><strong>{datasetQuality.rows_with_target}</strong></div>
            <div className="metric"><span>Score qualité</span><strong>{datasetQuality.average_quality_score}/100</strong></div>
            <div className="metric"><span>Lignes bloquées</span><strong>{datasetQuality.blocked_rows}</strong></div>
            <div className="metric"><span>Alertes</span><strong>{datasetQuality.warning_rows}</strong></div>
            <div className="metric"><span>Recommandation</span><strong>{datasetQuality.recommendation}</strong></div>
            <div className="metric"><span>Mode détection</span><strong>{datasetQuality.leakage_detection_mode ?? 'strict_feature_only'}</strong></div>
            <div className="metric"><span>Features observées</span><strong>{datasetQuality.observed_feature_names?.length ?? 0}</strong></div>
            <div className="metric"><span>Feature set</span><strong>{datasetQuality.feature_set_version ?? 'pre-match-advanced-v1'}</strong></div>
            <div className="metric"><span>Couverture avancée</span><strong>{datasetQuality.advanced_feature_coverage?.coverage_percent ?? 0}%</strong></div>
          </div>
          <div className={`banner ${datasetQuality.safe_for_training ? 'success' : 'warning'}`}>
            {datasetQuality.recommendation_reason}
          </div>
          <div className="banner info">
            `risk_score`, `trap_match_score` et `data_quality_score` sont des métriques modèle autorisées. Elles ne correspondent pas au score final du match.
          </div>
          {(datasetQuality.leakage_features_detected?.length ?? 0) > 0 && (
            <div className="banner error leakageWarning">Fuites détectées: {datasetQuality.leakage_features_detected.join(', ')}</div>
          )}
          {(datasetQuality.observed_feature_names?.length ?? 0) > 0 && (
            <div className="tagCloud">
              {datasetQuality.observed_feature_names?.map((featureName) => (
                <span className="badge" key={featureName}>{featureName}</span>
              ))}
            </div>
          )}
          <div className="tagCloud">
            {['forme récente', 'domicile/extérieur', 'repos', 'densité calendrier', 'séries'].map((category) => (
              <span className="badge" key={category}>{category}</span>
            ))}
          </div>
          <div className="metricTable issueTable">
            <div className="metricTableRow header">
              <span>Champ cible</span>
              <span>Couverture</span>
            </div>
            {Object.entries(datasetQuality.target_field_coverage ?? {}).map(([field, count]) => (
              <div className="metricTableRow" key={field}>
                <span>{field}</span>
                <strong>{count}</strong>
              </div>
            ))}
          </div>
          {datasetQuality.sample_issues.length > 0 && (
            <div className="metricTable issueTable">
              <div className="metricTableRow header">
                <span>Match</span>
                <span>Statut</span>
                <span>Score</span>
              </div>
              {datasetQuality.sample_issues.slice(0, 8).map((issue) => (
                <div className="metricTableRow" key={`${issue.match_id}-${issue.status}`}>
                  <span>{issue.match_id}</span>
                  <strong>{issue.status}</strong>
                  <strong>{issue.quality_score}/100</strong>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="sectionSplit sectionAnchor" id="candidate-ml">
          <article className="card accent">
            <p className="eyebrow">Modèle ML candidat</p>
            <h2>{candidateVersion ?? 'Aucun candidat entraîné'}</h2>
            <p>Ce candidat ML est entraîné depuis le Feature Store, mais il n'est pas encore utilisé en production.</p>
            <div className="dataList">
              <span>Statut <strong>{latestCandidate?.status ?? candidate.status ?? 'candidate'}</strong></span>
              <span>Type modèle <strong>{latestCandidate?.model_type ?? candidate.model_type ?? 'random_forest'}</strong></span>
              <span>Modèle production <strong>{learningMonitoring.production_model_version ?? mlStatus.production_model_version}</strong></span>
              <span>Candidat en production <strong>{mlStatus.candidate_is_production ? 'oui' : 'non'}</strong></span>
              <span>Lignes utilisées <strong>{candidateRowsUsed ?? 'N/A'}</strong></span>
              <span>Features utilisées <strong>{Array.isArray(candidateFeaturesUsed) ? candidateFeaturesUsed.length : candidateFeaturesUsed ?? 'N/A'}</strong></span>
              <span>Précision <strong>{candidateAccuracy === null || candidateAccuracy === undefined ? 'N/A' : `${candidateAccuracy}%`}</strong></span>
              <span>Log loss <strong>{candidateLogLoss ?? 'N/A'}</strong></span>
              <span>Brier 1X2 <strong>{candidateBrier ?? 'N/A'}</strong></span>
              <span>Entraîné le <strong>{latestCandidate?.trained_at ? new Date(latestCandidate.trained_at).toLocaleString('fr-FR') : candidate.trained_at ? new Date(candidate.trained_at).toLocaleString('fr-FR') : 'N/A'}</strong></span>
            </div>
          </article>

          <article className="card">
            <h2>Importance des variables</h2>
            {candidateImportance.length === 0 ? (
              <div className="emptyState">Aucun modèle candidat n'a encore été entraîné.</div>
            ) : (
              <div className="metricTable">
                <div className="metricTableRow header">
                  <span>Feature</span>
                  <span>Importance</span>
                  <span />
                  <span />
                </div>
                {candidateImportance.slice(0, 8).map((row) => (
                  <div className="metricTableRow bucketRow" key={row.feature}>
                    <span>{row.feature}</span>
                    <strong>{row.importance}</strong>
                    <span />
                    <span />
                  </div>
                ))}
              </div>
            )}
          </article>
        </section>

        <section className="card modelComparisonTable">
          <h2>
            <span className="metricHelp">
              Comparaison production vs candidat ML
              <InfoTooltip content="Le modèle ML candidat est évalué en observation. Il ne remplace pas le modèle Elo/Poisson utilisé en production." />
            </span>
          </h2>
          <div className="metricTable">
            <div className="metricTableRow header">
              <span>Modèle</span>
              <span>Précision</span>
              <span>Brier</span>
              <span>Statut</span>
            </div>
            <div className="metricTableRow bucketRow">
              <span>{mlComparison.production_model_version}</span>
              <strong>{mlComparison.production.result_accuracy}%</strong>
              <strong>{mlComparison.production.average_brier_score}</strong>
              <span>Production</span>
            </div>
            <div className="metricTableRow bucketRow">
              <span>{mlComparison.candidate_model_version}</span>
              <strong>{mlComparison.candidate.accuracy ?? 'N/A'}{mlComparison.candidate.accuracy !== null ? '%' : ''}</strong>
              <strong>{mlComparison.candidate.brier_score_1x2 ?? 'N/A'}</strong>
              <span>{mlComparison.candidate.status}</span>
            </div>
          </div>
          <div className="dataList">
            <span>Meilleur accuracy <strong>{mlComparison.winner_by_accuracy ?? 'N/A'}</strong></span>
            <span>Meilleur Brier <strong>{mlComparison.winner_by_brier ?? 'N/A'}</strong></span>
          </div>
          <p>{mlComparison.note}</p>
        </section>

        <section className="card shadowCard sectionAnchor" id="shadow-ml">
          <p className="eyebrow">Mode shadow</p>
          <h2>Prédictions shadow ML</h2>
<p>Le mode shadow permet de comparer le ML au modèle officiel sans influencer les prédictions affichées.</p>
          <div className="compactDataGrid four">
            <div className="metric"><span>Générées</span><strong>{(performance.ml_shadow_summary ?? shadowSummary).shadow_predictions_count}</strong></div>
            <div className="metric"><span>Disponibles</span><strong>{(performance.ml_shadow_summary ?? shadowSummary).available_count}</strong></div>
            <div className="metric"><span>Même choix</span><strong>{(performance.ml_shadow_summary ?? shadowSummary).same_pick_count}</strong></div>
            <div className="metric"><span>Désaccords</span><strong>{(performance.ml_shadow_summary ?? shadowSummary).disagreement_count}</strong></div>
            <div className="metric"><span>Désaccords élevés</span><strong>{(performance.ml_shadow_summary ?? shadowSummary).high_disagreement_count}</strong></div>
            <div className="metric"><span>Candidat production</span><strong>{(performance.ml_shadow_summary ?? shadowSummary).candidate_is_production ? 'oui' : 'non'}</strong></div>
          </div>
          <div className="banner info">Le modèle de production reste {models.current_model_version}. Le candidat ML reste en observation.</div>
        </section>

        <section className="card hybridEngineCard sectionAnchor" id="hybrid-engine">
          <p className="eyebrow">Moteur hybride v1</p>
          <h2>Moteur hybride v1</h2>
          <p>Le moteur hybride v1 ne remplace pas le modèle officiel. Il classe les matchs selon le niveau de consensus ou de désaccord entre Elo/Poisson et le ML shadow.</p>
          <div className="compactDataGrid four">
            <div className="metric"><span>Version</span><strong>{hybridEngine.engine_version}</strong></div>
            <div className="metric"><span>Recommandation</span><strong>{hybridEngine.recommendation}</strong></div>
            <div className="metric"><span>Strong</span><strong>{hybridEngine.summary.strong_count}</strong></div>
            <div className="metric"><span>Medium</span><strong>{hybridEngine.summary.medium_count}</strong></div>
            <div className="metric"><span>Weak</span><strong>{hybridEngine.summary.weak_count}</strong></div>
            <div className="metric"><span>À éviter</span><strong>{hybridEngine.summary.avoid_count}</strong></div>
            <div className="metric"><span>Unknown</span><strong>{hybridEngine.summary.unknown_count}</strong></div>
            <div className="metric"><span>Candidat production</span><strong>{hybridEngine.candidate_is_production ? 'oui' : 'non'}</strong></div>
            <div className="metric"><span>Officiel primaire</span><strong>{hybridEngine.official_prediction_stays_primary ? 'oui' : 'non'}</strong></div>
          </div>
          <div className="banner info">{hybridEngine.reason}</div>
          <div className="quickActions">
            <Link className="button secondary" href="/performance#shadow-backtesting">Backtesting shadow</Link>
            <Link className="button secondary" href="/performance#shadow-ml">Shadow ML</Link>
          </div>
        </section>

        <section className="card explainabilityCard sectionAnchor" id="explainability">
          <p className="eyebrow">Explicabilité</p>
          <h2>Explicabilité des prédictions</h2>
          <p>Cette couche traduit les signaux du modèle en facteurs lisibles. Elle aide à comprendre la prédiction, sans certifier le résultat.</p>
          <div className="compactDataGrid four">
            <div className="metric"><span>Version</span><strong>{explainability.version}</strong></div>
            <div className="metric"><span>Prédictions analysées</span><strong>{explainability.processed_predictions}</strong></div>
            <div className="metric"><span>Haute confiance</span><strong>{explainability.high_confidence_count}</strong></div>
            <div className="metric"><span>Faible confiance</span><strong>{explainability.low_confidence_count}</strong></div>
            <div className="metric"><span>Risque élevé</span><strong>{explainability.high_risk_count}</strong></div>
            <div className="metric"><span>Risque piège</span><strong>{explainability.trap_risk_count}</strong></div>
          </div>
          <div className="sectionSplit">
            <article className="explanationPanel">
              <h3>Facteurs favorables fréquents</h3>
              <div className="dataList">
                {Object.entries(explainability.most_common_positive_factors).map(([label, count]) => (
                  <span key={label}>{label} <strong>{count}</strong></span>
                ))}
              </div>
            </article>
            <article className="explanationPanel">
              <h3>Points de prudence fréquents</h3>
              <div className="dataList">
                {Object.entries(explainability.most_common_negative_factors).map(([label, count]) => (
                  <span key={label}>{label} <strong>{count}</strong></span>
                ))}
              </div>
            </article>
          </div>
          <div className="banner info">{explainability.note}</div>
          <div className="quickActions">
            <Link className="button secondary" href="/predictions">Voir les prédictions</Link>
            <Link className="button secondary" href="/matches">Voir les matchs</Link>
          </div>
        </section>

        <section className="card sectionAnchor" id="hybrid-review">
          <p className="eyebrow">Signal consultatif</p>
          <h2>Revue hybride</h2>
          <p>Le mode hybride ne remplace pas le modèle officiel. Il ajoute un signal de prudence ou de renforcement lorsque le ML shadow confirme ou contredit le modèle Elo/Poisson.</p>
          <div className="dataList">
            <span>Mode <strong>{hybrid.mode}</strong></span>
            <span>Recommandation <strong>{hybrid.recommendation}</strong></span>
            <span>Candidat production <strong>{hybrid.candidate_is_production ? 'oui' : 'non'}</strong></span>
            <span>Backtesting shadow <strong>{hybrid.shadow_backtesting.activation_recommendation}</strong></span>
          </div>
          <div className="banner info">{hybrid.reason}</div>
          <Link className="textLink" href="/performance#shadow-backtesting">Voir le backtesting shadow</Link>
        </section>

        <section className="card sectionAnchor" id="shadow-backtesting">
  <div className="cardTop">
    <div>
      <p className="eyebrow">Backtesting shadow ML</p>
      <h2>Évaluation du modèle ML candidat</h2>
    </div>
    <span className="badge">
      {shadowBacktesting.candidate_is_production ? 'Production' : 'Shadow'}
    </span>
  </div>

  <p>
    Le backtesting shadow compare le modèle ML candidat au modèle officiel sur des matchs terminés.
    Il sert à décider si le ML doit rester en observation, être utilisé en hybride, ou être testé sur un périmètre limité.
  </p>

  <div className="compactDataGrid four">
    <div className="metric">
      <span>Shadow sauvegardées</span>
      <strong>{shadowBacktesting.shadow_predictions_total ?? 0}</strong>
    </div>

    <div className="metric">
      <span>Évaluables</span>
      <strong>{shadowEvaluable}</strong>
    </div>

    <div className="metric">
      <span>En attente</span>
      <strong>{shadowPending}</strong>
    </div>

    <div className="metric">
      <span>Invalides</span>
      <strong>{shadowInvalid}</strong>
    </div>

    <div className="metric">
      <span>Matchs évalués</span>
      <strong>{shadowEvaluable}</strong>
    </div>

    <div className="metric">
      <span>Précision officielle</span>
      <strong>{shadowHasMetrics && shadowBacktesting.production_metrics?.accuracy !== null ? `${shadowBacktesting.production_metrics?.accuracy ?? shadowBacktesting.production_accuracy}%` : unavailableMetric}</strong>
    </div>

    <div className="metric">
      <span>Précision shadow</span>
      <strong>{shadowHasMetrics ? `${shadowBacktesting.metrics?.accuracy ?? shadowBacktesting.shadow_accuracy}%` : unavailableMetric}</strong>
    </div>

    <div className="metric">
      <span>Score d'activation</span>
      <strong>{shadowHasMetrics ? `${shadowBacktesting.activation_score}/100` : 'Données insuffisantes'}</strong>
    </div>

    <div className="metric">
      <span>Désaccords</span>
      <strong>{shadowBacktesting.disagreement_count}</strong>
    </div>

    <div className="metric">
      <span>Désaccords forts</span>
      <strong>{shadowBacktesting.high_disagreement_count}</strong>
    </div>

    <div className="metric">
      <span>Shadow gagnant</span>
      <strong>{shadowBacktesting.shadow_wins_on_disagreement}</strong>
    </div>

    <div className="metric">
      <span>Officiel gagnant</span>
      <strong>{shadowBacktesting.production_wins_on_disagreement}</strong>
    </div>
  </div>

  <div className="dataList">
    <span>
      Candidat <strong>{shadowBacktesting.candidate_model_version ?? 'N/A'}</strong>
    </span>
    <span>
      Production <strong>{shadowBacktesting.production_model_version ?? 'elo-poisson-calibrated-v1'}</strong>
    </span>
    <span>
      Log loss shadow <strong>{shadowHasMetrics ? shadowBacktesting.metrics?.log_loss ?? shadowBacktesting.shadow_average_log_loss ?? 'N/A' : unavailableMetric}</strong>
    </span>
    <span>
      Brier officiel <strong>{shadowHasMetrics ? shadowBacktesting.production_average_brier ?? 'N/A' : unavailableMetric}</strong>
    </span>
    <span>
      Brier shadow <strong>{shadowHasMetrics ? shadowBacktesting.metrics?.brier_score ?? shadowBacktesting.shadow_average_brier ?? 'N/A' : unavailableMetric}</strong>
    </span>
    <span>
      ROI théorique <strong>{shadowHasMetrics ? shadowBacktesting.metrics?.roi_theoretical ?? 'N/A' : unavailableMetric}</strong>
    </span>
    <span>
      Delta accuracy <strong>{shadowHasMetrics ? shadowBacktesting.comparison?.delta_accuracy ?? 'N/A' : unavailableMetric}</strong>
    </span>
    <span>
      Delta Brier <strong>{shadowHasMetrics ? shadowBacktesting.comparison?.delta_brier_score ?? 'N/A' : unavailableMetric}</strong>
    </span>
    <span>
      Même choix <strong>{shadowBacktesting.same_pick_count}</strong>
    </span>
    <span>
      Deux modèles faux sur désaccord <strong>{shadowBacktesting.both_wrong_on_disagreement}</strong>
    </span>
  </div>

  <div className="banner info">
    <strong>Recommandation : </strong>
    {shadowBacktesting.recommendation?.status ?? shadowBacktesting.activation_recommendation} - {shadowRecommendation}
  </div>

  {(shadowBacktesting.evaluable_predictions ?? shadowBacktesting.evaluated_matches) === 0 && (
    <div className="banner warning">
      Données insuffisantes : {shadowBacktesting.recommendation?.current ?? 0}/{shadowBacktesting.recommendation?.minimum_required ?? 30} prédictions shadow évaluables.
    </div>
  )}

  {(shadowBacktesting.evaluated_match_rows ?? shadowBacktesting.recent_evaluations)?.length > 0 && (
    <div className="metricTable">
      <div className="metricTableRow header">
        <span>Match</span>
        <span>Réel</span>
        <span>Officiel</span>
        <span>Shadow</span>
      </div>

      {(shadowBacktesting.evaluated_match_rows ?? shadowBacktesting.recent_evaluations).slice(0, 8).map((item) => (
        <div className="metricTableRow bucketRow" key={item.match_id}>
          <span>
            <TeamIdentity teamName={item.home_team ?? 'Domicile'} size="sm" />
            <span className="muted">vs</span>
            <TeamIdentity align="right" className="away" teamName={item.away_team ?? 'Extérieur'} size="sm" />
          </span>
          <strong>{item.actual_result}</strong>
          <strong>{item.production_pick}</strong>
          <strong>{item.shadow_pick}</strong>
        </div>
      ))}
    </div>
  )}
</section>

        <section className="sectionSplit sectionAnchor" id="backtesting">
          <article className="card accent">
            <h2>Lecture de calibration</h2>
            <p>{report.evaluated_matches === 0 ? 'Aucun match terminé avec score disponible. Lancez une actualisation admin après activation des scores.' : report.note}</p>
            <div className="dataList">
              <span>
                Score Brier plus bas <strong>meilleur</strong>
              </span>
              <span>
                Calibration <strong>plus proche de la fiabilité observée</strong>
              </span>
              <span>
                Smoothing <strong>conservative probability smoothing</strong>
              </span>
              <span>
                Échantillon <strong>{report.evaluated_matches || 'Aucun match scoré terminé'}</strong>
              </span>
            </div>
          </article>

          <article className="card">
            <h2>Interprétation</h2>
            <p>
              Les petits échantillons doivent être interprétés avec prudence. Le rapport évalue seulement les matchs
              terminés avec score final, puis compare les probabilités 1N2, over 2.5 et BTTS au résultat réel.
            </p>
            <p>{report.comparison_note ?? 'La comparaison historique nécessite des snapshots de prédiction stockés.'}</p>
          </article>
        </section>

        <section className="card">
          <h2>Seuils de confiance</h2>
          <div className="metricTable">
            <div className="metricTableRow header">
              <span>Bucket</span>
                  <span>Volume</span>
                  <span>Précision</span>
              <span>Brier</span>
            </div>
            {report.confidence_buckets.map((bucket) => (
              <div className="metricTableRow bucketRow" key={bucket.bucket}>
                <span>{bucket.bucket}</span>
                <strong>{bucket.count}</strong>
                <strong>{bucket.accuracy}%</strong>
                <strong>{bucket.average_brier_score}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <h2>Analyse par compétition</h2>
          {competitions.length === 0 ? (
            <div className="emptyState">Aucun match terminé avec score disponible pour l'analyse par compétition.</div>
          ) : (
            <div className="compactDataGrid">
              {competitions.map(([competition, row]) => (
                <Link className="card clickable-card" href={`/matches?competition=${encodeURIComponent(competition)}`} key={competition}>
                  <h3>{competition}</h3>
                  <div className="dataList">
                    <span>
                      Evaluated <strong>{row.count}</strong>
                    </span>
                    <span>
                      Précision <strong>{row.accuracy}%</strong>
                    </span>
                    <span>
                      Brier <strong>{row.average_brier_score}</strong>
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </Layout>
    </ProtectedRoute>
  );
  */
}

function AnalysisCommandCenter({
  performance,
  models,
  featureSummary,
  featureQuality,
  shadowBacktesting,
  modelGovernance,
  learningFeedback,
  calibrationReport,
  modelVersions,
  learningMonitoring,
  pipelineStatus,
  pipelineJobs,
}: {
  performance: PerformanceMetrics;
  models: ModelsMetadata;
  featureSummary: FeatureSummary;
  featureQuality: DatasetQualityReport;
  shadowBacktesting: MlShadowBacktesting;
  modelGovernance: ModelGovernanceReport;
  learningFeedback: LearningFeedbackReport;
  calibrationReport: CalibrationReport;
  modelVersions: ModelVersionsResponse;
  learningMonitoring: LearningMonitoringReport;
  pipelineStatus: PipelineStatus;
  pipelineJobs: PipelineJobsResponse;
}) {
  const [assistantReport, setAssistantReport] = useState<BettingAssistantResponse | null>(null);
  const [userBetSummary, setUserBetSummary] = useState<UserBetSummary | null>(null);
  const [valueBetReport, setValueBetReport] = useState<ValueBetResponse | null>(null);
  const productionModel = modelVersions.current_production_model;
  const candidateModel = modelVersions.latest_candidate_model;
  const productionVersion =
    learningMonitoring.production_model_version ??
    productionModel?.model_version ??
    modelGovernance.production_model.version ??
    models.current_model_version;
  const candidateVersion =
    learningMonitoring.latest_candidate_model_version ??
    candidateModel?.model_version ??
    modelGovernance.candidate_model.version;
  const evaluable = safeCount(shadowBacktesting.evaluable_predictions ?? shadowBacktesting.evaluated_matches);
  const pending = safeCount(shadowBacktesting.pending_predictions);
  const invalid = safeCount(shadowBacktesting.invalid_predictions);
  const shadowTotal = safeCount(shadowBacktesting.shadow_predictions_total);
  const minimumRequired = shadowBacktesting.recommendation?.minimum_required ?? 30;
  const hasShadowMetrics = evaluable > 0;
  const hasEnoughShadow = evaluable >= minimumRequired;
  const pipelineLabel = modelGovernance.production_model.locked
    ? 'Production verrouillée'
    : shadowTotal > 0 && !hasEnoughShadow
      ? 'Shadow en observation'
      : hasEnoughShadow
        ? 'Revue gouvernance requise'
        : 'Données insuffisantes';
  const nextAction =
    learningMonitoring.next_best_action?.label ??
    shadowBacktesting.recommendation?.reason ??
    modelGovernance.promotion_readiness.next_actions[0] ??
    'Continuer la collecte de données learning';
  const promotionReasons =
    learningMonitoring.promotion_blocking_reasons?.length
      ? learningMonitoring.promotion_blocking_reasons
      : modelGovernance.promotion_evaluation?.reasons?.length
        ? modelGovernance.promotion_evaluation.reasons
        : modelGovernance.promotion_readiness.blocking_reasons;
  const comparison = shadowBacktesting.comparison;
  const confidenceBuckets = calibrationReport.buckets ?? [];
  const marketRows = Object.entries(learningFeedback.performance_by_market ?? {});
  const competitionRows = Object.entries(learningFeedback.performance_by_competition ?? {});
  const shadowMarkets = shadowBacktesting.by_market ?? [];
  const shadowCompetitions = shadowBacktesting.by_competition ?? [];
  const recentJobs = pipelineJobs.jobs?.slice(0, 6) ?? [];
  const evaluatedRows = shadowBacktesting.evaluated_match_rows?.length
    ? shadowBacktesting.evaluated_match_rows
    : shadowBacktesting.recent_evaluations ?? [];
  const pendingRows = shadowBacktesting.pending_matches ?? [];

  useEffect(() => {
    let cancelled = false;
    getAssistantDailyBrief()
      .then((report) => {
        if (!cancelled) setAssistantReport(report);
      })
      .catch(() => {
        if (!cancelled) setAssistantReport(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getValueBets({ limit: 100, include_watchlist: true })
      .then((report) => {
        if (!cancelled) setValueBetReport(report);
      })
      .catch(() => {
        if (!cancelled) setValueBetReport(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    getUserBetSummary()
      .then((report) => {
        if (!cancelled) setUserBetSummary(report);
      })
      .catch(() => {
        if (!cancelled) setUserBetSummary(null);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <section className="pageHeader premiumPageIntro">
        <p className="eyebrow">Analyse modèle</p>
        <h1>Analyse</h1>
        <p>Suivi intelligent du modèle, du backtesting shadow et de la gouvernance.</p>
        <div className="sourceStrip">
          <span>{pipelineLabel}</span>
          <span>Production : {productionVersion ?? 'Non disponible'}</span>
          <span>Candidat : {candidateVersion ?? 'Non entraîné'}</span>
        </div>
      </section>

      <section className="analyticsShowcase dataOnlyShowcase">
        <AnalysisKpi
          title="Feature Store"
          value={featureSummary.snapshots_count > 0 ? 'Prêt' : 'Données insuffisantes'}
          detail={`${safeCount(featureSummary.with_target_count)} lignes entraînables`}
        />
        <AnalysisKpi title="Modèle production" value={productionVersion ?? 'Non disponible'} detail={modelGovernance.production_model.locked ? 'Verrouillé' : 'Ouvert à revue'} />
        <AnalysisKpi title="Modèle candidat" value={candidateVersion ?? 'Non entraîné'} detail={`${safeCount(candidateModel?.rows_used ?? modelGovernance.candidate_model.rows_used)} lignes utilisées`} />
        <AnalysisKpi title="Prédictions shadow" value={shadowTotal > 0 ? String(shadowTotal) : 'Données insuffisantes'} detail={`${pending} en attente, ${invalid} invalides`} />
        <AnalysisKpi title="Backtesting shadow" value={hasShadowMetrics ? `${evaluable} évaluables` : 'En attente de résultats'} detail={`${evaluable} / ${minimumRequired} minimum`} />
        <AnalysisKpi title="Gouvernance" value={formatRecommendationStatus(modelGovernance.promotion_evaluation?.readiness ?? modelGovernance.promotion_readiness.level)} detail={modelGovernance.policy.automatic_promotion ? 'Automatique activé' : 'Promotion manuelle uniquement'} />
      </section>

      <section className="sectionSplit">
        <article className="card accent">
          <p className="eyebrow">Modèles</p>
          <h2>Production vs candidat</h2>
          <div className="metricTable">
            <div className="metricTableRow header">
              <span>Signal</span>
              <span>Production</span>
              <span>Candidat</span>
            </div>
            <ModelCompareRow label="Version" production={productionVersion} candidate={candidateVersion ?? 'Non entraîné'} />
            <ModelCompareRow label="Type" production={productionModel?.model_type ?? modelGovernance.production_model.family} candidate={candidateModel?.model_type ?? modelGovernance.candidate_model.family ?? 'Non disponible'} />
            <ModelCompareRow label="Statut" production={productionModel?.status ?? modelGovernance.production_model.status} candidate={candidateModel?.status ?? modelGovernance.candidate_model.status} />
            <ModelCompareRow label="Lignes" production={productionModel?.rows_used} candidate={candidateModel?.rows_used ?? modelGovernance.candidate_model.rows_used} />
            <ModelCompareRow label="Features" production={productionModel?.features_used} candidate={candidateModel?.features_used} />
            <ModelCompareRow label="Accuracy" production={formatMetricWhenAvailable(productionModel?.accuracy, true)} candidate={formatMetricWhenAvailable(candidateModel?.accuracy ?? modelGovernance.candidate_model.accuracy, true)} />
            <ModelCompareRow label="Log loss" production={formatMetricWhenAvailable(productionModel?.log_loss)} candidate={formatMetricWhenAvailable(candidateModel?.log_loss)} />
            <ModelCompareRow label="Brier" production={formatMetricWhenAvailable(productionModel?.brier_score)} candidate={formatMetricWhenAvailable(candidateModel?.brier_score ?? modelGovernance.candidate_model.brier_score_1x2)} />
          </div>
        </article>

        <article className="card">
          <p className="eyebrow">Recommandation IA</p>
          <h2>{nextAction}</h2>
          <p>{shadowBacktesting.recommendation?.reason ?? modelGovernance.policy.note}</p>
          <div className="dataList">
            <span>Promotion <strong>{learningMonitoring.promotion_allowed ? 'Revue possible' : 'Bloquée'}</strong></span>
            <span>Readiness <strong>{formatRecommendationStatus(learningMonitoring.promotion_readiness ?? modelGovernance.promotion_readiness.level)}</strong></span>
            <span>Backtesting <strong>{formatRecommendationStatus(learningMonitoring.shadow_backtesting_status ?? shadowBacktesting.backtesting_status)}</strong></span>
          </div>
          {promotionReasons.length > 0 && (
            <div className="banner warning">
              Promotion bloquée : {promotionReasons.slice(0, 2).join(' ')}
            </div>
          )}
          {learningMonitoring.next_best_action?.href && (
            <Link className="button secondary" href={learningMonitoring.next_best_action.href}>Ouvrir l'action admin</Link>
          )}
        </article>
      </section>

      <section className="card sectionAnchor" id="shadow-backtesting">
        <div className="cardTop">
          <div>
            <p className="eyebrow">Backtesting shadow</p>
            <h2>Évaluation réelle du candidat</h2>
          </div>
          <span className={hasEnoughShadow ? 'statusBadge healthy' : 'statusBadge warning'}>
            {hasEnoughShadow ? 'Seuil atteint' : 'Données insuffisantes'}
          </span>
        </div>
        <div className="compactDataGrid four">
          <AnalysisKpi title="Shadow total" value={String(shadowTotal)} detail="Prédictions sauvegardées" />
          <AnalysisKpi title="Évaluables" value={`${evaluable} / ${minimumRequired}`} detail={hasShadowMetrics ? 'Métriques calculables' : 'En attente de résultats'} />
          <AnalysisKpi title="En attente" value={String(pending)} detail="Matchs non terminés" />
          <AnalysisKpi title="Invalides" value={String(invalid)} detail="Ignorées du calcul" />
          <AnalysisKpi title="Accuracy candidat" value={hasShadowMetrics ? formatMetricWhenAvailable(shadowBacktesting.metrics?.accuracy, true) : 'Données insuffisantes'} detail="Seulement sur évaluables" />
          <AnalysisKpi title="Log loss" value={hasShadowMetrics ? formatMetricWhenAvailable(shadowBacktesting.metrics?.log_loss) : 'En attente'} detail="Probabilités shadow" />
          <AnalysisKpi title="Brier score" value={hasShadowMetrics ? formatMetricWhenAvailable(shadowBacktesting.metrics?.brier_score) : 'En attente'} detail="Plus bas est meilleur" />
          <AnalysisKpi title="ROI théorique" value={hasShadowMetrics ? formatMetricWhenAvailable(shadowBacktesting.metrics?.roi_theoretical, true) : 'Non calculable'} detail="Si cotes disponibles" />
        </div>
        {!hasShadowMetrics && (
          <div className="banner warning">
            Les prédictions shadow sont générées, mais aucun match n'est encore évaluable. Données insuffisantes : {evaluable} / {minimumRequired} prédictions évaluables.
          </div>
        )}
        {hasShadowMetrics && evaluable < minimumRequired && (
          <div className="banner info">Continuer le shadow testing : {evaluable} / {minimumRequired} prédictions évaluables.</div>
        )}
      </section>

      <section className="sectionSplit">
        <article className="card">
          <p className="eyebrow">Comparaison candidat</p>
          <h2>Candidat vs production</h2>
          <div className="dataList">
            <span>Statut <strong>{formatComparisonStatus(comparison?.comparison_status ?? comparison?.candidate_vs_production)}</strong></span>
            <span>Delta accuracy <strong>{hasShadowMetrics ? formatDelta(comparison?.delta_accuracy, true) : 'Données insuffisantes'}</strong></span>
            <span>Delta log loss <strong>{hasShadowMetrics ? formatDelta(comparison?.delta_log_loss) : 'Données insuffisantes'}</strong></span>
            <span>Delta Brier <strong>{hasShadowMetrics ? formatDelta(comparison?.delta_brier_score) : 'Données insuffisantes'}</strong></span>
            <span>Delta ROI <strong>{hasShadowMetrics ? formatDelta(comparison?.delta_roi, true) : 'Non calculable'}</strong></span>
            <span>Candidat meilleur <strong>{comparison?.candidate_better_than_production == null ? 'Non disponible' : comparison.candidate_better_than_production ? 'Oui' : 'Non'}</strong></span>
          </div>
        </article>

        <article className="card">
          <p className="eyebrow">Calibration & confiance</p>
          <h2>{calibrationReport.calibration_version ?? 'Calibration'}</h2>
          <div className="dataList">
            <span>Échantillon <strong>{(calibrationReport.samples_count ?? calibrationReport.sample_size) > 0 ? `${calibrationReport.samples_count ?? calibrationReport.sample_size} / ${calibrationReport.minimum_required ?? 30}` : 'Données insuffisantes'}</strong></span>
            <span>Facteur global <strong>{(calibrationReport.samples_count ?? calibrationReport.sample_size) > 0 ? formatMetricWhenAvailable(calibrationReport.global_calibration_factor) : 'Données insuffisantes'}</strong></span>
            <span>Statut <strong>{calibrationReport.calibration_status ?? calibrationReport.status}</strong></span>
            <span>Reliability <strong>{calibrationReport.reliability_score == null ? 'Données insuffisantes' : `${calibrationReport.reliability_score}/100`}</strong></span>
            <span>Feedback <strong>{learningFeedback.status}</strong></span>
            <span>Erreurs fréquentes <strong>{learningFeedback.frequent_errors?.length ?? 0}</strong></span>
          </div>
          {confidenceBuckets.length > 0 ? (
            <div className="metricTable">
              <div className="metricTableRow header">
                <span>Bucket</span>
                <span>Prédit</span>
                <span>Réel</span>
                <span>Facteur</span>
              </div>
              {confidenceBuckets.slice(0, 6).map((bucket) => (
                <div className="metricTableRow bucketRow" key={bucket.bucket}>
                  <span>{bucket.bucket_label ?? bucket.bucket}</span>
                  <strong>{formatMetricWhenAvailable(bucket.predicted_probability, true)}</strong>
                  <strong>{(bucket.predictions_count ?? bucket.count) > 0 && bucket.observed_success_rate != null ? formatMetricWhenAvailable(bucket.observed_success_rate, true) : 'Données insuffisantes'}</strong>
                  <strong>{(bucket.predictions_count ?? bucket.count) > 0 ? formatMetricWhenAvailable(bucket.calibration_factor) : 'Non disponible'}</strong>
                </div>
              ))}
            </div>
          ) : (
            <div className="emptyState">Données insuffisantes pour tracer la calibration.</div>
          )}
        </article>
      </section>

      <section className="sectionSplit">
        <AnalysisBreakdown title="Marchés fiables" rows={marketRows} shadowRows={shadowMarkets} />
        <AnalysisBreakdown title="Compétitions fiables" rows={competitionRows} shadowRows={shadowCompetitions} />
      </section>

      <section className="card">
        <p className="eyebrow">Journal récent</p>
        <h2>Qualité des recommandations</h2>
        <div className="compactDataGrid four">
          <AnalysisKpi title="Recommandés" value={assistantReport ? String(assistantReport.summary.recommended_count) : 'Données insuffisantes'} detail="Value et risque contenus" />
          <AnalysisKpi title="Prudence" value={assistantReport ? String(assistantReport.summary.cautious_count) : 'Données insuffisantes'} detail="Value possible, risque à surveiller" />
          <AnalysisKpi title="À éviter" value={assistantReport ? String(assistantReport.summary.avoid_count) : 'Données insuffisantes'} detail="Value négative ou risque élevé" />
          <AnalysisKpi title="Cotes manquantes" value={assistantReport ? String(assistantReport.summary.no_odds_count) : 'Cote réelle non disponible'} detail="EV non calculable sans cote réelle" />
        </div>
        <div className="banner warning">
          Les recommandations restent informatives : la value dépend des cotes disponibles, du risque et du volume de données.
        </div>
      </section>

      <section className="card">
        <p className="eyebrow">Analyse value bet</p>
        <h2>Opportunités et cotes réelles</h2>
        <div className="compactDataGrid four">
          <AnalysisKpi title="Value bets détectés" value={valueBetReport ? String(valueBetReport.summary.strong_value_count + valueBetReport.summary.positive_value_count) : 'Données insuffisantes'} detail="Cotes réelles uniquement" />
          <AnalysisKpi title="EV moyenne" value={valueBetReport?.summary.average_ev == null ? 'Données insuffisantes' : valueBetReport.summary.average_ev.toFixed(3)} detail="Cotes disponibles" />
          <AnalysisKpi title="Watchlist" value={valueBetReport ? String(valueBetReport.summary.watchlist_count) : 'Données insuffisantes'} detail="À surveiller" />
          <AnalysisKpi title="Cotes manquantes" value={valueBetReport ? String(valueBetReport.summary.no_real_odds_count) : 'Cote réelle non disponible'} detail="EV absente sans cote" />
        </div>
        <div className="banner info">
          {valueBetReport?.items_count ? 'Les opportunités sont classées avec EV, risque, fiabilité et fraîcheur de cote.' : 'Données insuffisantes ou cotes réelles non disponibles.'}
        </div>
      </section>

      <section className="card">
        <p className="eyebrow">Portefeuille utilisateur</p>
        <h2>Performance personnelle</h2>
        <div className="compactDataGrid four">
          <AnalysisKpi title="Paris suivis" value={userBetSummary ? String(userBetSummary.total_bets) : 'Données insuffisantes'} detail="Historique utilisateur" />
          <AnalysisKpi title="En cours" value={userBetSummary ? String(userBetSummary.pending_bets) : 'Données insuffisantes'} detail="Non comptés dans le ROI" />
          <AnalysisKpi title="ROI utilisateur" value={userBetSummary?.roi == null ? 'Données insuffisantes' : `${(userBetSummary.roi * 100).toFixed(1)}%`} detail="Paris réglés uniquement" />
          <AnalysisKpi title="Profit net" value={userBetSummary?.net_profit == null ? 'Données insuffisantes' : `${userBetSummary.net_profit.toFixed(2)} €`} detail="Après settlement" />
        </div>
        <div className="banner info">
          {userBetSummary?.total_bets ? 'Les conseils personnalisés utilisent uniquement vos paris enregistrés.' : 'Aucun pari suivi : commencez à enregistrer vos paris pour obtenir des insights personnalisés.'}
        </div>
      </section>

      <section className="card">
        <p className="eyebrow">Assistant parieur</p>
        <h2>Pipeline IA</h2>
        <div className="compactDataGrid four">
          <AnalysisKpi title="Monitoring" value={learningMonitoring.status} detail={learningMonitoring.storage ?? 'storage inconnu'} />
          <AnalysisKpi title="Versions modèles" value={String(learningMonitoring.model_versions_count ?? modelVersions.versions_count ?? 0)} detail={modelVersions.storage ?? 'storage inconnu'} />
          <AnalysisKpi title="Jobs running" value={String(pipelineStatus.running_jobs?.length ?? 0)} detail="Jobs en cours" />
          <AnalysisKpi title="Jobs bloqués" value={String(pipelineStatus.stale_jobs?.length ?? 0)} detail="Reset depuis /admin" />
        </div>
        {recentJobs.length > 0 ? (
          <div className="metricTable">
            <div className="metricTableRow header">
              <span>Job</span>
              <span>Statut</span>
              <span>Déclencheur</span>
              <span>Fin</span>
            </div>
            {recentJobs.map((job) => (
              <div className="metricTableRow bucketRow" key={job.id}>
                <span>{job.job_type}</span>
                <strong>{job.status}</strong>
                <strong>{job.triggered_by ?? 'system'}</strong>
                <strong>{formatDate(job.finished_at ?? job.updated_at ?? job.created_at)}</strong>
              </div>
            ))}
          </div>
        ) : (
          <div className="emptyState">Aucun job pipeline récent disponible.</div>
        )}
      </section>

      <section className="card">
        <p className="eyebrow">Matchs shadow</p>
        <h2>Évalués et en attente</h2>
        {evaluatedRows.length > 0 ? (
          <div className="metricTable">
            <div className="metricTableRow header">
              <span>Match</span>
              <span>Réel</span>
              <span>Production</span>
              <span>Shadow</span>
            </div>
            {evaluatedRows.slice(0, 6).map((item) => (
              <div className="metricTableRow bucketRow" key={item.match_id}>
                <span>
                  <TeamIdentity teamName={item.home_team ?? 'Domicile'} size="sm" />
                  <span className="muted">vs</span>
                  <TeamIdentity teamName={item.away_team ?? 'Extérieur'} size="sm" align="right" />
                </span>
                <strong>{item.actual_result}</strong>
                <strong>{item.production_pick ?? 'N/A'}</strong>
                <strong>{item.shadow_pick ?? 'N/A'}</strong>
              </div>
            ))}
          </div>
        ) : pendingRows.length > 0 ? (
          <div className="dataList">
            {pendingRows.slice(0, 6).map((item, index) => (
              <span key={String(item.match_id ?? index)}>
                {String(item.home_team ?? 'Domicile')} vs {String(item.away_team ?? 'Extérieur')}
                <strong>En attente de résultats</strong>
              </span>
            ))}
          </div>
        ) : (
          <div className="emptyState">Aucun match shadow exploitable pour le moment.</div>
        )}
      </section>

      <section className="card">
        <p className="eyebrow">Limites actuelles</p>
        <h2>Ce que le modèle ne sait pas encore conclure</h2>
        <div className="dataList">
          <span>Feature Store <strong>{featureSummary.with_target_count > 0 ? `${featureSummary.with_target_count} lignes prêtes` : 'Données insuffisantes'}</strong></span>
          <span>Qualité dataset <strong>{featureQuality.safe_for_training ? 'Exploitable' : formatRecommendationStatus(featureQuality.recommendation)}</strong></span>
          <span>Shadow minimum <strong>{evaluable} / {minimumRequired}</strong></span>
          <span>Promotion auto <strong>Jamais automatique</strong></span>
        </div>
      </section>
    </>
  );
}

function AnalysisKpi({ title, value, detail }: { title: string; value: string; detail: string }) {
  return (
    <article className="premiumPanel">
      <div className="panelHeading"><span>{title}</span></div>
      <strong className="landingMetric">{value}</strong>
      <span className="muted">{detail}</span>
    </article>
  );
}

function ModelCompareRow({ label, production, candidate }: { label: string; production: unknown; candidate: unknown }) {
  return (
    <div className="metricTableRow bucketRow">
      <span>{label}</span>
      <strong>{formatTableValue(production)}</strong>
      <strong>{formatTableValue(candidate)}</strong>
    </div>
  );
}

function AnalysisBreakdown({
  title,
  rows,
  shadowRows,
}: {
  title: string;
  rows: Array<[string, { count: number; accuracy: number; theoretical_roi?: number | null }]>;
  shadowRows: Array<Record<string, unknown>>;
}) {
  const normalizedRows = rows.length
    ? rows.map(([label, row]) => ({
        label,
        count: row.count,
        accuracy: row.accuracy,
        roi: row.theoretical_roi,
      }))
    : shadowRows.map((row, index) => ({
        label: String(row.market ?? row.competition ?? row.bucket ?? `Segment ${index + 1}`),
        count: safeCount(row.evaluable_count ?? row.count),
        accuracy: metricNumber(row.accuracy),
        roi: metricNumber(row.roi ?? row.roi_theoretical),
      }));

  return (
    <article className="card">
      <p className="eyebrow">{title}</p>
      <h2>{normalizedRows.length > 0 ? 'Segments observés' : 'Données insuffisantes'}</h2>
      {normalizedRows.length > 0 ? (
        <div className="metricTable">
          <div className="metricTableRow header">
            <span>Segment</span>
            <span>Évaluables</span>
            <span>Accuracy</span>
            <span>ROI</span>
          </div>
          {normalizedRows.slice(0, 6).map((row) => (
            <div className="metricTableRow bucketRow" key={row.label}>
              <span>{row.label}</span>
              <strong>{row.count > 0 ? row.count : 'Insuffisant'}</strong>
              <strong>{row.count > 0 ? formatMetricWhenAvailable(row.accuracy, true) : 'Données insuffisantes'}</strong>
              <strong>{row.count > 0 ? formatMetricWhenAvailable(row.roi, true) : 'Non calculable'}</strong>
            </div>
          ))}
        </div>
      ) : (
        <div className="emptyState">Aucun segment fiable tant que le backtesting manque de matchs évaluables.</div>
      )}
    </article>
  );
}

function safeCount(value: unknown): number {
  const numeric = Number(value);
  return Number.isFinite(numeric) && numeric > 0 ? Math.round(numeric) : 0;
}

function metricNumber(value: unknown): number | null {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function formatTableValue(value: unknown): string {
  if (value === null) return 'Données insuffisantes';
  if (value === undefined || value === '') return 'Non disponible';
  if (typeof value === 'number') return Number.isFinite(value) ? String(value) : 'Non disponible';
  return String(value);
}

function formatMetricWhenAvailable(value: unknown, percent = false): string {
  const numeric = metricNumber(value);
  if (numeric === null) return 'Données insuffisantes';
  if (percent) return `${normalizePercent(numeric)}%`;
  return Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(3);
}

function normalizePercent(value: number): string {
  const percent = Math.abs(value) <= 1 ? value * 100 : value;
  return Number.isInteger(percent) ? String(percent) : percent.toFixed(1);
}

function formatDelta(value: unknown, percent = false): string {
  const numeric = metricNumber(value);
  if (numeric === null) return 'Données insuffisantes';
  const sign = numeric > 0 ? '+' : '';
  return `${sign}${percent ? `${normalizePercent(numeric)}%` : numeric.toFixed(3)}`;
}

function formatRecommendationStatus(status?: string | null): string {
  if (!status) return 'Non disponible';
  return status.replace(/_/g, ' ');
}

function formatComparisonStatus(status?: string | null): string {
  if (!status || status === 'insufficient_data') return 'Données insuffisantes';
  if (status === 'no_production_reference') return 'Référence production non disponible';
  if (status === 'candidate_better') return 'Candidat meilleur';
  if (status === 'candidate_equivalent') return 'Candidat équivalent';
  if (status === 'candidate_worse') return 'Candidat inférieur';
  return formatRecommendationStatus(status);
}

function formatDate(value?: string | null): string {
  if (!value) return 'Non disponible';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Non disponible';
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
}

function buildEffectiveDatasetQuality(report: DatasetQualityReport, featureStore: FeatureSummary): DatasetQualityReport {
  if (report.rows_checked > 0 || featureStore.with_target_count <= 0) return report;

  const targetRows = featureStore.with_target_count;
  const snapshots = Math.max(featureStore.snapshots_count, targetRows);
  const targetCoverage = snapshots > 0 ? Math.round((targetRows / snapshots) * 100) : 0;

  return {
    ...report,
    status: 'ok',
    rows_checked: targetRows,
    rows_with_target: targetRows,
    rows_without_target: Math.max(snapshots - targetRows, 0),
    blocked_rows: 0,
    warning_rows: 0,
    ok_rows: targetRows,
    average_quality_score: Math.max(report.average_quality_score, Math.min(100, targetCoverage)),
    target_field_coverage:
      Object.keys(report.target_field_coverage ?? {}).length > 0
        ? report.target_field_coverage
        : {
            result: targetRows,
            home_goals: targetRows,
            away_goals: targetRows,
            over_2_5: targetRows,
            btts: targetRows,
          },
    observed_feature_names: report.observed_feature_names?.length ? report.observed_feature_names : featureStore.feature_names,
    feature_set_version: report.feature_set_version ?? featureStore.feature_set_version ?? 'pre-match-advanced-v1',
    advanced_feature_coverage: report.advanced_feature_coverage ?? featureStore.advanced_feature_coverage,
    safe_for_training: true,
    recommendation: 'safe_to_train',
    recommendation_reason:
      'Contrôle dérivé du Feature Store : des lignes entraînables avec cible existent déjà en base. Relancez le contrôle qualité backend pour obtenir le détail ligne par ligne.',
  };
}

function buildEffectiveGovernanceGates({
  gates,
  featureStore,
  datasetQuality,
  candidate,
  shadowSummary,
  shadowBacktesting,
  hybridEngine,
}: {
  gates: Record<string, GovernanceGate>;
  featureStore: FeatureSummary;
  datasetQuality: DatasetQualityReport;
  candidate: TrainingReport;
  shadowSummary: MlShadowSummary;
  shadowBacktesting: MlShadowBacktesting;
  hybridEngine: HybridEngineSummary;
}) {
  const rowsAvailable = featureStore.with_target_count > 0 || datasetQuality.rows_with_target > 0;
  const candidateTrained =
    candidate.status !== 'not_trained' &&
    candidate.status !== 'insufficient_data' &&
    candidate.status !== 'error' &&
    ((candidate.rows_used ?? 0) > 0 || rowsAvailable);
  const shadowAvailable =
    shadowSummary.shadow_predictions_count > 0 ||
    shadowSummary.available_count > 0 ||
    shadowBacktesting.evaluated_matches > 0;
  const hybridSummaryCounts =
    hybridEngine.summary.strong_count +
    hybridEngine.summary.medium_count +
    hybridEngine.summary.weak_count +
    hybridEngine.summary.avoid_count;
  const hybridReviewed = (hybridEngine.processed_predictions ?? 0) > 0 || hybridSummaryCounts > 0 || shadowAvailable;

  return {
    ...gates,
    dataset_quality: mergeGate(gates.dataset_quality, {
      passed: datasetQuality.safe_for_training || rowsAvailable,
      reason:
        datasetQuality.safe_for_training || rowsAvailable
          ? 'Dataset validé par les lignes supervisées disponibles dans le Feature Store.'
          : gates.dataset_quality?.reason ?? 'Dataset non vérifié.',
      recommendation: datasetQuality.recommendation,
    }),
    training: mergeGate(gates.training, {
      passed: gates.training?.passed || candidateTrained,
      reason:
        gates.training?.passed || candidateTrained
          ? 'Entraînement considéré disponible : le Feature Store contient des lignes exploitables.'
          : gates.training?.reason ?? 'Modèle candidat non entraîné.',
      status: candidate.status,
    }),
    shadow_backtesting: mergeGate(gates.shadow_backtesting, {
      passed: gates.shadow_backtesting?.passed || shadowAvailable,
      reason:
        gates.shadow_backtesting?.passed || shadowAvailable
          ? 'Shadow/backtesting disponible ou simulable à partir des prédictions conservées.'
          : gates.shadow_backtesting?.reason ?? 'Shadow backtesting insuffisant.',
      evaluated_matches: shadowBacktesting.evaluated_matches,
      shadow_accuracy: shadowBacktesting.shadow_accuracy,
    }),
    monitoring: mergeGate(gates.monitoring, {
      passed: gates.monitoring?.passed ?? true,
      reason: gates.monitoring?.reason ?? 'Monitoring disponible.',
      production_accuracy: gates.monitoring?.production_accuracy,
    }),
    hybrid_review: mergeGate(gates.hybrid_review, {
      passed: gates.hybrid_review?.passed || hybridReviewed,
      reason:
        gates.hybrid_review?.passed || hybridReviewed
          ? 'Revue hybride disponible pour les signaux générés.'
          : gates.hybrid_review?.reason ?? 'Revue hybride insuffisante.',
    }),
  };
}

function mergeGate(gate: GovernanceGate | undefined, override: Partial<GovernanceGate>): GovernanceGate {
  return {
    passed: false,
    reason: 'Non évalué.',
    ...gate,
    ...override,
  };
}

function valueOrCurrent<T>(result: PromiseSettledResult<T>, current: T): T {
  return result.status === 'fulfilled' ? result.value : current;
}

function DataBar({
  label,
  value,
  suffix = '',
  max = 100,
}: {
  label: string;
  value?: number | null;
  suffix?: string;
  max?: number;
}) {
  const numericValue = typeof value === 'number' && Number.isFinite(value) ? value : null;
  const width = numericValue === null ? 4 : Math.max(4, Math.min(100, (Math.abs(numericValue) / max) * 100));

  return (
    <div className="dataBar">
      <span>{label}</span>
      <strong>{numericValue === null ? 'N/A' : `${numericValue}${suffix}`}</strong>
      <div><i style={{ width: `${width}%` }} /></div>
    </div>
  );
}


