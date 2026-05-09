import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { Card, StatusBanner } from '~/components/ui';
import { getPublicDashboardSummary } from '~/lib/api';
import { buildDashboardSummary, matchHref, type DashboardSummary } from '~/lib/mock-data';
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
    title: 'Gestion du risque',
    href: '/dashboard',
    body: 'Prioriser les décisions selon la lisibilité, le contexte et le niveau de risque.',
  },
  {
    title: 'Gouvernance IA',
    href: '/performance',
    body: 'Suivre le backtesting, la qualité des données et le modèle candidat.',
  },
];

export const getStaticProps: GetStaticProps<HomeProps> = async () => ({
  props: { summary: await loadHomeSummary() },
  revalidate: 120,
});

async function loadHomeSummary() {
  try {
    return await getPublicDashboardSummary();
  } catch (error) {
    console.error('Home summary fallback:', error);
    return buildDashboardSummary();
  }
}

export default function HomePage({ summary }: HomeProps) {
  const featured = summary.top_reliable_matches[0];

  return (
    <Layout>
      <section className="hero">
        <div className="heroCopy">
          <p className="eyebrow">Football analytics premium</p>
          <h1>FootIQ Pro</h1>
          <p className="subtitle">IA, value betting, risque et performance dans une lecture stratégique du football.</p>
          <p className="lead">
            FootIQ Pro croise probabilités, confiance modèle, signaux de marché et gouvernance ML pour aider à décider
            avec méthode. L'objectif n'est pas de promettre un résultat, mais d'éclairer le risque.
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
          <span className="panelLabel">Signal stratégique</span>
          <strong>{summary.total_matches}</strong>
          <div className="probabilityBar">
            <span style={{ width: `${summary.average_confidence}%` }} />
          </div>
          <div className="miniStats">
            <span>Confiance {summary.average_confidence}%</span>
            <span>Risque {summary.average_risk_score ?? 0}/100</span>
          </div>
        </Link>
      </section>

      <section className="grid five">
        {pillars.map((pillar) => (
          <Link className="card-link" href={pillar.href} key={pillar.title}>
            <Card className="clickable-card" tone="premium">
              <h3>{pillar.title}</h3>
              <p>{pillar.body}</p>
            </Card>
          </Link>
        ))}
      </section>

      <StatusBanner tone="premium">
        FootIQ Pro est un outil d'analyse statistique et probabiliste. Aucune prédiction ne garantit un résultat.
      </StatusBanner>
    </Layout>
  );
}
