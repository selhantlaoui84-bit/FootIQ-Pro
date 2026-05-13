export const PLAN_ENTITLEMENTS: Record<string, string[]> = {
  free: ['predictions.basic', 'matches.basic', 'dashboard.basic', 'limited_predictions_per_day'],
  pro: ['predictions.basic', 'matches.basic', 'dashboard.basic', 'predictions.advanced', 'odds.real', 'value_bets', 'bets.track', 'performance.basic', 'assistant.basic'],
  premium: [
    'predictions.basic',
    'matches.basic',
    'dashboard.basic',
    'predictions.advanced',
    'odds.real',
    'value_bets',
    'bets.track',
    'performance.basic',
    'assistant.basic',
    'assistant.advanced',
    'performance.advanced',
    'analysis.advanced',
    'alerts.intelligent',
    'bankroll.insights',
    'shadow_insights_read',
  ],
  enterprise: ['*'],
  admin: ['admin.access'],
  super_admin: ['*', 'super_admin.access'],
};

export function hasEntitlement(entitlements: string[] | null | undefined, featureKey: string) {
  if (!featureKey) return false;
  const active = entitlements ?? [];
  return active.includes('*') || active.includes(featureKey);
}

export function entitlementsForPlan(plan?: string | null) {
  return PLAN_ENTITLEMENTS[String(plan || 'free').toLowerCase()] ?? PLAN_ENTITLEMENTS.free;
}

export function requireEntitlement(entitlements: string[] | null | undefined, featureKey: string) {
  if (hasEntitlement(entitlements, featureKey)) return { allowed: true, featureKey };
  return { allowed: false, featureKey, upgrade_required: true };
}
