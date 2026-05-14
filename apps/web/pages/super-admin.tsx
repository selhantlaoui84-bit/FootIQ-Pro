import { useEffect, useMemo, useState } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { Card, EmptyState, ErrorState, LoadingState, MetricCard, PageHeader, StatBadge } from '~/components/ui';
import {
  getEntitlements,
  getPayments,
  getProductionHealth,
  getRevenueSummary,
  getSaasPlans,
  getSubscriptions,
  getSuperAdminAuditLog,
  getSuperAdminOverview,
  getSuperAdminUsers,
  promoteSuperAdminUser,
  restoreSuperAdminUser,
  suspendSuperAdminUser,
} from '~/lib/api';
import { useAuth } from '~/lib/auth';
import { Layout } from '~/src-layout';

type SuperAdminState = {
  overview: any | null;
  users: any[];
  plans: any[];
  subscriptions: any[];
  payments: any[];
  entitlements: any[];
  auditLog: any[];
  revenue: any | null;
  productionHealth: any | null;
};

const emptyState: SuperAdminState = {
  overview: null,
  users: [],
  plans: [],
  subscriptions: [],
  payments: [],
  entitlements: [],
  auditLog: [],
  revenue: null,
  productionHealth: null,
};

function formatMoney(cents?: number | null, currency = 'EUR') {
  if (cents === null || cents === undefined) return 'Données insuffisantes';
  return new Intl.NumberFormat('fr-FR', { style: 'currency', currency }).format(cents / 100);
}

function DataTable({ columns, rows, empty }: { columns: string[]; rows: any[]; empty: string }) {
  if (!rows.length) return <EmptyState>{empty}</EmptyState>;
  return (
    <div className="tableWrap superAdminTable">
      <table>
        <thead>
          <tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  );
}

export default function SuperAdminPage() {
  const { session, isSuperAdmin, platformUser } = useAuth();
  const accessToken = session?.access_token;
  const [state, setState] = useState<SuperAdminState>(emptyState);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  async function load() {
    if (!accessToken || !isSuperAdmin) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [overview, users, plans, subscriptions, payments, entitlements, auditLog, revenue, productionHealth] = await Promise.all([
        getSuperAdminOverview(accessToken),
        getSuperAdminUsers(undefined, accessToken),
        getSaasPlans(accessToken),
        getSubscriptions(undefined, accessToken),
        getPayments(undefined, accessToken),
        getEntitlements(undefined, accessToken),
        getSuperAdminAuditLog(undefined, accessToken),
        getRevenueSummary(accessToken),
        getProductionHealth(),
      ]);
      setState({
        overview,
        users: users?.items ?? [],
        plans: plans?.items ?? [],
        subscriptions: subscriptions?.items ?? [],
        payments: payments?.items ?? [],
        entitlements: entitlements?.items ?? [],
        auditLog: auditLog?.items ?? [],
        revenue,
        productionHealth,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Super Admin indisponible.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [accessToken, isSuperAdmin]);

  async function runUserAction(userId: string, action: 'promote' | 'suspend' | 'restore', role?: 'admin' | 'super_admin') {
    if (!accessToken) return;
    setActionMessage(null);
    try {
      if (action === 'promote') await promoteSuperAdminUser(userId, { confirm: true, role }, accessToken);
      if (action === 'suspend') await suspendSuperAdminUser(userId, { confirm: true }, accessToken);
      if (action === 'restore') await restoreSuperAdminUser(userId, { confirm: true }, accessToken);
      setActionMessage('Action appliquée et journalisée.');
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Action impossible.');
    }
  }

  const kpis = useMemo(() => {
    const overview = state.overview ?? {};
    return [
      ['Utilisateurs totaux', overview.total_users],
      ['Utilisateurs actifs', overview.active_users],
      ['Abonnés payants', overview.paying_subscribers],
      ['MRR', formatMoney(overview.monthly_revenue_cents)],
      ['Paiements échoués', overview.failed_payments],
      ['Churn risk', overview.churn_risk_count],
      ['Plans actifs', overview.active_plans],
      ['Nouveaux inscrits', overview.latest_signups?.length],
    ];
  }, [state.overview]);

  return (
    <ProtectedRoute requireSuperAdmin>
      <Layout>
        <section className="pageStack superAdminPage">
          <PageHeader eyebrow="Super Admin SaaS" title="Pilotage plateforme FootIQ Pro">
            <p>Pilotage abonnés, paiements, droits d'accès et santé commerciale FootIQ Pro.</p>
            <div className="chipRow">
              <StatBadge tone="premium">super_admin</StatBadge>
              <StatBadge tone="success">propriétaire : samir.elh@outlook.fr</StatBadge>
              <StatBadge tone="info">plateforme {state.overview?.storage ?? 'postgresql'}</StatBadge>
              <StatBadge tone="warning">dernière mise à jour temps réel</StatBadge>
            </div>
          </PageHeader>

          {loading && <LoadingState label="Chargement Super Admin..." />}
          {error && <ErrorState>{error}</ErrorState>}
          {actionMessage && <section className="banner success">{actionMessage}</section>}

          {!loading && (
            <>
              <section className="metricsGrid">
                {kpis.map(([label, value]) => (
                  <MetricCard key={label} label={String(label)} value={value ?? 'Données insuffisantes'} />
                ))}
              </section>

              <section className="adminGrid two">
                <Card className="span2">
                  <div className="cardHeader">
                    <div>
                      <p className="eyebrow">Gestion utilisateurs</p>
                      <h2>Utilisateurs et rôles</h2>
                    </div>
                    <StatBadge tone="info">{state.users.length} comptes</StatBadge>
                  </div>
                  <DataTable
                    columns={['Email', 'Nom', 'Rôle', 'Statut', 'Plan', 'Actions']}
                    empty="Aucun utilisateur réel enregistré."
                    rows={state.users.map((user) => (
                      <tr key={user.id ?? user.email}>
                        <td>{user.email}</td>
                        <td>{user.display_name ?? 'Données insuffisantes'}</td>
                        <td><span className="statusBadge tone-premium">{user.role}</span></td>
                        <td>{user.status}</td>
                        <td>{user.plan_id ?? 'free'}</td>
                        <td>
                          <div className="inlineActions">
                            <button className="button tiny" type="button" onClick={() => void runUserAction(user.id, 'promote', 'admin')}>Admin</button>
                            <button className="button tiny" type="button" onClick={() => void runUserAction(user.id, 'promote', 'super_admin')}>Super</button>
                            <button className="button tiny danger" type="button" onClick={() => void runUserAction(user.id, 'suspend')}>Suspendre</button>
                            <button className="button tiny" type="button" onClick={() => void runUserAction(user.id, 'restore')}>Restaurer</button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  />
                </Card>

                <Card>
                  <p className="eyebrow">Plans SaaS</p>
                  <h2>Free, Pro, Premium, Enterprise</h2>
                  <div className="stackList">
                    {state.plans.map((plan) => (
                      <div className="stackItem" key={plan.id ?? plan.code}>
                        <strong>{plan.name}</strong>
                        <span>{formatMoney(plan.price_monthly_cents, plan.currency)} / mois</span>
                        <small>{plan.description}</small>
                      </div>
                    ))}
                  </div>
                </Card>

                <Card>
                  <p className="eyebrow">Revenue summary</p>
                  <h2>Revenus réels</h2>
                  <MetricCard label="Revenus 30 jours" value={formatMoney(state.revenue?.revenue_30_days_cents, state.revenue?.currency)} />
                  <p className="mutedText">{state.revenue?.note ?? 'Données Stripe synchronisées côté serveur.'}</p>
                </Card>

                <Card>
                  <p className="eyebrow">Production Health</p>
                  <h2>Monitoring production</h2>
                  <div className="dataList">
                    <span>Database <strong>{state.productionHealth?.database ?? 'Données insuffisantes'}</strong></span>
                    <span>Stripe <strong>{state.productionHealth?.stripe ?? 'Données insuffisantes'}</strong></span>
                    <span>Webhook <strong>{state.productionHealth?.stripe_webhook ?? 'Données insuffisantes'}</strong></span>
                    <span>Cotes réelles <strong>{state.productionHealth?.odds_provider ?? 'Données insuffisantes'}</strong></span>
                    <span>Paiements échoués 24h <strong>{state.productionHealth?.failed_payments_24h ?? 'Données insuffisantes'}</strong></span>
                  </div>
                </Card>

                <Card className="span2">
                  <p className="eyebrow">Abonnements</p>
                  <h2>Subscriptions</h2>
                  <DataTable
                    columns={['Utilisateur', 'Plan', 'Statut', 'Provider', 'Période', 'Cancel']}
                    empty="Aucun abonnement réel enregistré."
                    rows={state.subscriptions.map((item) => (
                      <tr key={item.id}>
                        <td>{item.email ?? item.user_id}</td>
                        <td>{item.plan_code ?? item.plan_id}</td>
                        <td>{item.status}</td>
                        <td>{item.provider}</td>
                        <td>{item.current_period_end ?? 'Données insuffisantes'}</td>
                        <td>{item.cancel_at_period_end ? 'oui' : 'non'}</td>
                      </tr>
                    ))}
                  />
                </Card>

                <Card className="span2">
                  <p className="eyebrow">Paiements</p>
                  <h2>Transactions réelles</h2>
                  <DataTable
                    columns={['Utilisateur', 'Montant', 'Statut', 'Provider', 'Date', 'Référence']}
                    empty="Aucun paiement réel enregistré."
                    rows={state.payments.map((item) => (
                      <tr key={item.id}>
                        <td>{item.email ?? item.user_id}</td>
                        <td>{formatMoney(item.amount_cents, item.currency)}</td>
                        <td>{item.status}</td>
                        <td>{item.provider}</td>
                        <td>{item.paid_at ?? item.created_at ?? 'Données insuffisantes'}</td>
                        <td>{item.provider_payment_id ?? 'Données insuffisantes'}</td>
                      </tr>
                    ))}
                  />
                </Card>

                <Card className="span2">
                  <p className="eyebrow">Droits d'accès</p>
                  <h2>Entitlements</h2>
                  <DataTable
                    columns={['Utilisateur', 'Feature', 'Actif', 'Source', 'Expiration']}
                    empty="Aucun droit d'accès enregistré."
                    rows={state.entitlements.map((item) => (
                      <tr key={`${item.user_id}-${item.feature_key}`}>
                        <td>{item.email ?? item.user_id}</td>
                        <td>{item.feature_key}</td>
                        <td>{item.enabled ? 'oui' : 'non'}</td>
                        <td>{item.source}</td>
                        <td>{item.expires_at ?? 'Permanent'}</td>
                      </tr>
                    ))}
                  />
                </Card>

                <Card className="span2">
                  <p className="eyebrow">Audit log</p>
                  <h2>Actions critiques</h2>
                  <DataTable
                    columns={['Date', 'Acteur', 'Action', 'Cible', 'Résultat']}
                    empty="Aucune action critique journalisée."
                    rows={state.auditLog.map((item) => (
                      <tr key={item.id}>
                        <td>{item.created_at}</td>
                        <td>{item.actor_email}</td>
                        <td>{item.action}</td>
                        <td>{item.target_email ?? item.target_id ?? item.target_type}</td>
                        <td>Journalisé</td>
                      </tr>
                    ))}
                  />
                </Card>

                <Card className="span2">
                  <p className="eyebrow">Zone sécurité</p>
                  <h2>Contrôle plateforme</h2>
                  <div className="securityGrid">
                    <span>Routes protégées par JWT Supabase</span>
                    <span>ADMIN_API_KEY côté serveur uniquement</span>
                    <span>Secret Stripe côté serveur uniquement</span>
                    <span>Aucune donnée de paiement fictive affichée</span>
                    <span>Utilisateur courant : {platformUser?.email ?? 'Données insuffisantes'}</span>
                  </div>
                </Card>
              </section>
            </>
          )}
        </section>
      </Layout>
    </ProtectedRoute>
  );
}
