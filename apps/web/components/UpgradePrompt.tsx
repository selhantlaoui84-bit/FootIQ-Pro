import Link from 'next/link';

type UpgradePromptProps = {
  feature: string;
  title?: string;
  description?: string;
  requiredPlan?: 'Premium' | 'Pro';
  ctaLabel?: string;
};

export function UpgradePrompt({
  feature,
  title = 'Fonctionnalité premium',
  description,
  requiredPlan = 'Premium',
  ctaLabel = 'Voir les plans',
}: UpgradePromptProps) {
  return (
    <section className="banner warning upgradePrompt" data-feature={feature}>
      <div>
        <strong>{title}</strong>
        <span>{description ?? `Passez ${requiredPlan} pour débloquer cette analyse.`}</span>
      </div>
      <Link className="button secondary" href="/pricing">
        {ctaLabel}
      </Link>
    </section>
  );
}
