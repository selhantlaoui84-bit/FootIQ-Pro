export type ConfidenceStatus = 'FIABLE' | 'MOYEN' | 'A EVITER' | 'À ÉVITER';
export type Recommendation = 'Exploitable' | 'Prudence' | 'A eviter' | 'À éviter';

export type Prediction = {
  id: string;
  match_id: string;
  slug: string;
  home_team: string;
  away_team: string;
  competition: string;
  kickoff: string;
  status?: string;
  source?: string;
  probabilities: { home: number; draw: number; away: number };
  goals: { expected_home: number; expected_away: number; over_2_5: number; btts: number };
  confidence: { score: number; status: ConfidenceStatus };
  flags: { trap_match: boolean; risk: boolean };
  recommendation: Recommendation;
  main_prediction: string;
  explanation: string[];
  risks: string[];
  disclaimer: string;
};

export type Match = {
  id: string;
  match_id: string;
  slug: string;
  home_team: string;
  away_team: string;
  competition: string;
  kickoff: string;
  status?: string;
  source?: string;
  probabilities?: Prediction['probabilities'];
  goals?: Prediction['goals'];
  confidence?: Prediction['confidence'];
  flags?: Prediction['flags'];
  recommendation?: Recommendation;
  main_prediction?: string;
  explanation?: string[];
  risks?: string[];
  disclaimer?: string;
};

export type Team = {
  id: string;
  slug: string;
  name: string;
  competition: string;
  elo?: number;
  form?: string;
  goals_for?: number;
  goals_against?: number;
  trend?: 'rising' | 'stable' | 'declining';
  source?: string;
};

export type RefreshResponse = {
  status: string;
  source?: string;
  storage?: string;
  matches_imported?: number;
  teams_imported?: number;
  last_refresh_at?: string | null;
  error?: string;
};

export type PerformanceMetrics = {
  tracked: number;
  highConfidenceHitRate: string;
  averageConfidence: string;
  calibration: string;
  brierScore: string;
  modelVersion: string;
  lastUpdated: string;
  latest_refresh?: RefreshResponse | null;
};

export type HealthResponse = { status?: string; ok?: boolean };

export type DashboardSummary = {
  total_matches: number;
  upcoming_matches_count: number;
  reliable_matches_count: number;
  medium_matches_count: number;
  avoid_matches_count: number;
  trap_matches_count: number;
  average_confidence: number;
  competitions_breakdown: Record<string, number>;
  top_reliable_matches: Prediction[];
  top_risky_matches: Prediction[];
  last_refresh_at: string | null;
  source: string;
};

export const predictions: Prediction[] = [
  {
    id: 'psg-lyon',
    match_id: 'psg-lyon',
    slug: 'psg-lyon',
    home_team: 'PSG',
    away_team: 'Lyon',
    competition: 'Ligue 1',
    kickoff: '2026-05-05T20:00:00Z',
    status: 'SCHEDULED',
    source: 'mock',
    probabilities: { home: 61, draw: 23, away: 16 },
    goals: { expected_home: 2.1, expected_away: 1.2, over_2_5: 58, btts: 54 },
    confidence: { score: 78, status: 'FIABLE' },
    flags: { trap_match: false, risk: false },
    recommendation: 'Exploitable',
    main_prediction: 'PSG ou nul avec avantage domicile',
    explanation: [
      'Superiorite offensive nette a domicile',
      "Lyon concede davantage d'occasions a l'exterieur",
      'Les signaux recents sont coherents',
    ],
    risks: ['Rotation possible', 'Fatigue europeenne moderee'],
    disclaimer: 'Modele probabiliste. Aucune garantie de resultat.',
  },
  {
    id: 'marseille-rennes',
    match_id: 'marseille-rennes',
    slug: 'marseille-rennes',
    home_team: 'Marseille',
    away_team: 'Rennes',
    competition: 'Ligue 1',
    kickoff: '2026-05-06T18:45:00Z',
    status: 'SCHEDULED',
    source: 'mock',
    probabilities: { home: 43, draw: 29, away: 28 },
    goals: { expected_home: 1.5, expected_away: 1.2, over_2_5: 46, btts: 57 },
    confidence: { score: 54, status: 'A EVITER' },
    flags: { trap_match: false, risk: true },
    recommendation: 'Prudence',
    main_prediction: 'Match serre, nul fortement plausible',
    explanation: [
      'Ecart de niveau faible sur les dernieres semaines',
      'Rennes reste dangereux en transition',
      'Probabilite de nul elevee, lisibilite reduite',
    ],
    risks: ['Forme recente irreguliere', 'Pression du contexte', 'High draw probability'],
    disclaimer: 'Modele probabiliste. Aucune garantie de resultat.',
  },
  {
    id: 'real-madrid-arsenal',
    match_id: 'real-madrid-arsenal',
    slug: 'real-madrid-arsenal',
    home_team: 'Real Madrid',
    away_team: 'Arsenal',
    competition: 'Champions League',
    kickoff: '2026-05-07T20:00:00Z',
    status: 'SCHEDULED',
    source: 'mock',
    probabilities: { home: 44, draw: 27, away: 29 },
    goals: { expected_home: 1.8, expected_away: 1.5, over_2_5: 61, btts: 62 },
    confidence: { score: 64, status: 'MOYEN' },
    flags: { trap_match: false, risk: false },
    recommendation: 'Prudence',
    main_prediction: 'Real Madrid avantage leger, match ouvert',
    explanation: [
      'Deux attaques capables de creer un volume eleve',
      'Arsenal conserve une forte capacite de pressing',
      'La marge entre les issues reste moderee',
    ],
    risks: ['Qualite individuelle adverse', 'Transitions rapides', 'BTTS eleve'],
    disclaimer: 'Modele probabiliste. Aucune garantie de resultat.',
  },
  {
    id: 'lille-monaco',
    match_id: 'lille-monaco',
    slug: 'lille-monaco',
    home_team: 'Lille',
    away_team: 'Monaco',
    competition: 'Ligue 1',
    kickoff: '2026-05-08T19:00:00Z',
    status: 'SCHEDULED',
    source: 'mock',
    probabilities: { home: 36, draw: 31, away: 33 },
    goals: { expected_home: 1.2, expected_away: 1.3, over_2_5: 44, btts: 55 },
    confidence: { score: 48, status: 'A EVITER' },
    flags: { trap_match: false, risk: true },
    recommendation: 'A eviter',
    main_prediction: 'Aucune direction claire',
    explanation: [
      'Probabilites tres proches entre les trois issues',
      'Deux blocs capables de neutraliser le rythme',
      'Donnees recentes contradictoires, confiance reduite',
    ],
    risks: ['Inconsistent recent form', 'High draw probability', "Faible volume d'occasions"],
    disclaimer: 'Modele probabiliste. Aucune garantie de resultat.',
  },
  {
    id: 'lens-nice',
    match_id: 'lens-nice',
    slug: 'lens-nice',
    home_team: 'Lens',
    away_team: 'Nice',
    competition: 'Ligue 1',
    kickoff: '2026-05-09T17:00:00Z',
    status: 'SCHEDULED',
    source: 'mock',
    probabilities: { home: 41, draw: 30, away: 29 },
    goals: { expected_home: 1.4, expected_away: 1.2, over_2_5: 43, btts: 52 },
    confidence: { score: 56, status: 'MOYEN' },
    flags: { trap_match: false, risk: false },
    recommendation: 'Prudence',
    main_prediction: 'Lens leger avantage domicile',
    explanation: [
      'Lens garde un petit avantage territorial a domicile',
      'Nice limite bien les occasions concedees',
      'Le nul reste un scenario significatif',
    ],
    risks: ['Efficacite offensive variable', 'High draw probability', 'Rythme potentiellement ferme'],
    disclaimer: 'Modele probabiliste. Aucune garantie de resultat.',
  },
];

export const matches: Match[] = predictions;

export const teams: Team[] = [
  {
    id: 'psg',
    slug: 'psg',
    name: 'PSG',
    competition: 'Ligue 1',
    elo: 1884,
    form: 'V V N V V',
    goals_for: 72,
    goals_against: 29,
    trend: 'rising',
    source: 'mock',
  },
  {
    id: 'marseille',
    slug: 'marseille',
    name: 'Marseille',
    competition: 'Ligue 1',
    elo: 1712,
    form: 'V N D V N',
    goals_for: 54,
    goals_against: 41,
    trend: 'stable',
    source: 'mock',
  },
  {
    id: 'lyon',
    slug: 'lyon',
    name: 'Lyon',
    competition: 'Ligue 1',
    elo: 1668,
    form: 'D V V N D',
    goals_for: 49,
    goals_against: 46,
    trend: 'stable',
    source: 'mock',
  },
  {
    id: 'monaco',
    slug: 'monaco',
    name: 'Monaco',
    competition: 'Ligue 1',
    elo: 1761,
    form: 'V V D V N',
    goals_for: 61,
    goals_against: 39,
    trend: 'rising',
    source: 'mock',
  },
  {
    id: 'lille',
    slug: 'lille',
    name: 'Lille',
    competition: 'Ligue 1',
    elo: 1739,
    form: 'N V V N D',
    goals_for: 52,
    goals_against: 34,
    trend: 'stable',
    source: 'mock',
  },
  {
    id: 'lens',
    slug: 'lens',
    name: 'Lens',
    competition: 'Ligue 1',
    elo: 1695,
    form: 'V D N V D',
    goals_for: 47,
    goals_against: 38,
    trend: 'declining',
    source: 'mock',
  },
  {
    id: 'rennes',
    slug: 'rennes',
    name: 'Rennes',
    competition: 'Ligue 1',
    elo: 1644,
    form: 'D N V D N',
    goals_for: 43,
    goals_against: 44,
    trend: 'declining',
    source: 'mock',
  },
  {
    id: 'nice',
    slug: 'nice',
    name: 'Nice',
    competition: 'Ligue 1',
    elo: 1688,
    form: 'N V N D V',
    goals_for: 39,
    goals_against: 31,
    trend: 'stable',
    source: 'mock',
  },
  {
    id: 'arsenal',
    slug: 'arsenal',
    name: 'Arsenal',
    competition: 'Champions League',
    elo: 1859,
    form: 'V V V N V',
    goals_for: 68,
    goals_against: 28,
    trend: 'rising',
    source: 'mock',
  },
  {
    id: 'real-madrid',
    slug: 'real-madrid',
    name: 'Real Madrid',
    competition: 'Champions League',
    elo: 1917,
    form: 'V N V V V',
    goals_for: 74,
    goals_against: 32,
    trend: 'rising',
    source: 'mock',
  },
];

export const performanceMetrics: PerformanceMetrics = {
  tracked: 1248,
  highConfidenceHitRate: '64%',
  averageConfidence: '68',
  calibration: 'Stable',
  brierScore: '0.184',
  modelVersion: 'FootIQ-Pro v0.5',
  lastUpdated: '2026-05-02T08:00:00Z',
  latest_refresh: null,
};

export function buildDashboardSummary(source = 'mock'): DashboardSummary {
  const reliable = predictions.filter((prediction) => prediction.confidence.status === 'FIABLE');
  const medium = predictions.filter((prediction) => prediction.confidence.status === 'MOYEN');
  const avoid = predictions.filter((prediction) => isAvoidStatus(prediction.confidence.status));
  const traps = predictions.filter((prediction) => prediction.flags.trap_match);
  const competitionsBreakdown = predictions.reduce<Record<string, number>>((acc, prediction) => {
    acc[prediction.competition] = (acc[prediction.competition] ?? 0) + 1;
    return acc;
  }, {});

  return {
    total_matches: predictions.length,
    upcoming_matches_count: predictions.length,
    reliable_matches_count: reliable.length,
    medium_matches_count: medium.length,
    avoid_matches_count: avoid.length,
    trap_matches_count: traps.length,
    average_confidence: Math.round(
      predictions.reduce((sum, prediction) => sum + prediction.confidence.score, 0) / predictions.length,
    ),
    competitions_breakdown: competitionsBreakdown,
    top_reliable_matches: [...predictions].sort((a, b) => b.confidence.score - a.confidence.score).slice(0, 5),
    top_risky_matches: predictions
      .filter((prediction) => prediction.flags.risk || prediction.flags.trap_match)
      .slice(0, 5),
    last_refresh_at: performanceMetrics.lastUpdated,
    source,
  };
}

export function isAvoidStatus(status: string) {
  return status === 'A EVITER' || status === 'À ÉVITER';
}

export function getMockPrediction(id: string) {
  return (
    predictions.find((prediction) => prediction.id === id || prediction.match_id === id || prediction.slug === id) ??
    predictions[0]
  );
}

export function getMockMatch(id: string) {
  return matches.find((match) => match.id === id || match.match_id === id || match.slug === id) ?? matches[0];
}

export function getMockTeam(id: string) {
  return teams.find((team) => team.id === id || team.slug === id) ?? teams[0];
}

export function matchHref(match: Pick<Match, 'match_id' | 'slug' | 'id'>) {
  return `/matches/${match.slug || match.match_id || match.id}`;
}

export function teamHref(team: Pick<Team, 'slug' | 'id'>) {
  return `/teams/${team.slug || team.id}`;
}

export function slugify(value: string) {
  return (
    value
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'unknown'
  );
}

export function teamNameHref(name: string) {
  return `/teams/${slugify(name)}`;
}

export function statusClass(status: string) {
  if (isAvoidStatus(status)) {
    return 'avoid';
  }

  return status.toLowerCase();
}
