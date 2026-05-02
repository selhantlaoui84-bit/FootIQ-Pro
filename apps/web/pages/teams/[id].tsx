import type { GetStaticPaths, GetStaticProps } from 'next';
import Link from 'next/link';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getMatches, getPredictions, getTeam } from '~/lib/api';
import { matchHref, teams, type Match, type Prediction, type Team } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type TeamDetailProps = {
  team: Team;
  relatedMatches: Match[];
  relatedPredictions: Prediction[];
};

export const getStaticPaths: GetStaticPaths = async () => ({
  paths: teams.map((team) => ({ params: { id: team.slug } })),
  fallback: 'blocking',
});

export const getStaticProps: GetStaticProps<TeamDetailProps> = async ({ params }) => {
  const id = typeof params?.id === 'string' ? params.id : teams[0].slug;
  const [team, matches, predictions] = await Promise.all([getTeam(id), getMatches(), getPredictions()]);
  const relatedMatches = matches.filter((match) => match.home_team === team.name || match.away_team === team.name);
  const relatedPredictions = predictions.filter(
    (prediction) => prediction.home_team === team.name || prediction.away_team === team.name,
  );

  return { props: { team, relatedMatches, relatedPredictions }, revalidate: 120 };
};

export default function TeamDetailPage({ team, relatedMatches, relatedPredictions }: TeamDetailProps) {
  const averageConfidence =
    relatedPredictions.length > 0
      ? Math.round(
          relatedPredictions.reduce((sum, prediction) => sum + prediction.confidence.score, 0) /
            relatedPredictions.length,
        )
      : 0;

  return (
    <ProtectedRoute>
      <Layout>
      <section className="pageHeader">
        <p className="eyebrow">{team.competition}</p>
        <h1>{team.name}</h1>
        <p>Vue équipe construite à partir des matchs et prédictions disponibles.</p>
      </section>

      <section className="metrics">
        <article className="metric">
          <span>Elo placeholder</span>
          <strong>{team.elo ?? 'N/A'}</strong>
        </article>
        <article className="metric">
          <span>Recent form</span>
          <strong>{team.form ?? 'N/A'}</strong>
        </article>
        <article className="metric">
          <span>Related matches</span>
          <strong>{relatedMatches.length}</strong>
        </article>
        <article className="metric">
          <span>Average confidence</span>
          <strong>{averageConfidence || 'N/A'}</strong>
        </article>
        <article className="metric">
          <span>Trend</span>
          <strong>{team.trend ?? 'stable'}</strong>
        </article>
      </section>

      <section className="quickActions">
        <Link className="button secondary" href="/matches">
          Tous les matchs
        </Link>
        <Link className="button secondary" href="/predictions">
          Prédictions
        </Link>
        <Link className="button secondary" href="/teams">
          Équipes
        </Link>
      </section>

      <section className="sectionSplit">
        <div>
          <h2>Upcoming matches</h2>
          <div className="stack">
            {relatedMatches.length > 0 ? (
              relatedMatches.map((match) => <MatchCard match={match} key={match.match_id} />)
            ) : (
              <Link className="card clickable-card" href="/matches">
                <p>Aucun match lié disponible. Explorer tous les matchs.</p>
              </Link>
            )}
          </div>
        </div>
        <div>
          <h2>Recent related predictions</h2>
          <div className="stack">
            {relatedPredictions.length > 0 ? (
              relatedPredictions.map((prediction) => (
                <Link className="card clickable-card" href={matchHref(prediction)} key={prediction.match_id}>
                  <h3>
                    {prediction.home_team} vs {prediction.away_team}
                  </h3>
                  <p>{prediction.main_prediction}</p>
                  <div className="confidenceLine confidence-bar">
                    <span style={{ width: `${prediction.confidence.score}%` }} />
                  </div>
                </Link>
              ))
            ) : (
              <Link className="card clickable-card" href="/predictions">
                <p>Aucune prédiction liée disponible.</p>
              </Link>
            )}
          </div>
        </div>
      </section>
      </Layout>
    </ProtectedRoute>
  );
}

function MatchCard({ match }: { match: Match }) {
  return (
    <Link className="card clickable-card" href={matchHref(match)}>
      <span className="muted">{match.competition}</span>
      <h3>
        {match.home_team} vs {match.away_team}
      </h3>
      <p>{new Date(match.kickoff).toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' })}</p>
    </Link>
  );
}
