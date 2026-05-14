import type { ReactNode } from 'react';
import { hasEntitlement } from '~/lib/entitlements';
import { UpgradeCard } from '~/components/UpgradeCard';

type EntitlementGateProps = {
  entitlements?: string[] | null;
  featureKey: string;
  children: ReactNode;
  fallbackTitle?: string;
  fallbackDescription?: string;
};

export function EntitlementGate({ entitlements, featureKey, children, fallbackTitle, fallbackDescription }: EntitlementGateProps) {
  if (hasEntitlement(entitlements, featureKey)) return <>{children}</>;
  return <UpgradeCard title={fallbackTitle} description={fallbackDescription} />;
}
