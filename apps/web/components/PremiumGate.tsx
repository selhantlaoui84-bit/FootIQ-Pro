import type { ReactNode } from 'react';
import { UpgradePrompt } from '~/components/UpgradePrompt';
import { canAccessFeature, type FeatureKey } from '~/lib/plans';

type PremiumGateProps = {
  plan?: string | null;
  feature: FeatureKey;
  children: ReactNode;
  title?: string;
  description?: string;
  requiredPlan?: 'Premium' | 'Pro';
};

export function PremiumGate({ plan, feature, children, title, description, requiredPlan }: PremiumGateProps) {
  if (canAccessFeature(plan, feature)) return <>{children}</>;
  return <UpgradePrompt feature={feature} title={title} description={description} requiredPlan={requiredPlan} />;
}
