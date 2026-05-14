import Link from 'next/link';

type UpgradeCardProps = {
  title?: string;
  description?: string;
  ctaLabel?: string;
};

export function UpgradeCard({
  title = 'Accès premium requis',
  description = 'Passez sur un plan payant pour débloquer cette fonctionnalité.',
  ctaLabel = 'Voir les tarifs',
}: UpgradeCardProps) {
  return (
    <article className="card premiumPanel upgradeCard">
      <p className="eyebrow">Upgrade</p>
      <h3>{title}</h3>
      <p>{description}</p>
      <Link className="button primary" href="/pricing">
        {ctaLabel}
      </Link>
    </article>
  );
}
