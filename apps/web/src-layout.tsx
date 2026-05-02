import Link from 'next/link';
import { useRouter } from 'next/router';
import type { ReactNode } from 'react';
import { useAuth } from '~/lib/auth';

const links = [
  { href: '/matches', label: 'Matches' },
  { href: '/predictions', label: 'Predictions' },
  { href: '/teams', label: 'Teams' },
  { href: '/performance', label: 'Performance' },
  { href: '/about', label: 'About' },
];

export function Layout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { user, signOut } = useAuth();

  async function handleLogout() {
    await signOut();
    void router.push('/');
  }

  return (
    <div className="shell">
      <header className="topbar">
        <Link className="logo" href="/">
          FootIQ Pro
        </Link>
        <nav>
          {links.map((link) => (
            <Link key={link.href} href={link.href}>
              {link.label}
            </Link>
          ))}
          {user ? (
            <>
              <Link href="/dashboard">Dashboard</Link>
              <Link href="/profile">Profile</Link>
              <Link href="/admin">Admin</Link>
              <button className="navButton logoutButton" type="button" onClick={handleLogout}>
                Logout
              </button>
            </>
          ) : (
            <>
              <Link href="/login">Login</Link>
              <Link href="/register">Register</Link>
            </>
          )}
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
