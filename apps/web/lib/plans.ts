import type { PlanName } from '~/lib/mock-data';

export const PLAN_FREE = 'free';
export const PLAN_PREMIUM = 'premium';
export const PLAN_PRO = 'pro';
export const PLAN_ADMIN = 'admin';

export type FeatureKey =
  | 'prediction_details'
  | 'value_bets'
  | 'assistant'
  | 'my_bets'
  | 'advanced_performance'
  | 'backtesting'
  | 'admin';

const planFeatures: Record<PlanName, FeatureKey[]> = {
  free: ['prediction_details', 'my_bets'],
  premium: ['prediction_details', 'value_bets', 'assistant', 'my_bets', 'advanced_performance'],
  pro: ['prediction_details', 'value_bets', 'assistant', 'my_bets', 'advanced_performance', 'backtesting'],
  admin: ['prediction_details', 'value_bets', 'assistant', 'my_bets', 'advanced_performance', 'backtesting', 'admin'],
};

export function normalizePlan(plan?: string | null): PlanName {
  return plan === PLAN_PREMIUM || plan === PLAN_PRO || plan === PLAN_ADMIN ? plan : PLAN_FREE;
}

export function getPlanFeatures(plan?: string | null) {
  return planFeatures[normalizePlan(plan)];
}

export function canAccessFeature(plan: string | null | undefined, feature: FeatureKey) {
  return getPlanFeatures(plan).includes(feature);
}

export function getUpgradeMessage(feature: FeatureKey) {
  const labels: Record<FeatureKey, string> = {
    prediction_details: 'Passez Premium pour débloquer les prédictions complètes.',
    value_bets: 'Passez Premium pour accéder aux value bets calculées avec cotes réelles.',
    assistant: "Passez Premium pour utiliser l'assistant FootIQ complet.",
    my_bets: 'Passez Premium pour suivre plus de paris et analyser votre discipline.',
    advanced_performance: 'Passez Pro pour débloquer les analyses avancées.',
    backtesting: 'Passez Pro pour consulter le backtesting détaillé.',
    admin: 'Accès administrateur requis.',
  };
  return labels[feature];
}
