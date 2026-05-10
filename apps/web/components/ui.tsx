import type { CSSProperties, ReactNode } from 'react';
import { useState } from 'react';
import { getTeamInitials, resolveTeamLogoUrl, type TeamLogoSource } from '~/lib/team-assets';

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

export function ActionButton({
  children,
  href,
}: {
  children: ReactNode;
  href?: string;
}) {
  if (href) {
    return (
      <a className="premiumInlineButton" href={href}>
        {children}
      </a>
    );
  }

  return <span className="premiumInlineButton">{children}</span>;
}

export function TeamLogo({
  teamName,
  logoUrl,
  size = 'md',
  fallbackInitials,
  className = '',
}: {
  teamName: string;
  logoUrl?: string | null;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  fallbackInitials?: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const resolvedLogo = failed ? null : resolveTeamLogoUrl(teamName, logoUrl);
  const fallback = fallbackInitials || getTeamInitials(teamName);

  return (
    <span className={`teamLogo teamLogo-${size} ${className}`.trim()} aria-label={teamName}>
      {resolvedLogo ? (
        <img alt={teamName} loading={size === 'xl' ? 'eager' : 'lazy'} src={resolvedLogo} onError={() => setFailed(true)} />
      ) : (
        <span aria-hidden="true">{fallback}</span>
      )}
    </span>
  );
}

export function TeamIdentity({
  teamName,
  team,
  logoUrl,
  detail,
  tone = 'home',
  size = 'md',
}: {
  teamName: string;
  team?: TeamLogoSource | null;
  logoUrl?: string | null;
  detail?: ReactNode;
  tone?: 'home' | 'away';
  size?: 'sm' | 'md' | 'lg' | 'xl';
}) {
  return (
    <span className={`teamIdentity ${tone === 'away' ? 'away' : ''}`}>
      <TeamLogo teamName={teamName} logoUrl={logoUrl ?? resolveTeamLogoUrl(teamName, team)} size={size} />
      <span>
        <strong>{teamName}</strong>
        {detail && <small>{detail}</small>}
      </span>
    </span>
  );
}

export function TeamCrest({
  name,
  tone = 'home',
  logoUrl,
  size = 'md',
}: {
  name: string;
  tone?: 'home' | 'away';
  logoUrl?: string | null;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}) {
  return <TeamLogo teamName={name} logoUrl={logoUrl} size={size} className={`teamCrest ${tone === 'away' ? 'away' : ''}`} />;
}

export function TacticalPitch({
  home = 'Paris SG',
  away = 'Inter Milan',
  homeValue = 54,
  drawValue = 26,
  awayValue = 20,
  compact = false,
}: {
  home?: string;
  away?: string;
  homeValue?: number;
  drawValue?: number;
  awayValue?: number;
  compact?: boolean;
}) {
  const ringValue = `${Math.min(Math.max(drawValue, 0), 100) * 3.6}deg`;

  return (
    <div className={`tacticalPitch ${compact ? 'compact' : ''}`}>
      <div className="pitchTeam home">
        <TeamCrest name={home} />
        <strong>{home}</strong>
        <em>{homeValue}%</em>
        <span>Victoire</span>
      </div>
      <div className="pitchVisual" aria-label={`Probabilité du nul ${drawValue}%`}>
        <div className="pitchLines" />
        <div className="pitchZone zoneLeft" />
        <div className="pitchZone zoneRight" />
        <div className="probRing" style={{ '--ring-value': ringValue } as CSSProperties}>
          <strong>{drawValue}%</strong>
          <span>Nul</span>
        </div>
      </div>
      <div className="pitchTeam away">
        <TeamCrest name={away} tone="away" />
        <strong>{away}</strong>
        <em>{awayValue}%</em>
        <span>Victoire</span>
      </div>
    </div>
  );
}

export function MiniLineChart({ points = [18, 24, 21, 34, 31, 44, 40, 58, 65] }: { points?: number[] }) {
  const safePoints = points.length > 1 ? points : [20, 48, 34, 64];
  const max = Math.max(...safePoints, 1);
  const path = safePoints
    .map((point, index) => {
      const x = (index / (safePoints.length - 1)) * 100;
      const y = 100 - (point / max) * 82 - 8;
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');

  return (
    <svg className="miniLineChart" viewBox="0 0 100 100" role="img" aria-label="Courbe statistique">
      <path className="chartGridLine" d="M 0 78 H 100 M 0 52 H 100 M 0 26 H 100" />
      <path className="chartArea" d={`${path} L 100 100 L 0 100 Z`} />
      <path className="chartLine" d={path} pathLength={1} />
    </svg>
  );
}

export function TeamComparisonCurve({
  homeLabel = 'Domicile',
  awayLabel = 'Extérieur',
  homePoints = [54, 58, 62, 59, 66, 71, 68],
  awayPoints = [42, 40, 38, 44, 41, 36, 39],
}: {
  homeLabel?: string;
  awayLabel?: string;
  homePoints?: number[];
  awayPoints?: number[];
}) {
  return (
    <div className="teamComparisonCurve">
      <div className="curveLegend">
        <span><i className="homeLine" />{homeLabel}</span>
        <span><i className="awayLine" />{awayLabel}</span>
      </div>
      <DualLineChart homePoints={homePoints} awayPoints={awayPoints} />
    </div>
  );
}

function DualLineChart({ homePoints, awayPoints }: { homePoints: number[]; awayPoints: number[] }) {
  const safeHome = homePoints.length > 1 ? homePoints : [50, 52, 54];
  const safeAway = awayPoints.length > 1 ? awayPoints : [48, 46, 44];
  const max = Math.max(...safeHome, ...safeAway, 1);
  const min = Math.min(...safeHome, ...safeAway, 0);
  const range = Math.max(max - min, 1);
  const buildPath = (points: number[]) =>
    points
      .map((point, index) => {
        const x = (index / (points.length - 1)) * 100;
        const y = 88 - ((point - min) / range) * 76;
        return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
      })
      .join(' ');

  return (
    <svg className="dualLineChart" viewBox="0 0 100 100" role="img" aria-label="Comparaison des équipes">
      <path className="chartGridLine" d="M 0 82 H 100 M 0 58 H 100 M 0 34 H 100 M 0 10 H 100" />
      <path className="chartLine home" d={buildPath(safeHome)} pathLength={1} />
      <path className="chartLine away" d={buildPath(safeAway)} pathLength={1} />
    </svg>
  );
}

export function MiniBarChart({ values = [28, 44, 38, 62, 55, 76, 88] }: { values?: number[] }) {
  const max = Math.max(...values, 1);

  return (
    <div className="miniBarChart" aria-label="Histogramme statistique">
      {values.map((value, index) => (
        <span key={`${value}-${index}`} style={{ height: `${Math.max(12, (value / max) * 100)}%` }} />
      ))}
    </div>
  );
}

export function RadarChart({ labels = ['Attaque', 'Création', 'Défense', 'Solidité', 'Transition'] }: { labels?: string[] }) {
  return (
    <div className="radarWidget">
      <div className="radarChart" aria-hidden="true" />
      <div className="radarLabels">
        {labels.map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
    </div>
  );
}

export function ProbabilityRing({ value, label }: { value: number; label: string }) {
  const ringValue = `${Math.min(Math.max(value, 0), 100) * 3.6}deg`;

  return (
    <div className="probabilityRing" style={{ '--ring-value': ringValue } as CSSProperties}>
      <strong>{value}%</strong>
      <span>{label}</span>
    </div>
  );
}
