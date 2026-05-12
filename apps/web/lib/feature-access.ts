import { canAccessFeature, normalizePlan, type FeatureKey } from '~/lib/plans';

const limits: Record<string, Record<string, number | null>> = {
  free: { prediction_view: 5, value_bet_view: 2, assistant_request: 3, bet_created: 10, performance_view: 3 },
  premium: { prediction_view: 200, value_bet_view: 100, assistant_request: 50, bet_created: 250, performance_view: 100 },
  pro: { prediction_view: 1000, value_bet_view: 500, assistant_request: 200, bet_created: 2000, performance_view: 500 },
  admin: { prediction_view: null, value_bet_view: null, assistant_request: null, bet_created: null, performance_view: null },
};

export function canViewPredictionDetails(plan?: string | null) {
  return canAccessFeature(plan, 'prediction_details');
}

export function canViewValueBets(plan?: string | null) {
  return canAccessFeature(plan, 'value_bets');
}

export function canUseAssistant(plan?: string | null) {
  return canAccessFeature(plan, 'assistant');
}

export function canUseMyBets(plan?: string | null) {
  return canAccessFeature(plan, 'my_bets');
}

export function canViewAdvancedPerformance(plan?: string | null) {
  return canAccessFeature(plan, 'advanced_performance');
}

export function getFeatureLimit(plan: string | null | undefined, feature: FeatureKey | string) {
  return limits[normalizePlan(plan)]?.[feature] ?? null;
}
