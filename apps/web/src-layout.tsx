import Link from 'next/link';
import { useRouter } from 'next/router';
import type { ReactNode } from 'react';
import { useAuth } from '~/lib/auth';

const links = [
  { href: '/matches', label: 'Matchs' },
  { href: '/predictions', label: 'Prédictions' },
  { href: '/teams', label: 'Équipes' },
  { href: '/performance', label: 'Analyse' },
];

export function Layout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { user, isAdmin, loading, signOut } = useAuth();
  const hideAuthNavDuringLoginRedirect = router.pathname === '/login' && Boolean(user);
  const isActive = (href: string) => router.pathname === href || router.pathname.startsWith(`${href}/`);

  async function handleLogout() {
    await signOut();
    void router.push('/login');
  }

  return (
    <div className="shell">
      <header className="topbar">
        <Link className="logo" href="/">
          FootIQ Pro
        </Link>
        <nav aria-label="Navigation principale">
          {loading || hideAuthNavDuringLoginRedirect ? null : user ? (
            <>
              <Link className={isActive('/dashboard') ? 'active' : undefined} href="/dashboard">
                Tableau de bord
              </Link>
              {links.map((link) => (
                <Link className={isActive(link.href) ? 'active' : undefined} key={link.href} href={link.href}>
                  {link.label}
                </Link>
              ))}
              <Link className={isActive('/profile') ? 'active' : undefined} href="/profile">
                Profil
              </Link>
              {isAdmin && (
                <Link className={isActive('/admin') ? 'active' : undefined} href="/admin">
                  Admin
                </Link>
              )}
              <button className="navButton logoutButton" type="button" onClick={handleLogout}>
                Déconnexion
              </button>
            </>
          ) : (
            <>
              <Link className={isActive('/about') ? 'active' : undefined} href="/about">
                À propos
              </Link>
              <Link className={isActive('/login') ? 'active' : undefined} href="/login">
                Connexion
              </Link>
              <Link className={isActive('/register') ? 'active' : undefined} href="/register">
                Créer un compte
              </Link>
            </>
          )}
        </nav>
      </header>
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
            Outil d'analyse statistique. Aucune prédiction ne garantit un résultat.
          </span>
          <span className="footerCopy">© {new Date().getFullYear()} FootIQ Pro</span>
        </div>
      </footer>
    </div>
  );
}
