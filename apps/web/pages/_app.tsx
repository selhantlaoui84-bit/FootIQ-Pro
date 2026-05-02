import type { AppProps } from "next/app";
import Link from "next/link";
import "../styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <>
      <nav className="top-nav">
        <Link href="/" className="brand">
          FootIQ Pro
        </Link>

        <div className="nav-links">
  <Link href="/dashboard">Dashboard</Link>
  <Link href="/matches">Matches</Link>
  <Link href="/predictions">Predictions</Link>
  <Link href="/teams">Teams</Link>
  <Link href="/performance">Performance</Link>
  <Link href="/about">About</Link>
  <Link href="/admin">Admin</Link>
</div>
      </nav>

      <Component {...pageProps} />
    </>
  );
}

