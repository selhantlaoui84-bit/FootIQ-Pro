import Head from 'next/head';
import { Layout } from '~/src-layout';

export default function CGU() {
  return (
    <Layout>
      <Head>
        <title>Conditions générales d'utilisation — FootIQ Pro</title>
        <meta name="robots" content="noindex" />
      </Head>
      <article className="legalPage">
        <h1>Conditions générales d'utilisation</h1>
        <p className="legalDate">En vigueur depuis : mai 2026</p>

        <section>
          <h2>Objet</h2>
          <p>
            Les présentes CGU définissent les conditions d'accès et d'utilisation du service
            FootIQ Pro, outil d'analyse probabiliste du football.
          </p>
        </section>

        <section>
          <h2>Accès au service</h2>
          <p>
            L'accès au tableau de bord nécessite la création d'un compte. L'utilisateur
            s'engage à fournir des informations exactes et à maintenir la confidentialité de
            ses identifiants.
          </p>
        </section>

        <section>
          <h2>Utilisation autorisée</h2>
          <p>
            FootIQ Pro est destiné à un usage personnel d'analyse et d'information sportive.
            Toute utilisation commerciale, revente ou extraction automatisée des données est
            interdite sans autorisation écrite préalable.
          </p>
        </section>

        <section>
          <h2>Avertissement sur les analyses</h2>
          <p>
            Les analyses, probabilités et signaux fournis par FootIQ Pro sont des outils
            d'aide à la décision basés sur des modèles statistiques. <strong>Ils ne constituent
            en aucun cas des conseils de paris ou des garanties de résultats sportifs.</strong>
          </p>
          <p>
            L'éditeur décline toute responsabilité pour toute décision prise sur la base
            des informations présentées.
          </p>
        </section>

        <section>
          <h2>Propriété intellectuelle</h2>
          <p>
            Les algorithmes, données, interfaces et contenus de FootIQ Pro sont protégés
            par le droit de la propriété intellectuelle. Toute reproduction est interdite
            sans autorisation.
          </p>
        </section>

        <section>
          <h2>Droit applicable</h2>
          <p>
            Les présentes CGU sont soumises au droit français. Tout litige sera soumis
            à la compétence des tribunaux français.
          </p>
        </section>

        <section>
          <h2>Contact</h2>
          <p>
            Pour toute question :{' '}
            <a href="mailto:contact@footiq.pro">contact@footiq.pro</a>
          </p>
        </section>
      </article>
    </Layout>
  );
}
