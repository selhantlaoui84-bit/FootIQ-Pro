import { useRouter } from 'next/router';
import Link from 'next/link';
import { useEffect, type ReactNode } from 'react';
import { useAuth } from '~/lib/auth';

type ProtectedRouteProps = {
  children: ReactNode;
  requireAuth?: boolean;
  requireAdmin?: boolean;
};

export function ProtectedRoute({ children, requireAuth = true, requireAdmin = false }: ProtectedRouteProps) {
  const router = useRouter();
  const { isAuthenticated, isAdmin, loading, user, adminEmail } = useAuth();

  useEffect(() => {
    if (!loading && requireAuth && !isAuthenticated) {
      const next = router.asPath || '/dashboard';
      void router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [isAuthenticated, loading, requireAuth, router]);

  if (loading || (requireAuth && !isAuthenticated)) {
    return (
      <section className="protectedLoading authLockedScreen">
        <div className="skeleton" />
        <p>Vérification de la session...</p>
      </section>
    );
  }

  if (requireAdmin && !isAdmin) {
    return (
      <section className="authLockedScreen">
        <article className="accessDeniedCard">
          <span className="roleBadge">Utilisateur</span>
          <h1>Accès refusé</h1>
          <p>
            La console admin est réservée à {adminEmail}. Vous êtes connecté avec {user?.email ?? 'utilisateur inconnu'}.
          </p>
          <Link className="button primary" href="/dashboard">
            Retour au tableau de bord
          </Link>
        </article>
      </section>
    );
  }

  return <>{children}</>;
}

