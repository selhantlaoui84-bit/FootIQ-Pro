import Link from 'next/link';
import { useRouter } from 'next/router';
import type { ReactNode } from 'react';
import { useAuth } from '~/lib/auth';

const links = [
  { href: '/matches', label: 'Matchs' },
  { href: '/predictions', label: 'Prédictions' },
  { href: '/teams', label: 'Équipes' },
  { href: '/performance', label: 'Performance' },
];

export function Layout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { user, isAdmin, signOut } = useAuth();

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
        <nav>
          {user ? (
            <>
              <Link href="/dashboard">Tableau de bord</Link>
              {links.map((link) => (
                <Link key={link.href} href={link.href}>
                  {link.label}
                </Link>
              ))}
              <Link href="/profile">Profil</Link>
              {isAdmin && <Link href="/admin">Admin</Link>}
              <button className="navButton logoutButton" type="button" onClick={handleLogout}>
                Déconnexion
              </button>
            </>
          ) : (
            <>
              <Link href="/about">À propos</Link>
              <Link href="/login">Connexion</Link>
              <Link href="/register">Créer un compte</Link>
            </>
          )}
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}

