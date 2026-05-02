import Link from 'next/link';
import type { ReactNode } from 'react';

const links = [
  { href: '/dashboard', label: 'Dashboard' },
  { href: '/matches', label: 'Matches' },
  { href: '/predictions', label: 'Predictions' },
  { href: '/teams', label: 'Teams' },
  { href: '/performance', label: 'Performance' },
  { href: '/about', label: 'About' },
  { href: '/admin', label: 'Admin' },
];

export function Layout({ children }: { children: ReactNode }) {
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
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
