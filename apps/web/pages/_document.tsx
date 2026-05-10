import { Html, Head, Main, NextScript } from 'next/document';

const META = {
  title: 'FootIQ Pro - Analytics probabiliste du football',
  description:
    "FootIQ Pro identifie les matchs statistiquement lisibles, les signaux de confiance et les pièges du football français et européen. Analyse probabiliste, pas de promesses.",
  url: 'https://foot-iq-pro-ten.vercel.app',
  image: 'https://foot-iq-pro-ten.vercel.app/og-image.png',
};

export default function Document() {
  return (
    <Html lang="fr">
      <Head>
        {/* Favicon */}
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <link rel="shortcut icon" href="/favicon.svg" />

        {/* Primary meta */}
        <meta name="description" content={META.description} />
        <meta name="robots" content="index, follow" />
        <meta name="theme-color" content="#050812" />

        {/* Open Graph */}
        <meta property="og:type" content="website" />
        <meta property="og:site_name" content="FootIQ Pro" />
        <meta property="og:title" content={META.title} />
        <meta property="og:description" content={META.description} />
        <meta property="og:url" content={META.url} />
        <meta property="og:image" content={META.image} />
        <meta property="og:locale" content="fr_FR" />

        {/* Twitter / X */}
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:title" content={META.title} />
        <meta name="twitter:description" content={META.description} />
        <meta name="twitter:image" content={META.image} />

        {/* Structured data - SoftwareApplication */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              '@context': 'https://schema.org',
              '@type': 'SoftwareApplication',
              name: 'FootIQ Pro',
              applicationCategory: 'SportsApplication',
              operatingSystem: 'Web',
              description: META.description,
              url: META.url,
              offers: { '@type': 'Offer', price: '0', priceCurrency: 'EUR' },
            }),
          }}
        />
      </Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
