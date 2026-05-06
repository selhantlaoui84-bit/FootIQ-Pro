import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { getDashboardSummary } from '~/lib/api';
import { matchHref, type DashboardSummary } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type HomeProps = {
  summary: DashboardSummary;
};

const pillars = [
  {
    title: 'Probabilités claires',
    href: '/predictions',
    body: 'Lire les issues en pourcentages, sans promesse de certitude.',
  },
  { title: 'Indice de confiance', href: '/performance', body: 'Comprendre quand un signal est robuste ou fragile.' },
  {
    title: 'Détection des matchs pièges',
    href: '/predictions?trap=true',
    body: 'Repérer les favoris apparents avec signaux contradictoires.',
  },
  {
    title: 'Explications compréhensibles',
    href: '/about',
    body: 'Transformer les données en lecture utile et responsable.',
  },
];

export const getStaticProps: GetStaticProps<HomeProps> = async () => ({
  props: { summary: await getDashboardSummary() },
  revalidate: 120,
});

export default function HomePage({ summary }: HomeProps) {
  const featured = summary.top_reliable_matches[0];

  return (
    <Layout>
      <section className="hero">
        <div className="heroCopy">
          <p className="eyebrow">Football analytics probabiliste</p>
          <h1>FootIQ Pro</h1>
          <p className="subtitle">L'intelligence probabiliste du football français et européen.</p>
          <p className="lead">
            Notre IA ne promet pas de prédire l'avenir. Elle identifie les matchs statistiquement lisibles, les risques
            et les signaux qui comptent.
          </p>
          <div className="actions">
            <Link className="button primary" href="/dashboard">
              Tableau de bord
            </Link>
            <Link className="button secondary" href="/matches">
              Explorer les matchs
            </Link>
          </div>
        </div>
        <Link className="heroPanel clickable-card" href={featured ? matchHref(featured) : '/dashboard'}>
          <span className="panelLabel">Signal actuel</span>
          <strong>{summary.total_matches}</strong>
          <div className="probabilityBar">
            <span style={{ width: `${summary.average_confidence}%` }} />
          </div>
          <div className="miniStats">
            <span>Confiance {summary.average_confidence}%</span>

          </div>
        </Link>
      </section>

      <section className="grid five">
        {pillars.map((pillar) => (
          <Link className="card clickable-card card-link" href={pillar.href} key={pillar.title}>
            <h3>{pillar.title}</h3>
            <p>{pillar.body}</p>
          </Link>
        ))}
      </section>

      <section className="notice">
        FootIQ Pro est un outil d'analyse statistique et probabiliste. Aucune prédiction ne garantit un résultat.
      </section>
    </Layout>
  );
}
