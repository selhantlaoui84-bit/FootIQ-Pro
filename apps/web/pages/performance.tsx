import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { InfoTooltip } from '~/components/InfoTooltip';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import {
  getBacktesting,
  getFeatureSummary,
  getMlFeatureImportance,
  getHybridEngineSummary,
  getHybridSummary,
  getMlComparison,
  getMlStatus,
  getMlShadowBacktesting,
  getMlShadowSummary,
  getModelComparison,
  getModels,
  getPerformance,
} from '~/lib/api';
import type {
  BacktestingReport,
  FeatureImportanceRow,
  FeatureSummary,
  HybridEngineSummary,
  HybridSummary,
  MlComparison,
  MlStatus,
  MlShadowSummary,
  MlShadowBacktesting,
  ModelComparison,
  ModelsMetadata,
  PerformanceMetrics,
} from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type PerformanceProps = {
  performance: PerformanceMetrics;
  backtesting: BacktestingReport;
  models: ModelsMetadata;
  comparison: ModelComparison;
  featureSummary: FeatureSummary;
  mlStatus: MlStatus;
  mlComparison: MlComparison;
  shadowSummary: MlShadowSummary;
  shadowBacktesting: MlShadowBacktesting;
  hybridSummary: HybridSummary;
  hybridEngineSummary: HybridEngineSummary;
  featureImportance: FeatureImportanceRow[];
};

export const getStaticProps: GetStaticProps<PerformanceProps> = async () => {
  const [
    performance,
    backtesting,
    models,
    comparison,
    featureSummary,
    mlStatus,
    mlComparison,
    shadowSummary,
    shadowBacktesting,
    hybridSummary,
    hybridEngineSummary,
    featureImportance,
  ] = await Promise.all([
    getPerformance(),
    getBacktesting(),
    getModels(),
    getModelComparison(),
    getFeatureSummary(),
    getMlStatus(),
    getMlComparison(),
    getMlShadowSummary(),
    getMlShadowBacktesting(1000),
    getHybridSummary(),
    getHybridEngineSummary(),
    getMlFeatureImportance(),
  ]);

  return {
    props: {
      performance,
      backtesting,
      models,
      comparison,
      featureSummary,
      mlStatus,
      mlComparison,
      shadowSummary,
      shadowBacktesting,
      hybridSummary,
      hybridEngineSummary,
      featureImportance,
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
  mlStatus,
  mlComparison,
  shadowSummary,
  shadowBacktesting,
  hybridSummary,
  hybridEngineSummary,
  featureImportance,
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
    ['Accuracy résultat', `${report.result_accuracy}%`],
    ['Accuracy over 2.5', `${report.over_2_5_accuracy}%`],
    ['Accuracy BTTS', `${report.btts_accuracy}%`],
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
  const candidateImportance = candidate.feature_importance?.length ? candidate.feature_importance : featureImportance;

  return (
    <ProtectedRoute>
      <Layout>
        <section className="pageHeader">
          <p className="eyebrow">Model evaluation</p>
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
              <span>Meilleure accuracy <strong>{bestByAccuracy ?? 'N/A'}</strong></span>
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
                <span>Accuracy</span>
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
            </div>
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

        <section className="sectionSplit sectionAnchor" id="candidate-ml">
          <article className="card accent">
            <p className="eyebrow">Modèle ML candidat</p>
            <h2>{candidate.model_version ?? 'ml-candidate-v1'}</h2>
            <p>Ce candidat ML est entraîné depuis le Feature Store, mais il n'est pas encore utilisé en production.</p>
            <div className="dataList">
              <span>Status <strong>{candidate.status}</strong></span>
              <span>Modèle production <strong>{mlStatus.production_model_version}</strong></span>
              <span>Candidat en production <strong>{mlStatus.candidate_is_production ? 'oui' : 'non'}</strong></span>
              <span>Lignes utilisées <strong>{candidate.rows_used ?? 0}</strong></span>
              <span>Accuracy <strong>{candidate.accuracy ?? 0}%</strong></span>
              <span>Log loss <strong>{candidate.log_loss ?? 'N/A'}</strong></span>
              <span>Brier 1X2 <strong>{candidate.brier_score_1x2 ?? 'N/A'}</strong></span>
            </div>
          </article>

          <article className="card">
            <h2>Feature importance</h2>
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
              <span>Accuracy</span>
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
          <p>Le moteur hybride v1 ne remplace pas le mod?le officiel. Il classe les matchs selon le niveau de consensus ou de d?saccord entre Elo/Poisson et le ML shadow.</p>
          <div className="compactDataGrid four">
            <div className="metric"><span>Version</span><strong>{hybridEngine.engine_version}</strong></div>
            <div className="metric"><span>Recommandation</span><strong>{hybridEngine.recommendation}</strong></div>
            <div className="metric"><span>Strong</span><strong>{hybridEngine.summary.strong_count}</strong></div>
            <div className="metric"><span>Medium</span><strong>{hybridEngine.summary.medium_count}</strong></div>
            <div className="metric"><span>Weak</span><strong>{hybridEngine.summary.weak_count}</strong></div>
            <div className="metric"><span>? ?viter</span><strong>{hybridEngine.summary.avoid_count}</strong></div>
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

        <section className="card sectionAnchor" id="hybrid-review">
          <p className="eyebrow">Signal consultatif</p>
          <h2>Revue hybride</h2>
          <p>Le mode hybride ne remplace pas le mod?le officiel. Il ajoute un signal de prudence ou de renforcement lorsque le ML shadow confirme ou contredit le mod?le Elo/Poisson.</p>
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
      <span>Accuracy officielle</span>
      <strong>{shadowBacktesting.production_accuracy}%</strong>
    </div>

    <div className="metric">
      <span>Accuracy shadow</span>
      <strong>{shadowBacktesting.shadow_accuracy}%</strong>
    </div>

    <div className="metric">
      <span>Score d’activation</span>
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
              <span>Count</span>
              <span>Accuracy</span>
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
                      Accuracy <strong>{row.accuracy}%</strong>
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



