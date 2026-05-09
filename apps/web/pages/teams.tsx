import type { GetStaticProps } from 'next';
import Link from 'next/link';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { TeamCrest } from '~/components/ui';
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
        <section className="pageHeader premiumPageIntro">
          <h1>Équipes</h1>
          <p>
            {teams.length} équipes suivies
            {competitions ? ` sur ${competitions}` : ''}.
          </p>
        </section>

        <section className="teamsPremiumLayout">
          {teams.map((team) => (
            <Link className="premiumPanel teamPremiumCard clickable-card" href={teamHref(team)} key={team.id}>
              <div className="cardTop">
                <span>{team.competition}</span>
                <span className={`trend ${team.trend ?? 'stable'}`}>{team.trend ?? 'stable'}</span>
              </div>
              <TeamCrest name={team.name} />
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
              <TeamDataQuality team={team} />
            </Link>
          ))}
        </section>
      </Layout>
    </ProtectedRoute>
  );
}

function TeamDataQuality({ team }: { team: Team }) {
  const elo = typeof team.elo === 'number' ? team.elo : null;
  const eloScore = elo === null ? 0 : Math.max(0, Math.min(100, ((elo - 1400) / 600) * 100));
  const formLetters = String(team.form ?? '')
    .replace(/\s+/g, '')
    .split('')
    .filter(Boolean)
    .slice(0, 5);

  return (
    <div className="teamDataQuality">
      <div className="dataBar">
        <span>Niveau Elo</span>
        <strong>{elo ?? 'N/A'}</strong>
        <div><i style={{ width: `${eloScore || 4}%` }} /></div>
      </div>
      <div className="formBadges" aria-label="Forme récente">
        {formLetters.length > 0 ? (
          formLetters.map((letter, index) => <span className={`form-${letter.toLowerCase()}`} key={`${letter}-${index}`}>{letter}</span>)
        ) : (
          <span className="muted">Forme non disponible</span>
        )}
      </div>
    </div>
  );
}
