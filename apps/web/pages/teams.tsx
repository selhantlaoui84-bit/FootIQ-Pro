import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getTeams } from '~/lib/api';
import { teamHref, teams as mockTeams, type Team } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

type TeamsProps = {
  teams: Team[];
};

export const getStaticProps: GetStaticProps<TeamsProps> = async () => {
  try {
    return { props: { teams: await getTeams() }, revalidate: 120 };
  } catch (error) {
    console.error('Teams ISR fallback:', error);
    return { props: { teams: mockTeams }, revalidate: 120 };
  }
};

export default function TeamsPage({ teams }: TeamsProps) {
  const competitions = [...new Set(teams.map((team) => team.competition))].join(' / ');

  return (
    <ProtectedRoute>
      <Layout>
        <section className="pageHeader">
          <p className="eyebrow">Référentiel équipes</p>
          <h1>Équipes</h1>
          <p>
            {teams.length} équipes disponibles
            {competitions ? ` sur ${competitions}` : ''}.
          </p>
        </section>

        <section className="grid three">
          {teams.map((team) => (
            <Link className="card teamCard clickable-card" href={teamHref(team)} key={team.id}>
              <div className="cardTop">
                <span>{team.competition}</span>
                <span className={`trend ${team.trend ?? 'stable'}`}>{team.trend ?? 'stable'}</span>
              </div>
              <h2>{team.name}</h2>
              <div className="dataList">
                <span>
                  Rating Elo <strong>{team.elo ?? 'N/A'}</strong>
                </span>
                <span>
                  Forme récente <strong>{team.form ?? 'N/A'}</strong>
                </span>
                <span>
                  Source <strong>{team.source ?? 'mock'}</strong>
                </span>
              </div>
            </Link>
          ))}
        </section>
      </Layout>
    </ProtectedRoute>
  );
}
