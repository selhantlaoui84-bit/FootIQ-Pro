import { useState } from 'react';
import { getTeamInitials, resolveTeamLogo } from '~/lib/team-logos';

export type TeamLogoProps = {
  teamName: string;
  logoUrl?: string | null;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  fallbackInitials?: string;
  className?: string;
};

const SIZE_CLASS: Record<NonNullable<TeamLogoProps['size']>, string> = {
  xs: 'teamLogoXs',
  sm: 'teamLogoSm',
  md: 'teamLogoMd',
  lg: 'teamLogoLg',
  xl: 'teamLogoXl',
};

export function TeamLogo({
  teamName,
  logoUrl,
  size = 'md',
  fallbackInitials,
  className = '',
}: TeamLogoProps) {
  const [failed, setFailed] = useState(false);
  const resolvedLogo = failed ? null : resolveTeamLogo({ name: teamName, logoUrl });
  const fallback = fallbackInitials || getTeamInitials(teamName);

  return (
    <span className={`teamLogo ${SIZE_CLASS[size]} teamLogo-${size} ${className}`.trim()} aria-label={teamName}>
      {resolvedLogo ? (
        <img
          alt={teamName}
          className="teamLogoImage"
          decoding="async"
          loading={size === 'xl' ? 'eager' : 'lazy'}
          src={resolvedLogo}
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="teamLogoFallback" aria-hidden="true">
          {fallback}
        </span>
      )}
    </span>
  );
}
