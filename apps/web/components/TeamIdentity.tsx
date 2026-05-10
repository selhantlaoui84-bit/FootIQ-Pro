import { TeamLogo } from './TeamLogo';

export type TeamIdentityProps = {
  teamName: string;
  logoUrl?: string | null;
  subtitle?: string;
  size?: 'sm' | 'md' | 'lg';
  align?: 'left' | 'center' | 'right';
  className?: string;
};

export function TeamIdentity({
  teamName,
  logoUrl,
  subtitle,
  size = 'md',
  align = 'left',
  className = '',
}: TeamIdentityProps) {
  return (
    <span className={`teamIdentity teamIdentity-${align} ${className}`.trim()}>
      <TeamLogo teamName={teamName} logoUrl={logoUrl} size={size} />
      <span className="teamIdentityText">
        <strong className="teamIdentityName">{teamName}</strong>
        {subtitle && <small className="teamIdentitySubtitle">{subtitle}</small>}
      </span>
    </span>
  );
}
