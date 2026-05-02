import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { getPerformance, getPredictions } from '~/lib/api';
import type { PerformanceMetrics, Prediction } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type PerformanceProps = {
  performance: PerformanceMetrics;
  predictions: Prediction[];
};

export const getStaticProps: GetStaticProps<PerformanceProps> = async () => {
  const [performance, predictions] = await Promise.all([getPerformance(), getPredictions()]);

  return { props: { performance, predictions }, revalidate: 120 };
};

export default function PerformancePage({ performance, predictions }: PerformanceProps) {
  const reliable = predictions.filter((prediction) => prediction.confidence.status === 'FIABLE').length;
  const averageConfidence = predictions.length
    ? Math.round(predictions.reduce((sum, prediction) => sum + prediction.confidence.score, 0) / predictions.length)
    : performance.averageConfidence;
  const items = [
    ['Predictions tracked', predictions.length || performance.tracked],
    ['Reliable predictions', reliable],
    ['Average confidence', averageConfidence],
    ['Calibration status', performance.calibration],
    ['Brier score', performance.brierScore],
    ['Model version', performance.modelVersion],
  ];

  return (
    <Layout>
      <section className="pageHeader">
        <p className="eyebrow">Calibration modèle</p>
        <h1>Performance</h1>
        <p>Un bon modèle probabiliste n'a pas toujours raison. Il doit surtout être bien calibré.</p>
      </section>

      <section className="metrics">
        {items.map(([label, value]) => (
          <Link className="metric clickable-card" href="/predictions" key={label}>
            <span>{label}</span>
            <strong>{value}</strong>
          </Link>
        ))}
      </section>

      <section className="sectionSplit">
        <Link className="card clickable-card" href="/about">
          <h2>Lecture responsable</h2>
          <p>
            Les taux de réussite sont suivis par niveau de confiance. L'objectif est une calibration honnête: lorsqu'un
            événement est annoncé à 60%, il doit se produire environ 60% du temps sur un grand volume.
          </p>
        </Link>
        <Link className="card clickable-card" href="/admin">
          <h2>Dernier refresh</h2>
          <div className="dataList">
            <span>
              Source <strong>{performance.latest_refresh?.source ?? 'mock'}</strong>
            </span>
            <span>
              Last refresh <strong>{performance.latest_refresh?.last_refresh_at ?? 'N/A'}</strong>
            </span>
          </div>
        </Link>
      </section>
    </Layout>
  );
}
