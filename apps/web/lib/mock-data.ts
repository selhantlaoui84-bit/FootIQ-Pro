export type ConfidenceStatus = 'FIABLE' | 'MOYEN' | 'A EVITER' | 'Ã€ Ã‰VITER';
export type Recommendation = 'Exploitable' | 'Prudence' | 'A eviter' | 'Ã€ Ã©viter';

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
  model_version?: string;
  calibration?: {
    applied: boolean;
    method: string;
    overconfidence_factor?: number;
    draw_adjustment?: number;
    confidence_penalty?: number;
  };
  probabilities: { home: number; draw: number; away: number };
  goals: {
    expected_home: number;
    expected_away: number;
    most_likely_score?: string;
    over_1_5?: number;
    over_2_5: number;
    over_3_5?: number;
    btts: number;
  };
  confidence: { score: number; status: ConfidenceStatus };
  features?: {
    elo_delta?: number;
    form_delta?: number;
    attack_delta?: number;
    defense_delta?: number;
    draw_risk_score?: number;
    data_quality_score?: number;
  };
  flags: { trap_match: boolean; risk: boolean };
  risk_score?: number;
  trap_match_score?: number;
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
  predictions_imported?: number;
  snapshots_saved?: number;
  feature_snapshots_saved?: number;
  training_rows_available?: number;
  last_refresh_at?: string | null;
  error?: string;
  detail?: string;
};



export type FeatureSummary = {
  snapshots_count: number;
  with_target_count: number;
  without_target_count: number;
  target_coverage: number;
  model_versions: Record<string, number>;
  feature_names: string[];
  storage?: string;
};

export type FeatureDatasetRow = {
  match_id: string;
  model_version: string;
  features: Record<string, number | string | boolean | null>;
  target?: Record<string, number | string | boolean | null> | null;
  created_at?: string | null;
};

export type FeatureImportanceRow = {
  feature: string;
  importance: number;
};

export type TrainingReport = {
  status: 'ok' | 'insufficient_data' | 'error' | 'not_trained' | string;
  model_type?: 'random_forest' | 'xgboost' | string;
  fallback_used?: boolean;
  model_version?: string;
  rows_used?: number;
  train_rows?: number;
  test_rows?: number;
  accuracy?: number;
  log_loss?: number | null;
  brier_score_1x2?: number | null;
  confusion_matrix?: Record<string, unknown>;
  feature_importance?: FeatureImportanceRow[];
  feature_columns?: string[];
  trained_at?: string;
  artifact_path?: string;
  metadata_path?: string;
  note?: string;
  detail?: string;
};

export type MlStatus = {
  status: string;
  latest_candidate: TrainingReport;
  feature_store: FeatureSummary;
  candidate_model_exists: boolean;
  production_model_version: string;
  candidate_is_production: boolean;
};

export type ModelsMetadata = {
  current_model_version: string;
  previous_model_version: string;
  family: string;
  calibration: boolean;
  description: string;
  available_model_versions?: string[];
};

export type ModelComparisonRow = {
  snapshots: number;
  evaluated_matches: number;
  result_accuracy: number;
  average_brier_score: number;
  average_confidence: number;
};

export type ModelComparison = {
  model_versions: Record<string, ModelComparisonRow>;
  best_model_by_brier: string | null;
  best_model_by_accuracy: string | null;
  note: string;
};

export type PredictionSnapshot = {
  id: string;
  match_id?: string;
  model_version?: string;
  prediction?: Prediction | null;
  created_at?: string | null;
  evaluated_at?: string | null;
  actual_result?: string | null;
  result_correct?: boolean | null;
  brier_score_1x2?: number | null;
};

export type ConfidenceBucket = {
  bucket: string;
  count: number;
  accuracy: number;
  average_brier_score: number;
};

export type CompetitionBacktest = {
  count: number;
  accuracy: number;
  average_brier_score: number;
};

export type BacktestingReport = {
  model_version: string;
  previous_model_version?: string;
  comparison_note?: string;
  calibration_applied?: boolean;
  evaluated_matches: number;
  result_accuracy: number;
  over_2_5_accuracy: number;
  btts_accuracy: number;
  average_brier_score: number;
  average_confidence: number;
  calibration_score: number;
  confidence_buckets: ConfidenceBucket[];
  competition_breakdown: Record<string, CompetitionBacktest>;
  last_backtest_at?: string;
  note: string;
};

export type PerformanceMetrics = {
  tracked: number;
  highConfidenceHitRate: string;
  averageConfidence: string;
  calibration: string;
  brierScore: string;
  modelVersion: string;
  model_version?: string;
  previous_model_version?: string;
  comparison_note?: string;
  calibration_applied?: boolean;
  current_model_version?: string;
  snapshots_count?: number;
  feature_snapshots_count?: number;
  training_rows_available?: number;
  target_coverage?: number;
  feature_store_ready?: boolean;
  ml_candidate?: TrainingReport;
  candidate_is_production?: boolean;
  model_versions?: Record<string, ModelComparisonRow>;
  best_model_by_brier?: string | null;
  best_model_by_accuracy?: string | null;
  model_comparison_note?: string;
  predictions_tracked?: number;
  evaluated_matches?: number;
  result_accuracy?: number;
  over_2_5_accuracy?: number;
  btts_accuracy?: number;
  average_brier_score?: number;
  calibration_score?: number;
  confidence_buckets?: ConfidenceBucket[];
  competition_breakdown?: Record<string, CompetitionBacktest>;
  average_confidence?: number;
  average_risk_score?: number;
  reliable_count?: number;
  medium_count?: number;
  avoid_count?: number;
  trap_match_count?: number;
  note?: string;
  lastUpdated: string;
  latest_refresh?: RefreshResponse | null;
};

export type HealthResponse = { status?: string; ok?: boolean };

export type DashboardSummary = {
  total_matches: number;
  teams_count: number;
  predictions_count: number;
  upcoming_matches_count: number;
  reliable_matches_count: number;
  medium_matches_count: number;
  avoid_matches_count: number;
  trap_matches_count: number;
  average_confidence: number;
  average_risk_score?: number;
  model_version?: string;
  calibration_applied?: boolean;
  current_model_version?: string;
  snapshots_count?: number;
  feature_snapshots_count?: number;
  training_rows_available?: number;
  target_coverage?: number;
  feature_store_ready?: boolean;
  ml_candidate_status?: string;
  ml_candidate_accuracy?: number | null;
  ml_candidate_model_version?: string;
  best_model_by_brier?: string | null;
  evaluated_matches?: number;
  result_accuracy?: number;
  average_brier_score?: number;
  calibration_score?: number;
  competitions_breakdown: Record<string, number>;
  top_reliable_matches: Prediction[];
  top_risky_matches: Prediction[];
  last_refresh_at: string | null;
  source: string;
  storage: string;
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
    model_version: 'elo-poisson-calibrated-v1',
    calibration: { applied: true, method: 'conservative_probability_smoothing', overconfidence_factor: 0.1, draw_adjustment: 2, confidence_penalty: 5 },
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
    model_version: 'elo-poisson-calibrated-v1',
    calibration: { applied: true, method: 'conservative_probability_smoothing', overconfidence_factor: 0.1, draw_adjustment: 2, confidence_penalty: 5 },
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
    model_version: 'elo-poisson-calibrated-v1',
    calibration: { applied: true, method: 'conservative_probability_smoothing', overconfidence_factor: 0.1, draw_adjustment: 2, confidence_penalty: 5 },
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
    model_version: 'elo-poisson-calibrated-v1',
    calibration: { applied: true, method: 'conservative_probability_smoothing', overconfidence_factor: 0.1, draw_adjustment: 2, confidence_penalty: 5 },
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
    model_version: 'elo-poisson-calibrated-v1',
    calibration: { applied: true, method: 'conservative_probability_smoothing', overconfidence_factor: 0.1, draw_adjustment: 2, confidence_penalty: 5 },
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


export const mockFeatureSummary: FeatureSummary = {
  snapshots_count: 0,
  with_target_count: 0,
  without_target_count: 0,
  target_coverage: 0,
  model_versions: {},
  feature_names: [
    'elo_delta',
    'form_delta',
    'attack_delta',
    'defense_delta',
    'draw_risk_score',
    'data_quality_score',
    'risk_score',
    'trap_match_score',
    'expected_home',
    'expected_away',
    'over_2_5_probability',
    'btts_probability',
    'home_probability',
    'draw_probability',
    'away_probability',
  ],
  storage: 'memory',
};

export const mockFeatureDataset: FeatureDatasetRow[] = [];

export const mockMlFeatureImportance: FeatureImportanceRow[] = [
  { feature: 'elo_delta', importance: 0.18 },
  { feature: 'home_probability', importance: 0.14 },
  { feature: 'away_probability', importance: 0.12 },
  { feature: 'data_quality_score', importance: 0.1 },
  { feature: 'draw_risk_score', importance: 0.08 },
];

export const mockTrainingReport: TrainingReport = {
  status: 'not_trained',
  model_type: 'random_forest',
  fallback_used: false,
  model_version: 'ml-candidate-v1',
  rows_used: 0,
  train_rows: 0,
  test_rows: 0,
  accuracy: 0,
  log_loss: null,
  brier_score_1x2: null,
  confusion_matrix: {},
  feature_importance: mockMlFeatureImportance,
  feature_columns: mockFeatureSummary.feature_names,
  note: 'Candidate model is not yet used for production predictions.',
};

export const mockMlStatus: MlStatus = {
  status: mockTrainingReport.status,
  latest_candidate: mockTrainingReport,
  feature_store: mockFeatureSummary,
  candidate_model_exists: false,
  production_model_version: 'elo-poisson-calibrated-v1',
  candidate_is_production: false,
};

export const mockModelsMetadata: ModelsMetadata = {
  current_model_version: 'elo-poisson-calibrated-v1',
  previous_model_version: 'elo-poisson-v1',
  family: 'elo_poisson',
  calibration: true,
  description: 'Calibrated Elo + Poisson model with conservative probability smoothing.',
  available_model_versions: ['elo-poisson-calibrated-v1', 'elo-poisson-v1'],
};

export const mockModelComparison: ModelComparison = {
  model_versions: {},
  best_model_by_brier: null,
  best_model_by_accuracy: null,
  note: 'Model comparison is based on stored prediction snapshots.',
};

export const mockPredictionSnapshots: PredictionSnapshot[] = [];

export const mockBacktestingReport: BacktestingReport = {
  model_version: 'elo-poisson-calibrated-v1',
  previous_model_version: 'elo-poisson-v1',
  comparison_note: 'Historical model comparison requires stored prediction snapshots.',
  calibration_applied: true,
  evaluated_matches: 0,
  result_accuracy: 0,
  over_2_5_accuracy: 0,
  btts_accuracy: 0,
  average_brier_score: 0,
  average_confidence: 0,
  calibration_score: 0,
  confidence_buckets: [
    { bucket: '0-49', count: 0, accuracy: 0, average_brier_score: 0 },
    { bucket: '50-59', count: 0, accuracy: 0, average_brier_score: 0 },
    { bucket: '60-69', count: 0, accuracy: 0, average_brier_score: 0 },
    { bucket: '70-79', count: 0, accuracy: 0, average_brier_score: 0 },
    { bucket: '80-89', count: 0, accuracy: 0, average_brier_score: 0 },
    { bucket: '90-100', count: 0, accuracy: 0, average_brier_score: 0 },
  ],
  competition_breakdown: {},
  last_backtest_at: '2026-05-02T08:00:00Z',
  note: 'Backtesting is computed on finished matches with available scores.',
};

export const performanceMetrics: PerformanceMetrics = {
  tracked: 1248,
  highConfidenceHitRate: '64%',
  averageConfidence: '68',
  calibration: 'Stable',
  brierScore: '0.184',
  modelVersion: 'FootIQ-Pro v0.5',
  model_version: mockBacktestingReport.model_version,
  previous_model_version: mockBacktestingReport.previous_model_version,
  comparison_note: mockBacktestingReport.comparison_note,
  calibration_applied: true,
  current_model_version: mockModelsMetadata.current_model_version,
  snapshots_count: 0,
  feature_snapshots_count: mockFeatureSummary.snapshots_count,
  training_rows_available: mockFeatureSummary.with_target_count,
  target_coverage: mockFeatureSummary.target_coverage,
  feature_store_ready: mockFeatureSummary.snapshots_count > 0,
  ml_candidate: mockTrainingReport,
  candidate_is_production: false,
  model_versions: mockModelComparison.model_versions,
  best_model_by_brier: mockModelComparison.best_model_by_brier,
  best_model_by_accuracy: mockModelComparison.best_model_by_accuracy,
  model_comparison_note: mockModelComparison.note,
  predictions_tracked: predictions.length,
  evaluated_matches: mockBacktestingReport.evaluated_matches,
  result_accuracy: mockBacktestingReport.result_accuracy,
  over_2_5_accuracy: mockBacktestingReport.over_2_5_accuracy,
  btts_accuracy: mockBacktestingReport.btts_accuracy,
  average_brier_score: mockBacktestingReport.average_brier_score,
  calibration_score: mockBacktestingReport.calibration_score,
  confidence_buckets: mockBacktestingReport.confidence_buckets,
  competition_breakdown: mockBacktestingReport.competition_breakdown,
  note: mockBacktestingReport.note,
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
    teams_count: teams.length,
    predictions_count: predictions.length,
    upcoming_matches_count: predictions.length,
    reliable_matches_count: reliable.length,
    medium_matches_count: medium.length,
    avoid_matches_count: avoid.length,
    trap_matches_count: traps.length,
    average_confidence: Math.round(
      predictions.reduce((sum, prediction) => sum + prediction.confidence.score, 0) / predictions.length,
    ),
    average_risk_score: Math.round(
      predictions.reduce((sum, prediction) => sum + (prediction.risk_score ?? 50), 0) / predictions.length,
    ),
    model_version: 'elo-poisson-calibrated-v1',
    calibration_applied: true,
    current_model_version: mockModelsMetadata.current_model_version,
    snapshots_count: 0,
    feature_snapshots_count: mockFeatureSummary.snapshots_count,
    training_rows_available: mockFeatureSummary.with_target_count,
    target_coverage: mockFeatureSummary.target_coverage,
    feature_store_ready: mockFeatureSummary.snapshots_count > 0,
    ml_candidate_status: mockMlStatus.status,
    ml_candidate_accuracy: mockTrainingReport.accuracy,
    ml_candidate_model_version: mockTrainingReport.model_version,
    best_model_by_brier: mockModelComparison.best_model_by_brier,
    evaluated_matches: mockBacktestingReport.evaluated_matches,
    result_accuracy: mockBacktestingReport.result_accuracy,
    average_brier_score: mockBacktestingReport.average_brier_score,
    calibration_score: mockBacktestingReport.calibration_score,
    competitions_breakdown: competitionsBreakdown,
    top_reliable_matches: [...predictions].sort((a, b) => b.confidence.score - a.confidence.score).slice(0, 5),
    top_risky_matches: predictions
      .filter((prediction) => prediction.flags.risk || prediction.flags.trap_match)
      .slice(0, 5),
    last_refresh_at: performanceMetrics.lastUpdated,
    source,
    storage: 'memory',
  };
}

export function isAvoidStatus(status: string) {
  return status === 'A EVITER' || status === 'Ã€ Ã‰VITER';
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





