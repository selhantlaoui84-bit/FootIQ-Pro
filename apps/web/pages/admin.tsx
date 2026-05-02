import { useEffect, useState } from 'react';
import Link from 'next/link';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { getBackendHealth, getRefreshStatus, refreshData } from '~/lib/api';
import { useAuth } from '~/lib/auth';
import type { HealthResponse, RefreshResponse } from '~/lib/mock-data';
import { Layout } from '~/src-layout';

export default function AdminPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [refreshInfo, setRefreshInfo] = useState<RefreshResponse | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const adminKeyConfigured = Boolean(process.env.NEXT_PUBLIC_ADMIN_API_KEY);
  const { user, isAdmin } = useAuth();

  useEffect(() => {
    getBackendHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
    getRefreshStatus()
      .then(setRefreshInfo)
      .catch(() => setRefreshInfo(null));
  }, []);

  async function handleRefresh() {
    setIsRefreshing(true);
    setError(null);

    if (!adminKeyConfigured) {
      setError('Admin key not configured');
      setIsRefreshing(false);
      return;
    }

    try {
      const result = await refreshData();

      if (!result) {
        setError('Refresh unavailable. Check the admin key or backend.');
        return;
      }

      if (result.status === 'error') {
        setError(result.detail ?? result.error ?? 'Refresh refused.');
        return;
      }

      setRefreshInfo(result);
    } catch {
      setError('Refresh impossible pour le moment.');
    } finally {
      setIsRefreshing(false);
    }
  }

  return (
    <ProtectedRoute requireAdmin>
      <Layout>
        <section className="pageHeader">
          <p className="eyebrow">Administration MVP</p>
          <h1>Admin</h1>
          <p>Controle du backend, du refresh football-data.org et de la source active.</p>
          <div className="roleStrip">
            <span className="userBadge">{user?.email ?? 'Unknown user'}</span>
            <span className={`roleBadge ${isAdmin ? 'admin' : ''}`}>{isAdmin ? 'Admin' : 'User'}</span>
          </div>
          <div className="quickActions">
            <Link className="button secondary" href="/dashboard">
              Dashboard
            </Link>
            <Link className="button secondary" href="/matches">
              Matches
            </Link>
            <Link className="button secondary" href="/predictions">
              Predictions
            </Link>
          </div>
        </section>

        <section className="sectionSplit">
          <article className="card">
            <h2>Backend health</h2>
            <div className="dataList">
              <span>
                Status <strong>{health?.status ?? (health?.ok ? 'ok' : 'indisponible')}</strong>
              </span>
              <span>
                API URL <strong>{process.env.NEXT_PUBLIC_API_URL ?? 'non configuree'}</strong>
              </span>
              <span>
                Admin key <strong>{adminKeyConfigured ? 'configured' : 'missing'}</strong>
              </span>
            </div>
          </article>

          <article className="card accent">
            <h2>Refresh data</h2>
            <p>Import Ligue 1 et Champions League, avec fallback mock automatique.</p>
            {!adminKeyConfigured && <div className="banner warning">Admin key not configured</div>}
            {!isAdmin && <div className="banner error">Admin access required.</div>}
            <button
              className="button primary"
              type="button"
              onClick={handleRefresh}
              disabled={isRefreshing || !adminKeyConfigured || !isAdmin}
            >
              {isRefreshing ? 'Refresh en cours...' : 'Refresh data'}
            </button>
          </article>
        </section>

        {error && <section className="banner error">{error}</section>}

        <section className="card">
          <h2>Dernier refresh</h2>
          <div className="dataList">
            <span>
              Status <strong>{refreshInfo?.status ?? 'unknown'}</strong>
            </span>
            <span>
              Source <strong>{refreshInfo?.source ?? 'mock'}</strong>
            </span>
            <span>
              Storage <strong>{refreshInfo?.storage ?? 'memory'}</strong>
            </span>
            <span>
              Matches imported <strong>{refreshInfo?.matches_imported ?? 0}</strong>
            </span>
            <span>
              Teams imported <strong>{refreshInfo?.teams_imported ?? 0}</strong>
            </span>
            <span>
              Last refresh <strong>{refreshInfo?.last_refresh_at ?? 'N/A'}</strong>
            </span>
          </div>
        </section>
      </Layout>
    </ProtectedRoute>
  );
}
