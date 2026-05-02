import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getBacktesting, getFeatureSummary, getModelComparison, getModels, getPerformance } from '~/lib/api';
import type { BacktestingReport, FeatureSummary, ModelComparison, ModelsMetadata, PerformanceMetrics } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type PerformanceProps = {
  performance: PerformanceMetrics;
  backtesting: BacktestingReport;
  models: ModelsMetadata;
  comparison: ModelComparison;
  featureSummary: FeatureSummary;
};

export const getStaticProps: GetStaticProps<PerformanceProps> = async () => {
  const [performance, backtesting, models, comparison, featureSummary] = await Promise.all([
    getPerformance(),
    getBacktesting(),
    getModels(),
    getModelComparison(),
    getFeatureSummary(),
  ]);

  return { props: { performance, backtesting, models, comparison, featureSummary }, revalidate: 120 };
};

export default function PerformancePage({ performance, backtesting, models, comparison, featureSummary }: PerformanceProps) {
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
    ['Model version', report.model_version],
    ['Previous model', report.previous_model_version ?? 'elo-poisson-v1'],
    ['Calibration', report.calibration_applied ? 'applied' : 'applied'],
    ['Predictions tracked', performance.predictions_tracked ?? performance.tracked],
    ['Evaluated matches', report.evaluated_matches],
    ['Result accuracy', `${report.result_accuracy}%`],
    ['Over 2.5 accuracy', `${report.over_2_5_accuracy}%`],
    ['BTTS accuracy', `${report.btts_accuracy}%`],
    ['Average Brier', report.average_brier_score],
    ['Calibration score', `${report.calibration_score}/100`],
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
            <Link className="metric clickable-card" href={label === 'Predictions tracked' ? '/predictions' : '/performance'} key={label}>
              <span>{label}</span>
              <strong>{value}</strong>
            </Link>
          ))}
        </section>


        <section className="sectionSplit" id="model-comparison">
          <article className="card accent">
            <p className="eyebrow">Current model</p>
            <h2>{models.current_model_version}</h2>
            <div className="dataList">
              <span>Previous <strong>{models.previous_model_version}</strong></span>
              <span>Family <strong>{models.family}</strong></span>
              <span>Calibration <strong>{models.calibration ? 'enabled' : 'disabled'}</strong></span>
              <span>Snapshots <strong>{performance.snapshots_count ?? 0}</strong></span>
            </div>
            <p>{models.description}</p>
          </article>
          <article className="card">
            <h2>Best model</h2>
            <div className="dataList">
              <span>Best by Brier <strong>{bestByBrier ?? 'N/A'}</strong></span>
              <span>Best by accuracy <strong>{bestByAccuracy ?? 'N/A'}</strong></span>
            </div>
            <p>A prediction snapshot is a saved version of what the model believed before evaluation. This enables fair model comparison over time.</p>
          </article>
        </section>

        <section className="card">
          <h2>Model comparison</h2>
          {modelRows.length === 0 ? (
            <div className="emptyState">No prediction snapshots available yet. Run an admin refresh with PostgreSQL enabled.</div>
          ) : (
            <div className="metricTable">
              <div className="metricTableRow header">
                <span>Model</span>
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
            <h2>Historical training dataset</h2>
            <p>
              The Feature Store freezes the model inputs used for each match. This prepares future supervised learning
              models such as XGBoost.
            </p>
            <div className="dataList">
              <span>
                Status <strong>{featureStoreReady ? 'ready' : 'warming up'}</strong>
              </span>
              <span>
                Storage <strong>{featureSummary.storage ?? 'memory'}</strong>
              </span>
              <span>
                Snapshots <strong>{featureStore.snapshots_count}</strong>
              </span>
              <span>
                Training rows <strong>{featureStore.with_target_count}</strong>
              </span>
              <span>
                Target coverage <strong>{featureStore.target_coverage}%</strong>
              </span>
            </div>
            <a className="button secondary" href={`${apiUrl}/features/export`}>
              Download CSV
            </a>
          </article>

          <article className="card">
            <h2>Feature inventory</h2>
            {featureStore.feature_names.length === 0 ? (
              <div className="emptyState">No feature snapshots available yet. Run an admin refresh after PostgreSQL is enabled.</div>
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

        <section className="sectionSplit">
          <article className="card accent">
            <h2>Calibration reading</h2>
            <p>{report.evaluated_matches === 0 ? 'No finished matches with scores available yet. Run admin refresh after score fields are enabled.' : report.note}</p>
            <div className="dataList">
              <span>
                Lower Brier score <strong>is better</strong>
              </span>
              <span>
                Calibration <strong>closer to expected reliability is better</strong>
              </span>
              <span>
                Smoothing <strong>conservative probability smoothing</strong>
              </span>
              <span>
                Sample size <strong>{report.evaluated_matches || 'No finished scored matches yet'}</strong>
              </span>
            </div>
          </article>

          <article className="card">
            <h2>Interpretation</h2>
            <p>
              Small samples should be interpreted carefully. This report only evaluates finished matches with available
              final scores, then compares the 1X2 probabilities, over 2.5 signal and BTTS signal against reality.
            </p>
            <p>{report.comparison_note ?? 'Historical model comparison requires stored prediction snapshots.'}</p>
          </article>
        </section>

        <section className="card">
          <h2>Confidence buckets</h2>
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
          <h2>Competition breakdown</h2>
          {competitions.length === 0 ? (
            <div className="emptyState">No finished scored matches available for competition analysis yet.</div>
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

