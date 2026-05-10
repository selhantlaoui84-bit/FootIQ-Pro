const FOOTBALL_DATA_CREST_BASE = 'https://crests.football-data.org';

const TEAM_CREST_IDS: Record<string, number> = {
  arsenal: 57,
  'arsenal fc': 57,
  barcelona: 81,
  'fc barcelona': 81,
  'bayern munchen': 5,
  'bayern munich': 5,
  'fc bayern munchen': 5,
  'fc bayern münchen': 5,
  'borussia dortmund': 4,
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
  manchester: 65,
  'manchester city': 65,
  'manchester city fc': 65,
  marseille: 516,
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
  logo_url?: string | null;
  logoUrl?: string | null;
  crest_url?: string | null;
  crestUrl?: string | null;
  crest?: string | null;
  emblem?: string | null;
  image?: string | null;
};

export function normalizeTeamName(value: string | null | undefined) {
  return String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/\b(fc|cf|sc|ac|as|rc|afc|club)\b/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

export function getTeamInitials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');
}

export function resolveTeamLogoUrl(teamName: string, source?: TeamLogoSource | string | null) {
  const explicit =
    typeof source === 'string'
      ? source
      : source?.logo_url ?? source?.logoUrl ?? source?.crest_url ?? source?.crestUrl ?? source?.crest ?? source?.emblem ?? source?.image;

  if (typeof explicit === 'string') {
    const trimmed = explicit.trim();
    if (trimmed.startsWith('https://') && !BAD_LOGO_VALUES.has(trimmed.toLowerCase())) {
      return trimmed;
    }
  }

  const normalized = normalizeTeamName(teamName);
  const directId = TEAM_CREST_IDS[normalized] ?? TEAM_CREST_IDS[String(teamName ?? '').trim().toLowerCase()];
  return directId ? `${FOOTBALL_DATA_CREST_BASE}/${directId}.svg` : null;
}
