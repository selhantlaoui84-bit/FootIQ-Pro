import type { ReactNode } from 'react';

type Tone = 'default' | 'success' | 'warning' | 'danger' | 'info' | 'premium';

export function PageHeader({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <section className="pageHeader premiumHeader">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h1>{title}</h1>
      {children}
    </section>
  );
}

export function Card({
  children,
  tone = 'default',
  className = '',
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return <article className={`card uiCard tone-${tone} ${className}`.trim()}>{children}</article>;
}

export function MetricCard({
  label,
  value,
  detail,
  tone = 'default',
}: {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: Tone;
}) {
  return (
    <article className={`metric metricCard tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </article>
  );
}

export function StatBadge({ children, tone = 'default' }: { children: ReactNode; tone?: Tone }) {
  return <span className={`statusBadge tone-${tone}`}>{children}</span>;
}

export function StatusBanner({ children, tone = 'info' }: { children: ReactNode; tone?: Tone }) {
  return <section className={`banner tone-${tone}`}>{children}</section>;
}

export function SectionGrid({ children, columns = 'three' }: { children: ReactNode; columns?: 'two' | 'three' | 'five' }) {
  return <section className={`grid ${columns}`}>{children}</section>;
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="emptyState">{children}</div>;
}

export function LoadingState({ label = 'Chargement...' }: { label?: string }) {
  return (
    <section className="protectedLoading">
      <div className="skeleton" />
      <p>{label}</p>
    </section>
  );
}

export function ErrorState({ children }: { children: ReactNode }) {
  return <section className="banner error">{children}</section>;
}
