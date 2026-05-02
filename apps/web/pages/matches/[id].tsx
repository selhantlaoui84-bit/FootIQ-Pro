import type { GetStaticPaths, GetStaticProps } from 'next';
import Link from 'next/link';
import { InfoTooltip } from '~/components/InfoTooltip';
import { ProtectedRoute } from '~/components/ProtectedRoute';
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
    <ProtectedRoute>
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
              Modèle <strong>{prediction.model_version ?? 'elo-poisson-calibrated-v1'}</strong>
            </span>
            <span>
              Score attendu{' '}
              <strong>
                {prediction.goals.expected_home} - {prediction.goals.expected_away}
              </strong>
            </span>
            <span>
              Score probable <strong>{prediction.goals.most_likely_score ?? 'N/A'}</strong>
            </span>
            <span>
              Over 1.5 <strong>{prediction.goals.over_1_5 ?? 'N/A'}%</strong>
            </span>
            <span>
              Over 2.5 <strong>{prediction.goals.over_2_5}%</strong>
            </span>
            <span>
              Over 3.5 <strong>{prediction.goals.over_3_5 ?? 'N/A'}%</strong>
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
          <h2 className="metricHelp">
            Indice de confiance
            <InfoTooltip content="Indice de confiance du modèle. Il mesure la lisibilité statistique du match, pas une certitude de résultat." />
          </h2>
          <strong className="bigScore">{prediction.confidence.score}/100</strong>
          <div className="confidenceLine tall confidence-bar">
            <span style={{ width: `${prediction.confidence.score}%` }} />
          </div>
          <div className="dataList">
            <span>
              <span className="metricHelp">Score de risque <InfoTooltip content="Score de risque contextuel. Plus il est élevé, plus le match est difficile à lire." /></span>
              <strong>{prediction.risk_score ?? 'N/A'}</strong>
            </span>
            <span>
              <span className="metricHelp">Score piège <InfoTooltip content="Indique un match potentiellement piégeux malgré un favori apparent." /></span>
              <strong>{prediction.trap_match_score ?? 'N/A'}</strong>
            </span>
            <span>
              Qualité des données <strong>{prediction.features?.data_quality_score ?? 'N/A'}</strong>
            </span>
          </div>
          <p>{prediction.recommendation}</p>
        </article>
      </section>

      <section className="grid three">
        <article className="card">
          <h2>Elo</h2>
          <strong className="bigScore">{prediction.features?.elo_delta ?? 'N/A'}</strong>
          <p>Écart Elo ajusté avec avantage domicile.</p>
          <InfoTooltip content="Écart de niveau relatif entre les deux équipes selon le système Elo." />
        </article>
        <article className="card">
          <h2>Forme</h2>
          <strong className="bigScore">{prediction.features?.form_delta ?? 'N/A'}</strong>
          <p>Différentiel de dynamique récente.</p>
          <InfoTooltip content="Différence de forme récente entre les équipes." />
        </article>
        <article className="card">
          <h2>Attaque / Défense</h2>
          <div className="dataList">
            <span>Écart attaque <strong>{prediction.features?.attack_delta ?? 'N/A'}</strong></span>
            <span>Écart défense <strong>{prediction.features?.defense_delta ?? 'N/A'}</strong></span>
            <span>Risque de nul <strong>{prediction.features?.draw_risk_score ?? 'N/A'}</strong></span>
          </div>
        </article>
      </section>


      <section className="sectionSplit">
        <article className="card accent">
          <h2>Calibration</h2>
          <div className="dataList">
            <span>
              Appliquée <strong>{prediction.calibration?.applied ? 'oui' : 'oui'}</strong>
            </span>
            <span>
              Méthode <strong>{prediction.calibration?.method ?? 'conservative_probability_smoothing'}</strong>
            </span>
            <span>
              Pénalité de confiance <strong>{prediction.calibration?.confidence_penalty ?? 'N/A'}</strong>
            </span>
          </div>
          <p>Le modèle réduit les probabilités trop agressives pour améliorer la calibration.</p>
        </article>
        <article className="card">
          <h2>Lissage des probabilités</h2>
          <p>Les favoris trop hauts sont légèrement lissés et le nul est rehaussé lorsque le match reste incertain.</p>
        </article>
      </section>

      <section className="sectionSplit">
        <article className="card accent">
          <h2>Recommandation FootIQ</h2>
          <strong>{prediction.recommendation}</strong>
          <p>{prediction.main_prediction}</p>
        </article>
        <article className={prediction.flags.trap_match || prediction.flags.risk ? 'card danger' : 'card'}>
          <h2>{prediction.flags.trap_match ? 'Match piège détecté' : 'Alerte de risque'}</h2>
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
    </ProtectedRoute>
  );
}

function Probability({ label, value }: { label: string; value: number }) {
  return (
    <article className="card probability">
      <span className="metricHelp">
        {label}
        <InfoTooltip content="Probabilité estimée par le modèle. Elle exprime une tendance statistique, pas une garantie." />
      </span>
      <strong>{value}%</strong>
      <div className="probabilityBar confidence-bar">
        <span style={{ width: `${value}%` }} />
      </div>
    </article>
  );
}

