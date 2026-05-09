import type { Match, Prediction, Recommendation } from '~/lib/mock-data';

export function normalizeFrenchText(value: string | null | undefined) {
  if (!value) return '';
  return value
    .replace(/\u00c3\u0083\u00c2\u00a9/g, 'é')
    .replace(/\u00c3\u0083\u00c2\u00a8/g, 'è')
    .replace(/\u00c3\u0083\u00c2\u00aa/g, 'ê')
    .replace(/\u00c3\u0083 /g, 'à')
    .replace(/\u00c3\u0083\u00e2\u0082\u00ac/g, 'À')
    .replace(/\u00c3\u0083\u00e2\u20ac\u00b0/g, 'É')
    .replace(/\u00c3\u0083\u00e2\u20ac\u00a1/g, 'Ç')
    .replace(/\u00c3\u0083\u00c2\u00ae/g, 'î')
    .replace(/\u00c3\u0083\u00c2\u00b4/g, 'ô')
    .replace(/\u00c3\u0083\u00c2\u00bb/g, 'û')
    .replace(/\u00c3\u0083\u00c2\u00a7/g, 'ç')
    .replace(/Pr\?d/g, 'Préd')
    .replace(/mod\?le/g, 'modèle')
    .replace(/donn\?es/g, 'données')
    .replace(/g\?n\?r/g, 'génér')
    .replace(/d\?saccord/g, 'désaccord')
    .replace(/\?\s?\?viter/g, 'À éviter')
    .replace(/A EVITER/g, 'À ÉVITER');
}

export function formatBooleanFr(value: boolean | null | undefined) {
  if (value === null || value === undefined) return 'Non renseigné';
  return value ? 'Oui' : 'Non';
}

export function formatStatusLabel(status: string | null | undefined) {
  const normalized = normalizeFrenchText(status).toUpperCase();
  if (normalized === 'A EVITER' || normalized === 'À ÉVITER') return 'À ÉVITER';
  if (normalized === 'FIABLE') return 'FIABLE';
  if (normalized === 'MOYEN') return 'MOYEN';
  return normalizeFrenchText(status) || 'Non renseigné';
}

export function formatRecommendationLabel(recommendation: Recommendation | string | null | undefined) {
  const normalized = normalizeFrenchText(recommendation);
  if (!normalized) return 'Non renseignée';
  if (normalized.toUpperCase() === 'A EVITER') return 'À éviter';
  return normalized;
}

export function formatModelStatusLabel(status: string | null | undefined) {
  const value = normalizeFrenchText(status);
  return (
    {
      ok: 'Prêt',
      not_trained: 'Non entraîné',
      insufficient_data: 'Données insuffisantes',
      blocked: 'Bloqué',
      error: 'Erreur',
      running: 'En cours',
      success: 'Terminé',
    }[value] ?? value ?? 'Non renseigné'
  );
}

export function formatCompetitionLabel(competition: string | null | undefined) {
  const value = normalizeFrenchText(competition);
  return (
    {
      CL: 'Ligue des champions',
      'Champions League': 'Ligue des champions',
      FL1: 'Ligue 1',
      PL: 'Premier League',
      PD: 'Liga',
      SA: 'Serie A',
      BL1: 'Bundesliga',
      DED: 'Eredivisie',
      PPL: 'Liga Portugal',
      WC: 'Coupe du monde',
    }[value] ?? value ?? 'Compétition'
  );
}

export function formatMatchStatusLabel(status: string | null | undefined) {
  const value = normalizeFrenchText(status).toUpperCase();
  return (
    {
      FINISHED: 'Terminé',
      TIMED: 'À venir',
      SCHEDULED: 'Programmé',
      POSTPONED: 'Reporté',
      LIVE: 'En direct',
      IN_PLAY: 'En cours',
      PAUSED: 'Pause',
    }[value] ?? normalizeFrenchText(status) ?? 'À venir'
  );
}

export function formatKickoffFr(date: string | null | undefined) {
  if (!date) return 'Date non disponible';
  const parsed = new Date(date);
  if (Number.isNaN(parsed.getTime())) return 'Date non disponible';
  return parsed.toLocaleString('fr-FR', { dateStyle: 'medium', timeStyle: 'short' });
}

export function formatScore(match: Pick<Match, 'score_full_time_home' | 'score_full_time_away'>) {
  const home = match.score_full_time_home;
  const away = match.score_full_time_away;
  if (home === null || home === undefined || away === null || away === undefined) return 'Score non disponible';
  return `${home} - ${away}`;
}

export function formatWinnerLabel(
  match: Pick<Match, 'home_team' | 'away_team' | 'winner' | 'score_full_time_home' | 'score_full_time_away'>,
) {
  if (match.winner === 'HOME_TEAM') return `Victoire ${match.home_team}`;
  if (match.winner === 'AWAY_TEAM') return `Victoire ${match.away_team}`;
  if (match.winner === 'DRAW') return 'Match nul';
  const home = match.score_full_time_home;
  const away = match.score_full_time_away;
  if (home === null || home === undefined || away === null || away === undefined) return 'Résultat non disponible';
  if (home > away) return `Victoire ${match.home_team}`;
  if (away > home) return `Victoire ${match.away_team}`;
  return 'Match nul';
}

export function formatFinishedMatchSummary(match: Match | Prediction) {
  const score = formatScore(match);
  const home = match.score_full_time_home ?? null;
  const away = match.score_full_time_away ?? null;
  const totalGoals = home !== null && away !== null ? home + away : null;
  return {
    score,
    halftime:
      match.score_half_time_home !== null &&
      match.score_half_time_home !== undefined &&
      match.score_half_time_away !== null &&
      match.score_half_time_away !== undefined
        ? `${match.score_half_time_home} - ${match.score_half_time_away}`
        : 'Non disponible',
    winner: formatWinnerLabel(match),
    result1n2: home === null || away === null ? 'Non disponible' : home > away ? '1' : away > home ? '2' : 'N',
    over25: totalGoals === null ? 'Non disponible' : totalGoals > 2 ? 'Oui' : 'Non',
    btts: home === null || away === null ? 'Non disponible' : home > 0 && away > 0 ? 'Oui' : 'Non',
    totalGoals,
  };
}
