import Head from 'next/head';
import { Layout } from '~/src-layout';

export default function Confidentialite() {
  return (
    <Layout>
      <Head>
        <title>Politique de confidentialité — FootIQ Pro</title>
        <meta name="robots" content="noindex" />
      </Head>
      <article className="legalPage">
        <h1>Politique de confidentialité</h1>
        <p className="legalDate">Dernière mise à jour : mai 2026</p>

        <section>
          <h2>Données collectées</h2>
          <p>
            FootIQ Pro collecte uniquement les données strictement nécessaires au fonctionnement
            du service :
          </p>
          <ul>
            <li>Adresse e-mail (identification du compte)</li>
            <li>Mot de passe (stocké sous forme hachée via Supabase Auth)</li>
          </ul>
          <p>Aucune donnée bancaire, aucune donnée de localisation n'est collectée.</p>
        </section>

        <section>
          <h2>Finalité du traitement</h2>
          <p>
            Les données collectées sont utilisées exclusivement pour authentifier les
            utilisateurs et leur donner accès au tableau de bord et aux analyses.
          </p>
        </section>

        <section>
          <h2>Base légale</h2>
          <p>
            Le traitement est fondé sur l'exécution d'un contrat (accès au service) conformément
            à l'article 6(1)(b) du RGPD.
          </p>
        </section>

        <section>
          <h2>Conservation des données</h2>
          <p>
            Les données de compte sont conservées jusqu'à la suppression du compte par
            l'utilisateur, ou pendant une durée maximale de 3 ans après la dernière connexion.
          </p>
        </section>

        <section>
          <h2>Sous-traitants</h2>
          <p>
            L'authentification est gérée par <strong>Supabase</strong> (Supabase Inc., États-Unis),
            soumis à des clauses contractuelles types conformes au RGPD.
          </p>
          <p>
            L'hébergement est assuré par <strong>Vercel Inc.</strong> (États-Unis), également
            soumis à des clauses contractuelles types.
          </p>
        </section>

        <section>
          <h2>Vos droits</h2>
          <p>
            Conformément au RGPD, vous disposez des droits d'accès, de rectification, d'effacement,
            de portabilité et d'opposition. Pour exercer ces droits, contactez :{' '}
            <a href="mailto:contact@footiq.pro">contact@footiq.pro</a>.
          </p>
          <p>
            Vous pouvez également introduire une réclamation auprès de la CNIL (
            <a href="https://www.cnil.fr" target="_blank" rel="noopener noreferrer">
              www.cnil.fr
            </a>
            ).
          </p>
        </section>

        <section>
          <h2>Cookies</h2>
          <p>
            FootIQ Pro utilise uniquement les cookies techniques nécessaires à l'authentification
            (session Supabase). Aucun cookie publicitaire ou de suivi tiers n'est déposé.
          </p>
        </section>
      </article>
    </Layout>
  );
}
