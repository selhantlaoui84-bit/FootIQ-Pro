import Head from 'next/head';
import { Layout } from '~/src-layout';

export default function MentionsLegales() {
  return (
    <Layout>
      <Head>
        <title>Mentions légales — FootIQ Pro</title>
        <meta name="robots" content="noindex" />
      </Head>
      <article className="legalPage">
        <h1>Mentions légales</h1>

        <section>
          <h2>Éditeur</h2>
          <p>
            FootIQ Pro est un projet à titre personnel / expérimental. Il n'est pas exploité
            par une société immatriculée. Pour toute question, contacter :{' '}
            <a href="mailto:contact@footiq.pro">contact@footiq.pro</a>.
          </p>
        </section>

        <section>
          <h2>Hébergement</h2>
          <p>
            Ce site est hébergé par <strong>Vercel Inc.</strong>, 340 Pine Street, Suite 701,
            San Francisco, CA 94104, États-Unis.
          </p>
        </section>

        <section>
          <h2>Propriété intellectuelle</h2>
          <p>
            L'ensemble du contenu de ce site (textes, algorithmes, design) est la propriété de
            l'éditeur. Toute reproduction sans autorisation écrite est interdite.
          </p>
        </section>

        <section>
          <h2>Responsabilité</h2>
          <p>
            FootIQ Pro est un outil d'analyse statistique et probabiliste. Aucune prédiction
            ne garantit un résultat sportif. L'éditeur décline toute responsabilité quant à
            l'utilisation des données présentées.
          </p>
        </section>
      </article>
    </Layout>
  );
}
