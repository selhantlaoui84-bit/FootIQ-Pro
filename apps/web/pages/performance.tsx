import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { InfoTooltip } from '~/components/InfoTooltip';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import {
  getBacktesting,
  getFeatureQualityReport,
  getFeatureSummary,
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
  getPerformance,
} from '~/lib/api';
import type {
  BacktestingReport,
  DatasetQualityReport,
  FeatureImportanceRow,
  FeatureSummary,
  HybridEngineSummary,
  ExplainabilitySummary,
  HybridSummary,
  MlComparison,
  MlStatus,
  MlShadowSummary,
  MlShadowBacktesting,
  ModelGovernanceReport,
  ModelComparison,
  ModelsMetadata,
  PerformanceMetrics,
} from '~/lib/mock-data';
import {
  mockBacktestingReport,
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
  mockModelsMetadata,
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
  ] = await Promise.all([
    load('performance', getPerformance(), fallback.performance),
    load('backtesting', getBacktesting(), fallback.backtesting),
    load('models', getModels(), fallback.models),
    load('comparison', getModelComparison(), fallback.comparison),
    load('featureSummary', getFeatureSummary(), fallback.featureSummary),
    load('featureQuality', getFeatureQualityReport(1000), fallback.featureQuality),
    load('mlStatus', getMlStatus(), fallback.mlStatus),
    load('mlComparison', getMlComparison(), fallback.mlComparison),
    load('shadowSummary', getMlShadowSummary(), fallback.shadowSummary),
    load('shadowBacktesting', getMlShadowBacktesting(1000), fallback.shadowBacktesting),
    load('hybridSummary', getHybridSummary(), fallback.hybridSummary),
    load('hybridEngineSummary', getHybridEngineSummary(), fallback.hybridEngineSummary),
    load('explainabilitySummary', getExplainabilitySummary(200, 'upcoming'), fallback.explainabilitySummary),
    load('featureImportance', getMlFeatureImportance(), fallback.featureImportance),
    load('modelGovernance', getModelGovernance(), fallback.modelGovernance),
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
    },
    revalidate: 120,
  };
};

export default function PerformancePage({
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
}: PerformanceProps) {
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

  const items = [
    ['Modèle', report.model_version],
    ['Modèle précédent', report.previous_model_version ?? 'elo-poisson-v1'],
    ['Calibration', report.calibration_applied ? 'active' : 'active'],
    ['Prédictions suivies', performance.predictions_tracked ?? performance.tracked],
    ['Matchs évalués', report.evaluated_matches],
    ['Précision résultat', `${report.result_accuracy}%`],
    ['Précision over 2.5', `${report.over_2_5_accuracy}%`],
    ['Précision BTTS', `${report.btts_accuracy}%`],
    ['Score Brier moyen', report.average_brier_score],
    ['Score de calibration', `${report.calibration_score}/100`],
  ];
  const competitions = Object.entries(report.competition_breakdown ?? {});
  const modelRows = Object.entries(performance.model_versions ?? comparison.model_versions ?? {});
  const bestByBrier = performance.best_model_by_brier ?? comparison.best_model_by_brier;
  const bestByAccuracy = performance.best_model_by_accuracy ?? comparison.best_model_by_accuracy;
  const featureStore = {
    ...featureSummary,
    snapshots_count: performance.feature_snapshots_count ?? featureSummary.snapshots_count,
    with_target_count: performance.training_rows_available ?? featureSummary.with_target_count,
    target_coverage: performance.target_coverage ?? featureSummary.target_coverage,
  };
  const featureStoreReady = performance.feature_store_ready ?? featureStore.snapshots_count > 0;
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://footiq-pro-production.up.railway.app';
  const candidate = performance.ml_candidate ?? mlStatus.latest_candidate;
  const hybrid = performance.hybrid_summary ?? hybridSummary;
  const hybridEngine = performance.hybrid_engine_summary ?? hybridEngineSummary;
  const explainability = performance.explainability_summary ?? explainabilitySummary;
  const datasetQuality = performance.dataset_quality ?? featureQuality;
  const candidateImportance = candidate.feature_importance?.length ? candidate.feature_importance : featureImportance;

  const governance = performance.model_governance ?? modelGovernance;
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
        <section className="pageHeader">
          <p className="eyebrow">Analyse modèle</p>
          <h1>Performance</h1>
          <p>A good probabilistic model is not always right; it must be well calibrated.</p>
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
              <span>Snapshots <strong>{performance.snapshots_count ?? 0}</strong></span>
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
  </div>

  <h3>Gates de validation</h3>
  <div className="governanceGrid">
    {Object.entries(governance.governance_gates).map(([key, gate]) => (
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
      {governance.promotion_readiness.blocking_reasons.length === 0 ? (
        <div className="emptyState">Aucun blocage critique déclaré.</div>
      ) : (
        <ul className="blockerList">
          {governance.promotion_readiness.blocking_reasons.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </article>

    <article className="card">
      <h3>Prochaines actions</h3>
      {governance.promotion_readiness.next_actions.length === 0 ? (
        <div className="emptyState">Aucune action prioritaire.</div>
      ) : (
        <ul className="blockerList">
          {governance.promotion_readiness.next_actions.map((item) => (
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
            <h2>{candidate.model_version ?? 'ml-candidate-v1'}</h2>
            <p>Ce candidat ML est entraîné depuis le Feature Store, mais il n'est pas encore utilisé en production.</p>
            <div className="dataList">
              <span>Statut <strong>{candidate.status}</strong></span>
              <span>Modèle production <strong>{mlStatus.production_model_version}</strong></span>
              <span>Candidat en production <strong>{mlStatus.candidate_is_production ? 'oui' : 'non'}</strong></span>
              <span>Lignes utilisées <strong>{candidate.rows_used ?? 0}</strong></span>
              <span>Précision <strong>{candidate.accuracy ?? 0}%</strong></span>
              <span>Log loss <strong>{candidate.log_loss ?? 'N/A'}</strong></span>
              <span>Brier 1X2 <strong>{candidate.brier_score_1x2 ?? 'N/A'}</strong></span>
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
          <p>Cette couche traduit les signaux du modèle en facteurs lisibles. Elle aide à comprendre la prédiction, sans garantir le résultat.</p>
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
      <span>Matchs évalués</span>
      <strong>{shadowBacktesting.evaluated_matches}</strong>
    </div>

    <div className="metric">
      <span>Précision officielle</span>
      <strong>{shadowBacktesting.production_accuracy}%</strong>
    </div>

    <div className="metric">
      <span>Précision shadow</span>
      <strong>{shadowBacktesting.shadow_accuracy}%</strong>
    </div>

    <div className="metric">
      <span>Score d'activation</span>
      <strong>{shadowBacktesting.activation_score}/100</strong>
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
      Brier officiel <strong>{shadowBacktesting.production_average_brier ?? 'N/A'}</strong>
    </span>
    <span>
      Brier shadow <strong>{shadowBacktesting.shadow_average_brier ?? 'N/A'}</strong>
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
    {shadowBacktesting.activation_recommendation} — {shadowBacktesting.recommendation_reason}
  </div>

  {shadowBacktesting.recent_evaluations?.length > 0 && (
    <div className="metricTable">
      <div className="metricTableRow header">
        <span>Match</span>
        <span>Réel</span>
        <span>Officiel</span>
        <span>Shadow</span>
      </div>

      {shadowBacktesting.recent_evaluations.slice(0, 8).map((item) => (
        <div className="metricTableRow bucketRow" key={item.match_id}>
          <span>
            {item.home_team} - {item.away_team}
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
}


