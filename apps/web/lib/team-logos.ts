const FOOTBALL_DATA_CREST_BASE = 'https://crests.football-data.org';

const TEAM_CREST_IDS: Record<string, number> = {
  arsenal: 57,
  'arsenal fc': 57,
  barcelona: 81,
  barcelone: 81,
  'fc barcelona': 81,
  bayern: 5,
  'bayern munchen': 5,
  'bayern münchen': 5,
  'bayern munich': 5,
  'fc bayern munchen': 5,
  'fc bayern münchen': 5,
  'borussia dortmund': 4,
  dortmund: 4,
  'atletico madrid': 78,
  'atlético madrid': 78,
  'atletico de madrid': 78,
  'como 1907': 7397,
  'hellas verona': 450,
  'hellas verona fc': 450,
  inter: 108,
  'inter milan': 108,
  'fc internazionale milano': 108,
  juventus: 109,
  lens: 546,
  lille: 521,
  liverpool: 64,
  lyon: 523,
  'olympique lyonnais': 523,
  manchester: 65,
  'manchester city': 65,
  'manchester city fc': 65,
  marseille: 516,
  'olympique de marseille': 516,
  monaco: 548,
  'as monaco': 548,
  napoli: 113,
  nice: 522,
  psg: 524,
  'paris sg': 524,
  'paris saint-germain': 524,
  'paris saint germain': 524,
  real: 86,
  'real madrid': 86,
  'real madrid cf': 86,
  rennes: 529,
  roma: 100,
  udinese: 115,
  'udinese calcio': 115,
};

const BAD_LOGO_VALUES = new Set(['', 'null', 'undefined', 'n/a', 'na']);

export type TeamLogoSource = {
  name?: string | null;
  teamName?: string | null;
  team_name?: string | null;
  short_name?: string | null;
  tla?: string | null;
  logo_url?: string | null;
  logoUrl?: string | null;
  crest_url?: string | null;
  crestUrl?: string | null;
  crest?: string | null;
  logo?: string | null;
  emblem?: string | null;
  image?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' ? (value as Record<string, unknown>) : null;
}

function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function normalizeTeamName(value: string | null | undefined) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\b(fc|cf|sc|ac|as|rc|afc|club)\b/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function validLogoUrl(value: unknown): string | null {
  const candidate = stringValue(value);
  if (!candidate || BAD_LOGO_VALUES.has(candidate.toLowerCase())) return null;
  return candidate.startsWith('https://') ? candidate : null;
}

function logoFromKnownTeam(teamName: string | null | undefined): string | null {
  const normalized = normalizeTeamName(teamName);
  const directId = TEAM_CREST_IDS[normalized] ?? TEAM_CREST_IDS[String(teamName ?? '').trim().toLowerCase()];
  return directId ? `${FOOTBALL_DATA_CREST_BASE}/${directId}.svg` : null;
}

export function getTeamInitials(teamName: string): string {
  const initials = teamName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');

  return initials || 'FC';
}

export function resolveTeamLogo(teamOrName: unknown): string | null {
  if (typeof teamOrName === 'string') {
    return logoFromKnownTeam(teamOrName);
  }

  const team = asRecord(teamOrName);
  if (!team) return null;

  const explicit =
    validLogoUrl(team.logoUrl) ??
    validLogoUrl(team.logo_url) ??
    validLogoUrl(team.crestUrl) ??
    validLogoUrl(team.crest_url) ??
    validLogoUrl(team.crest) ??
    validLogoUrl(team.logo) ??
    validLogoUrl(team.emblem) ??
    validLogoUrl(team.image);

  if (explicit) return explicit;

  const name =
    stringValue(team.name) ??
    stringValue(team.teamName) ??
    stringValue(team.team_name) ??
    stringValue(team.short_name) ??
    stringValue(team.tla);

  return logoFromKnownTeam(name);
}

export function resolveTeamLogoUrl(teamName: string, source?: TeamLogoSource | string | null): string | null {
  if (source) {
    const explicit = resolveTeamLogo(source);
    if (explicit) return explicit;
  }

  return resolveTeamLogo(teamName);
}

export function resolveMatchTeamLogo(match: unknown, side: 'home' | 'away'): string | null {
  const row = asRecord(match);
  if (!row) return null;

  const nested = asRecord(row[side === 'home' ? 'homeTeam' : 'awayTeam']);
  const prefix = side === 'home' ? 'home' : 'away';

  const nestedLogo = nested ? resolveTeamLogo(nested) : null;
  if (nestedLogo) return nestedLogo;

  const directLogo =
    validLogoUrl(row[`${prefix}_team_logo`]) ??
    validLogoUrl(row[`${prefix}_crest`]) ??
    validLogoUrl(row[`${prefix}Logo`]);

  if (directLogo) return directLogo;

  const name =
    stringValue(row[`${prefix}_team`]) ??
    stringValue(row[`${prefix}_team_name`]) ??
    (nested ? stringValue(nested.name) ?? stringValue(nested.short_name) ?? stringValue(nested.tla) : null);

  return logoFromKnownTeam(name);
}
