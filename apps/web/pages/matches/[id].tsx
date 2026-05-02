import type { GetStaticPaths, GetStaticProps } from 'next';
import Link from 'next/link';
import { getMatch, getPrediction } from '~/lib/api';
import { matches, statusClass, teamNameHref, type Match, type Prediction } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type MatchDetailProps = {
  match: Match;
  prediction: Prediction;
};

export const getStaticPaths: GetStaticPaths = async () => ({
  paths: matches.map((match) => ({ params: { id: match.slug } })),
  fallback: 'blocking',
});

export const getStaticProps: GetStaticProps<MatchDetailProps> = async ({ params }) => {
  const id = typeof params?.id === 'string' ? params.id : matches[0].slug;
  const [match, prediction] = await Promise.all([getMatch(id), getPrediction(id)]);

  return { props: { match, prediction }, revalidate: 120 };
};

export default function MatchDetailPage({ match, prediction }: MatchDetailProps) {
  const kickoff = prediction.kickoff || match.kickoff;

  return (
    <Layout>
      <section className="matchHeader">
        <div>
          <p className="eyebrow">{prediction.competition || match.competition}</p>
          <h1>
            {prediction.home_team} vs {prediction.away_team}
          </h1>
          <p>{new Date(kickoff).toLocaleString('fr-FR', { dateStyle: 'full', timeStyle: 'short' })}</p>
        </div>
        <span className={`badge large status-badge ${statusClass(prediction.confidence.status)}`}>
          {prediction.confidence.status}
        </span>
      </section>

      <section className="grid three">
        <Probability label={prediction.home_team} value={prediction.probabilities.home} />
        <Probability label="Nul" value={prediction.probabilities.draw} />
        <Probability label={prediction.away_team} value={prediction.probabilities.away} />
      </section>

      <section className="sectionSplit">
        <article className="card">
          <h2>Modèle offensif</h2>
          <div className="dataList">
            <span>
              Score attendu{' '}
              <strong>
                {prediction.goals.expected_home} - {prediction.goals.expected_away}
              </strong>
            </span>
            <span>
              Over 2.5 <strong>{prediction.goals.over_2_5}%</strong>
            </span>
            <span>
              BTTS <strong>{prediction.goals.btts}%</strong>
            </span>
            <span>
              Source <strong>{prediction.source ?? match.source ?? 'mock'}</strong>
            </span>
          </div>
        </article>

        <article className="card">
          <h2>Confidence Index</h2>
          <strong className="bigScore">{prediction.confidence.score}/100</strong>
          <div className="confidenceLine tall confidence-bar">
            <span style={{ width: `${prediction.confidence.score}%` }} />
          </div>
          <p>{prediction.recommendation}</p>
        </article>
      </section>

      <section className="sectionSplit">
        <article className="card accent">
          <h2>Recommandation FootIQ</h2>
          <strong>{prediction.recommendation}</strong>
          <p>{prediction.main_prediction}</p>
        </article>
        <article className={prediction.flags.trap_match || prediction.flags.risk ? 'card danger' : 'card'}>
          <h2>{prediction.flags.trap_match ? 'Match piège détecté' : 'Risk alert'}</h2>
          <p>
            {prediction.flags.trap_match
              ? 'Favori apparent, mais signaux contradictoires.'
              : prediction.flags.risk
                ? 'Lisibilité réduite, prudence recommandée.'
                : 'Aucune alerte majeure détectée.'}
          </p>
        </article>
      </section>

      <section className="sectionSplit">
        <article className="card">
          <h2>Explication</h2>
          <ul>
            {prediction.explanation.slice(0, 3).map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>
        <article className="card">
          <h2>Risques</h2>
          <ul>
            {prediction.risks.map((risk) => (
              <li key={risk}>{risk}</li>
            ))}
          </ul>
        </article>
      </section>

      <section className="grid three">
        {[prediction.home_team, prediction.away_team].map((team) => (
          <Link className="card clickable-card" href={teamNameHref(team)} key={team}>
            <h3>{team}</h3>
            <p>Voir la fiche équipe et les matchs liés.</p>
          </Link>
        ))}
      </section>

      <section className="notice">{prediction.disclaimer}</section>
      <Link className="textLink" href="/matches">
        Retour aux matchs
      </Link>
    </Layout>
  );
}

function Probability({ label, value }: { label: string; value: number }) {
  return (
    <article className="card probability">
      <span>{label}</span>
      <strong>{value}%</strong>
      <div className="probabilityBar confidence-bar">
        <span style={{ width: `${value}%` }} />
      </div>
    </article>
  );
}
