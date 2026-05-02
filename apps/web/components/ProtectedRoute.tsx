import { useRouter } from 'next/router';
import { useEffect, type ReactNode } from 'react';
import { useAuth } from '~/lib/auth';

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { user, loading } = useAuth();

  useEffect(() => {
    if (!loading && !user) {
      const next = router.asPath || '/dashboard';
      void router.replace(`/login?next=${encodeURIComponent(next)}`);
    }
  }, [loading, router, user]);

  if (loading || !user) {
    return (
      <section className="protectedLoading">
        <div className="skeleton" />
        <p>Verification de la session...</p>
      </section>
    );
  }

  return <>{children}</>;
}
