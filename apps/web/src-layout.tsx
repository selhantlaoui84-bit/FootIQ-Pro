import Link from 'next/link';
import { useRouter } from 'next/router';
import type { ReactNode } from 'react';
import { useAuth } from '~/lib/auth';

const links = [
  { href: '/matches', label: 'Matchs', icon: '▣' },
  { href: '/predictions', label: 'Prédictions', icon: '◎' },
  { href: '/teams', label: 'Équipes', icon: '◇' },
  { href: '/performance', label: 'Analyse', icon: '↗' },
];

function formatToday() {
  return new Intl.DateTimeFormat('fr-FR', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date());
}

export function Layout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { user, isAdmin, loading, signOut } = useAuth();
  const hideAuthNavDuringLoginRedirect = router.pathname === '/login' && Boolean(user);
  const isActive = (href: string) => router.pathname === href || router.pathname.startsWith(`${href}/`);
  const today = formatToday();

  async function handleLogout() {
    await signOut();
    void router.push('/login');
  }

  return (
    <div className="shell appShell">
      <header className="topbar appSidebar">
        <Link className="logo premiumLogo" href="/">
          <span>FootIQ</span> <em>Pro</em>
        </Link>
        <p className="brandTagline">L'analyse. L'avantage. La victoire.</p>

        <nav aria-label="Navigation principale" className="mainNav">
          {loading || hideAuthNavDuringLoginRedirect ? null : user ? (
            <>
              <Link className={isActive('/dashboard') ? 'active' : undefined} href="/dashboard">
                <span aria-hidden="true">▦</span>
                Tableau de bord
              </Link>
              {links.map((link) => (
                <Link className={isActive(link.href) ? 'active' : undefined} key={link.href} href={link.href}>
                  <span aria-hidden="true">{link.icon}</span>
                  {link.label}
                </Link>
              ))}
              <Link className={isActive('/my-bets') ? 'active' : undefined} href="/my-bets">
                <span aria-hidden="true">▱</span>
                Mes paris
              </Link>
              {isAdmin && (
                <Link className={isActive('/admin') ? 'active' : undefined} href="/admin">
                  <span aria-hidden="true">♢</span>
                  Admin
                </Link>
              )}
            </>
          ) : (
            <>
              <Link className={isActive('/about') ? 'active' : undefined} href="/about">
                <span aria-hidden="true">◇</span>
                À propos
              </Link>
              <Link className={isActive('/login') ? 'active' : undefined} href="/login">
                <span aria-hidden="true">◎</span>
                Connexion
              </Link>
              <Link className={isActive('/register') ? 'active' : undefined} href="/register">
                <span aria-hidden="true">＋</span>
                Créer un compte
              </Link>
            </>
          )}
        </nav>

        {user ? (
          <div className="sidebarAccount">
            <div className="analystBadge">
              <span>IQ</span>
              <div>
                <strong>FootIQ Pro</strong>
                <small>Analyste Élite</small>
              </div>
              <em>PRO</em>
            </div>
            <div className="portfolioCard">
              <span>Solde du portefeuille</span>
              <strong>24 580,75 €</strong>
              <small>Évolution (30 jours)</small>
              <b>+12,47%</b>
              <div className="sparkline" aria-hidden="true" />
            </div>
            <button className="navButton logoutButton logoutWide" type="button" onClick={handleLogout}>
              Déconnexion
            </button>
          </div>
        ) : (
          <div className="sidebarAccount">
            <div className="portfolioCard">
              <span>Mode découverte</span>
              <strong>Analytics IA</strong>
              <small>Probabilités, risque et performance.</small>
            </div>
          </div>
        )}
      </header>

      <div className="contentShell">
        <div className="pageToolbar" aria-label="Commandes rapides">
          <span className="toolbarDate">▣ {today}</span>
          <span className="toolbarButton">◇ Alertes</span>
          <span className="toolbarButton">▽ Filtres</span>
        </div>
        <main>{children}</main>
        <footer className="siteFooter">
          <div className="footerInner">
            <span className="footerBrand">FootIQ Pro</span>
            <nav className="footerLinks" aria-label="Navigation secondaire">
              <a href="/about">À propos</a>
              <a href="/mentions-legales">Mentions légales</a>
              <a href="/confidentialite">Confidentialité</a>
              <a href="/cgu">CGU</a>
            </nav>
            <span className="footerNotice">
              Outil d'analyse statistique. Chaque prédiction conserve une incertitude.
            </span>
            <span className="footerCopy">© {new Date().getFullYear()} FootIQ Pro</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
