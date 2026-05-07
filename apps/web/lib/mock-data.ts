export type ConfidenceStatus = 'FIABLE' | 'MOYEN' | 'À ÉVITER';
export type Recommendation = 'Exploitable' | 'Prudence' | 'À éviter' | 'À éviter';

export type ExplainabilityFactor = {
  feature: string;
  label: string;
  value: number | string | null;
  impact: 'positive' | 'negative' | 'neutral' | string;
  strength: number;
  message: string;
};

export type PredictionExplainability = {
  version: string;
  summary: string;
  official_signal: string;
  confidence_reading: string;
  top_positive_factors: ExplainabilityFactor[];
  top_negative_factors: ExplainabilityFactor[];
  neutral_factors: ExplainabilityFactor[];
  risk_notes: string[];
  data_quality_notes: string[];
  hybrid_notes: string[];
  plain_language: string;
  disclaimer: string;
};

export type ExplainabilitySummary = {
  version: string;
  processed_predictions: number;
  high_confidence_count: number;
  low_confidence_count: number;
  high_risk_count: number;
  trap_risk_count: number;
  most_common_positive_factors: Record<string, number>;
  most_common_negative_factors: Record<string, number>;
  note: string;
};

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
  score_full_time_home?: number | null;
  score_full_time_away?: number | null;
  score_half_time_home?: number | null;
  score_half_time_away?: number | null;
  winner?: string | null;
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
  shadow?: { prediction?: MlShadowPrediction | null; comparison?: MlShadowComparison | null };
  hybrid?: HybridDecision;
  hybrid_engine?: HybridEngineDecision;
  explainability?: PredictionExplainability;
};

export type MatchView = 'all' | 'upcoming' | 'history';

export type MlShadowPrediction = {
  match_id: string;
  model_version: string;
  candidate_is_production: boolean;
  available: boolean;
  status: string;
  predicted_result: 'home' | 'draw' | 'away' | null;
  probabilities: { home: number; draw: number; away: number } | null;
  confidence: number | null;
  source: string;
  note: string;
};

export type MlShadowComparison = {
  same_pick: boolean | null;
  production_pick: 'home' | 'draw' | 'away' | null;
  shadow_pick: 'home' | 'draw' | 'away' | null;
  confidence_delta: number | null;
  disagreement_level: 'none' | 'low' | 'medium' | 'high' | 'unknown' | string;
  note: string;
};

export type MlShadowRow = {
  id?: string;
  match_id: string;
  production_model_version?: string;
  candidate_model_version?: string;
  production_prediction?: Prediction;
  shadow_prediction: MlShadowPrediction;
  comparison: MlShadowComparison;
  created_at?: string;
};

export type MlShadowSummary = {
  shadow_predictions_count: number;
  available_count: number;
  unavailable_count: number;
  same_pick_count: number;
  disagreement_count: number;
  high_disagreement_count: number;
  candidate_model_version: string | null;
  candidate_is_production?: boolean;
  production_model_version?: string;
};

export type GenerateShadowPredictionsResponse = {
  status: string;
  job_id?: string | null;
  message?: string;
  next_check_endpoint?: string;
  storage?: string;
  view?: MatchView;
  shadow_predictions_generated?: number;
  shadow_predictions_saved?: number;
  available_count?: number;
  unavailable_count?: number;
  same_pick_count?: number;
  disagreement_count?: number;
  high_disagreement_count?: number;
  candidate_is_production?: boolean;
  created_at?: string;
  note?: string;
  detail?: string;
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
  score_full_time_home?: number | null;
  score_full_time_away?: number | null;
  score_half_time_home?: number | null;
  score_half_time_away?: number | null;
  winner?: string | null;
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
  predictions_generated?: number;
  predictions_saved?: number;
  predictions_failed?: number;
  predictions_save_errors_sample?: string[];
  snapshots_saved?: number;
  refresh_duration_ms?: number;
  next_recommended_actions?: string[];
  warning?: string;
  configured_competitions?: string[];
  competition_warnings?: string[];
  feature_snapshots_saved?: number;
  training_rows_available?: number;
  last_refresh_at?: string | null;
  job_id?: string;
  message?: string;
  next_check_endpoint?: string;
  error?: string;
  detail?: string;
  stable_refresh_status?: RefreshResponse;
  current_job?: RefreshJobStatus;
};

export type AdminDiagnosticsResponse = {
  hasApiUrl: boolean;
  apiUrlHost: string;
  hasAdminApiKey: boolean;
  hasCronSecret?: boolean;
  cronConfigured?: boolean;
  backendHealth: {
    status: 'ok' | 'error' | string;
    data?: unknown;
    error?: string;
  };
  refreshStatus: {
    status: 'ok' | 'error' | string;
    data?: RefreshResponse | unknown;
    error?: string;
  };
};



export type RefreshJobStatus = {
  job_id: string | null;
  status: 'idle' | 'running' | 'success' | 'error' | string;
  started_at: string | null;
  updated_at?: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  result: Record<string, unknown> | null;
  error: string | null;
};

export type FeatureSummary = {
  snapshots_count: number;
  with_target_count: number;
  without_target_count: number;
  target_coverage: number;
  model_versions: Record<string, number>;
  feature_names: string[];
  feature_set_version?: string | null;
  advanced_feature_coverage?: AdvancedFeatureCoverage;
  storage?: string;
};

export type AdvancedFeatureCoverage = {
  advanced_features_present: number;
  advanced_features_expected: number;
  coverage_percent: number;
};

export type FeatureDatasetRow = {
  match_id: string;
  model_version: string;
  features: Record<string, number | string | boolean | null>;
  target?: Record<string, number | string | boolean | null> | null;
  created_at?: string | null;
};

export type DatasetQualityRowIssue = {
  match_id: string;
  model_version: string | null;
  feature_count: number;
  has_target: boolean;
  target_fields: string[];
  leakage_features: string[];
  missing_core_features: string[];
  quality_score: number;
  status: 'ok' | 'warning' | 'blocked' | string;
  warnings: string[];
};

export type DatasetQualityReport = {
  status: 'ok' | 'empty' | 'blocked' | string;
  rows_checked: number;
  rows_with_target: number;
  rows_without_target: number;
  blocked_rows: number;
  warning_rows: number;
  ok_rows: number;
  average_quality_score: number;
  leakage_features_detected: string[];
  missing_core_features: Record<string, number>;
  target_field_coverage: Record<string, number>;
  safe_feature_names?: string[];
  blocked_feature_names?: string[];
  observed_feature_names?: string[];
  leakage_detection_mode?: string;
  feature_set_version?: string | null;
  feature_set_version_coverage?: Record<string, number>;
  advanced_feature_coverage?: AdvancedFeatureCoverage;
  safe_for_training: boolean;
  recommendation: 'safe_to_train' | 'review_warnings' | 'blocked_leakage_detected' | 'insufficient_data' | string;
  recommendation_reason: string;
  sample_checked_rows?: Array<{
    match_id: string;
    feature_names: string[];
    target_fields: string[];
    leakage_features: string[];
    status: string;
  }>;
  sample_issues: DatasetQualityRowIssue[];
};

export type FeatureImportanceRow = {
  feature: string;
  importance: number;
};

export type TrainingReport = {
  status: 'ok' | 'insufficient_data' | 'error' | 'not_trained' | 'blocked' | string;
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
  reason?: string;
  warning?: string;
  rows_loaded?: number;
  rows_with_target?: number;
  quality_recommendation?: string;
  quality_recommendation_reason?: string;
  minimum_required_rows?: number;
  dataset_quality?: DatasetQualityReport;
};

export type BuildFeatureStoreResponse = {
  status: string;
  job_id?: string;
  message?: string;
  next_check_endpoint?: string;
  storage?: string;
  predictions_source?: 'postgresql' | 'generated_on_the_fly' | string;
  matches_available?: number;
  predictions_available?: number;
  finished_matches_available?: number;
  finished_with_scores?: number;
  count_by_status?: Record<string, number>;
  feature_snapshots_built?: number;
  snapshots_created?: number;
  feature_snapshots_saved?: number;
  snapshots_saved?: number;
  feature_snapshots_skipped?: number;
  training_rows_available?: number;
  target_coverage?: number;
  feature_set_version?: string | null;
  advanced_feature_coverage?: AdvancedFeatureCoverage;
  model_version?: string;
  duration_ms?: number;
  created_at?: string;
  note?: string;
  detail?: string;
  reason_if_zero_snapshots?: string | null;
};

export type MlStatus = {
  status: string;
  latest_candidate: TrainingReport;
  feature_store: FeatureSummary;
  dataset_quality?: DatasetQualityReport;
  candidate_model_exists: boolean;
  production_model_version: string;
  candidate_is_production: boolean;
};

export type MlComparison = {
  production_model_version: string;
  candidate_model_version: string;
  candidate_is_production: boolean;
  production: {
    evaluated_matches: number;
    result_accuracy: number;
    average_brier_score: number;
    calibration_score: number;
  };
  candidate: {
    status: string;
    rows_used: number;
    accuracy: number | null;
    log_loss: number | null;
    brier_score_1x2: number | null;
    trained_at: string | null;
  };
  winner_by_accuracy: 'production' | 'candidate' | null;
  winner_by_brier: 'production' | 'candidate' | null;
  note: string;
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
  feature_set_version?: string | null;
  advanced_feature_coverage?: AdvancedFeatureCoverage;
  feature_columns_count?: number;
  ml_candidate?: TrainingReport;
  ml_comparison?: MlComparison;
  ml_shadow_summary?: MlShadowSummary;
  ml_shadow_backtesting?: MlShadowBacktesting;
  hybrid_summary?: HybridSummary;
  hybrid_engine_summary?: HybridEngineSummary;
  explainability_summary?: ExplainabilitySummary;
  dataset_quality?: DatasetQualityReport;
  candidate_is_production?: boolean;
  model_versions?: Record<string, ModelComparisonRow>;
  best_model_by_brier?: string | null;
  best_model_by_accuracy?: string | null;
  model_comparison_note?: string;
  model_governance?: ModelGovernanceReport;
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
  admin_alerts?: AdminAlertsReport | {
  overall_status: string;
  alerts_count: number;
  critical_count: number;
  warning_count: number;
};
};

export type HealthResponse = { status?: string; ok?: boolean };

export type DashboardSummary = {
  total_matches: number;
  teams_count: number;
  predictions_count: number;
  upcoming_matches_count: number;
  historical_matches_count?: number;
  reliable_matches_count: number;
  medium_matches_count: number;
  avoid_matches_count: number;
  trap_matches_count: number;
  average_confidence: number;
  average_risk_score?: number;
  admin_alerts_status?: string;
  admin_alerts_count?: number;
  admin_critical_alerts_count?: number;
  model_version?: string;
  calibration_applied?: boolean;
  current_model_version?: string;
  snapshots_count?: number;
  feature_snapshots_count?: number;
  training_rows_available?: number;
  target_coverage?: number;
  feature_store_ready?: boolean;
  feature_set_version?: string | null;
  advanced_feature_coverage?: AdvancedFeatureCoverage;
  model_governance_level?: string;
  model_governance_score?: number;
  model_governance_blockers_count?: number;
  model_promotion_ready?: boolean;
  ml_candidate_status?: string;
  ml_candidate_accuracy?: number | null;
  ml_candidate_model_version?: string;
  ml_shadow_summary?: MlShadowSummary;
  shadow_disagreement_count?: number;
  shadow_high_disagreement_count?: number;
  shadow_evaluated_matches?: number;
  shadow_accuracy?: number;
  shadow_activation_recommendation?: string;
  hybrid_recommendation?: string;
  hybrid_mode?: string;
  hybrid_candidate_is_production?: boolean;
  hybrid_engine_version?: string;
  hybrid_engine_recommendation?: string;
  hybrid_engine_strong_count?: number;
  hybrid_engine_avoid_count?: number;
  explainability_version?: string;
  high_risk_explanations_count?: number;
  trap_risk_explanations_count?: number;
  dataset_quality_safe_for_training?: boolean;
  dataset_quality_score?: number;
  dataset_quality_recommendation?: string;
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

export type HybridDecision = {
  mode: string;
  official_model_version: string;
  candidate_model_version: string | null;
  candidate_is_production: boolean;
  production_pick: 'home' | 'draw' | 'away' | null;
  shadow_pick: 'home' | 'draw' | 'away' | null;
  agreement: 'agree' | 'disagree' | 'unknown' | string;
  consensus_score: number;
  decision_label: 'signal_renforce' | 'prudence_shadow' | 'desaccord_modele' | 'shadow_indisponible' | string;
  risk_adjustment: number;
  display_message: string;
  explanation: string[];
};

export type HybridSummary = {
  mode: string;
  candidate_is_production: boolean;
  production_model_version: string;
  shadow_summary: MlShadowSummary;
  shadow_backtesting: MlShadowBacktesting;
  recommendation: 'keep_official' | 'use_hybrid_advisory' | 'insufficient_data' | string;
  reason: string;
};

export type HybridEngineDecision = {
  engine_version: string;
  mode: string;
  candidate_is_production: boolean;
  official_prediction_stays_primary: boolean;
  production_model_version: string;
  candidate_model_version: string | null;
  production_pick: 'home' | 'draw' | 'away' | null;
  shadow_pick: 'home' | 'draw' | 'away' | null;
  agreement: 'agree' | 'disagree' | 'unknown' | string;
  consensus_score: number;
  risk_adjustment: number;
  decision_level: 'strong' | 'medium' | 'weak' | 'avoid' | 'unknown' | string;
  decision_label: string;
  action: string;
  display_title: string;
  display_message: string;
  explanation: string[];
  warnings: string[];
  evidence: {
    production_confidence: number | null;
    shadow_confidence: number | null;
    confidence_delta: number | null;
    disagreement_level: string | null;
    shadow_backtesting_status: string | null;
    shadow_accuracy: number | null;
    production_accuracy: number | null;
    activation_recommendation: string | null;
  };
};

export type HybridEngineSummary = {
  engine_version: string;
  mode: string;
  candidate_is_production: boolean;
  official_prediction_stays_primary: boolean;
  production_model_version: string;
  limit?: number;
  view?: string;
  processed_predictions?: number;
  duration_ms?: number;
  shadow_evaluated_matches?: number;
  shadow_accuracy?: number;
  shadow_activation_recommendation?: string;
  shadow_backtesting?: MlShadowBacktesting;
  summary: {
    strong_count: number;
    medium_count: number;
    weak_count: number;
    avoid_count: number;
    unknown_count: number;
  };
  recommendation: 'keep_official' | 'hybrid_advisory_active' | 'insufficient_shadow_data' | string;
  reason: string;
};

export type AdminAlert = {
  id: string;
  level: 'critical' | 'warning' | 'info' | string;
  title: string;
  message: string;
  area: string;
  recommended_action: string;
  action_href: string;
  blocking: boolean;
  created_at: string;
};

export type AdminAlertsReport = {
  status: string;
  generated_at: string;
  overall_status: 'healthy' | 'warning' | 'critical' | string;
  alerts_count: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  alerts: AdminAlert[];
  next_best_action: {
    label: string;
    href: string;
    priority: string;
  };
  policy: {
    external_notifications_enabled: boolean;
    automatic_model_promotion: boolean;
    note: string;
  };
};

export const mockAdminAlertsReport: AdminAlertsReport = {
  status: 'ok',
  generated_at: '2026-05-03T13:00:00Z',
  overall_status: 'warning',
  alerts_count: 1,
  critical_count: 0,
  warning_count: 1,
  info_count: 0,
  alerts: [
    {
      id: 'feature_store_empty',
      level: 'warning',
      title: 'Feature Store à préparer',
      message: "Le jeu de variables n'est pas encore prêt.",
      area: 'feature_store',
      recommended_action: 'Construire le Feature Store.',
      action_href: '/admin',
      blocking: false,
      created_at: '2026-05-03T13:00:00Z',
    },
  ],
  next_best_action: {
    label: 'Construire le Feature Store.',
    href: '/admin',
    priority: 'warning',
  },
  policy: {
    external_notifications_enabled: false,
    automatic_model_promotion: false,
    note: "Les alertes sont affichées dans l'admin sans notification externe.",
  },
};

export type AdminWorkflowStatus = {
  refresh: {
    data_imported?: boolean;
    last_refresh_at: string | null;
    source?: string;
    storage: string;
    matches_imported: number;
    teams_imported?: number;
    predictions_imported: number;
    predictions_generated?: number;
    predictions_saved?: number;
    predictions_failed?: number;
  };
  feature_store: {
  ready: boolean;
  snapshots_count: number;
  training_rows_available: number;
  target_coverage: number;
  storage?: string;
};
  feature_engineering?: { feature_set_version?: string | null; advanced_feature_coverage: number };
  candidate_model: { trained: boolean; status: string; model_version: string | null; accuracy: number | null };
  shadow_predictions: { generated: boolean; count: number; disagreement_count: number };
  shadow_backtesting: { ready: boolean; evaluated_matches: number; shadow_accuracy: number; activation_recommendation: string };
  hybrid: { mode: string; recommendation: string };
  dataset_quality?: {
    safe_for_training: boolean;
    recommendation: string;
    average_quality_score: number;
    blocked_rows: number;
    warning_rows: number;
  };
  latest_refresh_job?: RefreshJobStatus;
  latest_feature_store_job?: RefreshJobStatus;
  cron?: {
    hourly_refresh_last_run?: { ran_at?: string; result?: unknown } | null;
    match_finished_check_last_run?: { ran_at?: string; result?: unknown } | null;
  };
  next_step: 'refresh_data' | 'build_feature_store' | 'train_candidate_model' | 'generate_shadow_predictions' | 'review_shadow_backtesting' | 'ready_for_hybrid_review' | string;
  admin_alerts?: {
  overall_status: string;
  alerts_count: number;
  critical_count: number;
  warning_count: number;
  next_best_action?: {
    label: string;
    href: string;
    priority: string;
  };
};
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
    disclaimer: 'Modèle probabiliste. Aucune garantie de résultat.',
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
    confidence: { score: 54, status: 'À ÉVITER' },
    flags: { trap_match: false, risk: true },
    recommendation: 'Prudence',
    main_prediction: 'Match serré, nul fortement plausible',
    explanation: [
      'Ecart de niveau faible sur les dèrnieres semaines',
      'Rennes reste dangereux en transition',
      'Probabilite de nul élevée, lisibilite réduite',
    ],
    risks: ['Forme recente irreguliere', 'Pression du contexte', 'High draw probability'],
    disclaimer: 'Modèle probabiliste. Aucune garantie de résultat.',
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
    main_prediction: 'Real Madrid avantage léger, match ouvert',
    explanation: [
      'Deux attaques capables de creer un volume eleve',
      'Arsenal conserve une forte capacite de pressing',
      'La marge entre les issues reste moderee',
    ],
    risks: ['Qualite individuelle adverse', 'Transitions rapides', 'BTTS eleve'],
    disclaimer: 'Modèle probabiliste. Aucune garantie de résultat.',
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
    confidence: { score: 48, status: 'À ÉVITER' },
    flags: { trap_match: false, risk: true },
    recommendation: 'À éviter',
    main_prediction: 'Aucune direction claire',
    explanation: [
      'Probabilites tres proches entre les trois issues',
      'Deux blocs capables de neutraliser le rythme',
      'Donnees recentes contradictoires, confiance reduite',
    ],
    risks: ['Inconsistent recent form', 'High draw probability', "Faible volume d'occasions"],
    disclaimer: 'Modèle probabiliste. Aucune garantie de résultat.',
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
    main_prediction: 'Lens léger avantage domicile',
    explanation: [
      'Lens garde un petit avantage territorial a domicile',
      'Nice limite bien les occasions concedees',
      'Le nul reste un scenario significatif',
    ],
    risks: ['Efficacite offensive variable', 'High draw probability', 'Rythme potentiellement ferme'],
    disclaimer: 'Modele probabiliste. Aucune garantie de resultat.',
  },
];

export const matches: Match[] = [
  ...predictions,
  {
    id: 'psg-marseille-historique',
    match_id: 'psg-marseille-historique',
    slug: 'psg-marseille-historique',
    home_team: 'PSG',
    away_team: 'Marseille',
    competition: 'Ligue 1',
    kickoff: '2026-04-18T19:00:00Z',
    status: 'FINISHED',
    source: 'mock',
    score_full_time_home: 2,
    score_full_time_away: 1,
    score_half_time_home: 1,
    score_half_time_away: 0,
    winner: 'HOME_TEAM',
  },
];

export const mockPredictionExplainability: PredictionExplainability = {
  version: 'explainability-v1',
  summary: 'Le modèle officiel oriente la lecture vers domicile avec une probabilité principale de 61%.',
  official_signal: 'Signal officiel: domicile, porté par plusieurs facteurs favorables et quelques points de prudence.',
  confidence_reading: 'Signal lisible: plusieurs indicateurs convergent, sans certitude de résultat.',
  top_positive_factors: [
    {
      feature: 'elo_delta',
      label: 'Écart Elo',
      value: 42,
      impact: 'positive',
      strength: 70,
      message: 'Ce signal penche vers le domicile et soutient le choix domicile.',
    },
    {
      feature: 'data_quality_score',
      label: 'Qualité des données',
      value: 82,
      impact: 'positive',
      strength: 82,
      message: 'La qualité des données renforce la lisibilité statistique.',
    },
  ],
  top_negative_factors: [
    {
      feature: 'draw_risk_score',
      label: 'Risque de match nul',
      value: 58,
      impact: 'negative',
      strength: 58,
      message: 'Le risque de nul reste un point de prudence.',
    },
  ],
  neutral_factors: [],
  risk_notes: ['Le niveau de risque reste surveillé, mais ne domine pas la lecture.'],
  data_quality_notes: ['La qualité des données est suffisante pour une lecture probabiliste.'],
  hybrid_notes: ['Le ML shadow peut compléter la lecture sans remplacer le modèle officiel.'],
  plain_language: 'Cette explication traduit les signaux statistiques disponibles avant le match. Elle aide à comprendre la prédiction, sans prouver la cause du résultat futur.',
  disclaimer: 'Modèle probabiliste. Aucune garantie de résultat.',
};

export const mockExplainabilitySummary: ExplainabilitySummary = {
  version: 'explainability-v1',
  processed_predictions: predictions.length,
  high_confidence_count: predictions.filter((prediction) => prediction.confidence.score >= 75).length,
  low_confidence_count: predictions.filter((prediction) => prediction.confidence.score < 55).length,
  high_risk_count: predictions.filter((prediction) => (prediction.risk_score ?? 0) >= 65 || prediction.flags.risk).length,
  trap_risk_count: predictions.filter((prediction) => prediction.flags.trap_match).length,
  most_common_positive_factors: { 'Écart Elo': 2, 'Qualité des données': 2 },
  most_common_negative_factors: { 'Risque de match nul': 2, 'Score de risque': 1 },
  note: "L'explicabilité décrit les signaux du modèle sans garantir le résultat.",
};

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


export const mockAdvancedFeatureNames = [
  'home_recent_points_per_match',
  'away_recent_points_per_match',
  'form_points_delta',
  'home_recent_goals_for_avg',
  'away_recent_goals_for_avg',
  'attack_recent_delta',
  'home_recent_goals_against_avg',
  'away_recent_goals_against_avg',
  'defense_recent_delta',
  'home_recent_win_rate',
  'away_recent_win_rate',
  'win_rate_delta',
  'home_recent_unbeaten_rate',
  'away_recent_unbeaten_rate',
  'unbeaten_rate_delta',
  'home_recent_matches_count',
  'away_recent_matches_count',
  'home_recent_home_points_avg',
  'home_recent_home_goals_for_avg',
  'home_recent_home_goals_against_avg',
  'away_recent_away_points_avg',
  'away_recent_away_goals_for_avg',
  'away_recent_away_goals_against_avg',
  'home_rest_days',
  'away_rest_days',
  'rest_days_delta',
  'home_matches_last_7d',
  'home_matches_last_14d',
  'home_matches_last_21d',
  'away_matches_last_7d',
  'away_matches_last_14d',
  'away_matches_last_21d',
  'schedule_density_delta_14d',
  'home_win_streak',
  'home_unbeaten_streak',
  'home_loss_streak',
  'away_win_streak',
  'away_unbeaten_streak',
  'away_loss_streak',
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
    ...mockAdvancedFeatureNames,
  ],
  feature_set_version: 'pre-match-advanced-v1',
  advanced_feature_coverage: {
    advanced_features_present: mockAdvancedFeatureNames.length,
    advanced_features_expected: mockAdvancedFeatureNames.length,
    coverage_percent: 100,
  },
  storage: 'memory',
};

export const mockFeatureDataset: FeatureDatasetRow[] = [];

export const mockFeatureQualityReport: DatasetQualityReport = {
  status: 'empty',
  rows_checked: 0,
  rows_with_target: 0,
  rows_without_target: 0,
  blocked_rows: 0,
  warning_rows: 0,
  ok_rows: 0,
  average_quality_score: 0,
  leakage_features_detected: [],
  missing_core_features: {},
  target_field_coverage: {
    result: 0,
    home_goals: 0,
    away_goals: 0,
    over_2_5: 0,
    btts: 0,
  },
  safe_feature_names: mockFeatureSummary.feature_names,
  blocked_feature_names: [
    'score_full_time_home',
    'score_full_time_away',
    'score_half_time_home',
    'score_half_time_away',
    'winner',
    'actual_result',
    'result',
    'target_result',
    'home_goals',
    'away_goals',
    'final_score',
    'full_time_result',
  ],
  observed_feature_names: [],
  leakage_detection_mode: 'strict_feature_only',
  feature_set_version: 'pre-match-advanced-v1',
  feature_set_version_coverage: {},
  advanced_feature_coverage: mockFeatureSummary.advanced_feature_coverage,
  safe_for_training: false,
  recommendation: 'insufficient_data',
  recommendation_reason: 'Aucune ligne supervisee disponible pour le controle qualite.',
  sample_checked_rows: [],
  sample_issues: [],
};

export const mockBuildFeatureStoreResponse: BuildFeatureStoreResponse = {
  status: 'not_run',
  storage: 'memory',
  feature_snapshots_built: 0,
  feature_snapshots_saved: 0,
  feature_snapshots_skipped: 0,
  training_rows_available: 0,
  target_coverage: 0,
  feature_set_version: mockFeatureSummary.feature_set_version,
  advanced_feature_coverage: mockFeatureSummary.advanced_feature_coverage,
  model_version: 'elo-poisson-calibrated-v1',
  note: 'Construisez le Feature Store après avoir actualisé les données.',
};

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
  note: "Le modèle candidat n'est pas encore utilisé pour les prédictions de production.",
};

export const mockMlStatus: MlStatus = {
  status: mockTrainingReport.status,
  latest_candidate: mockTrainingReport,
  feature_store: mockFeatureSummary,
  dataset_quality: mockFeatureQualityReport,
  candidate_model_exists: false,
  production_model_version: 'elo-poisson-calibrated-v1',
  candidate_is_production: false,
};


export const mockMlShadowSummary: MlShadowSummary = {
  shadow_predictions_count: 0,
  available_count: 0,
  unavailable_count: 0,
  same_pick_count: 0,
  disagreement_count: 0,
  high_disagreement_count: 0,
  candidate_model_version: 'ml-candidate-v1',
  candidate_is_production: false,
  production_model_version: 'elo-poisson-calibrated-v1',
};

export const mockMlShadowPredictions: MlShadowRow[] = [];

export const mockGenerateShadowPredictionsResponse: GenerateShadowPredictionsResponse = {
  status: 'not_run',
  storage: 'memory',
  view: 'upcoming',
  shadow_predictions_generated: 0,
  shadow_predictions_saved: 0,
  available_count: 0,
  unavailable_count: 0,
  same_pick_count: 0,
  disagreement_count: 0,
  high_disagreement_count: 0,
  candidate_is_production: false,
  note: "Les prédictions ML shadow seront calculées en parallèle du modèle officiel.",
};

export const mockMlComparison: MlComparison = {
  production_model_version: 'elo-poisson-calibrated-v1',
  candidate_model_version: 'ml-candidate-v1',
  candidate_is_production: false,
  production: {
    evaluated_matches: 0,
    result_accuracy: 0,
    average_brier_score: 0,
    calibration_score: 0,
  },
  candidate: {
    status: mockTrainingReport.status,
    rows_used: mockTrainingReport.rows_used ?? 0,
    accuracy: mockTrainingReport.accuracy ?? null,
    log_loss: mockTrainingReport.log_loss ?? null,
    brier_score_1x2: mockTrainingReport.brier_score_1x2 ?? null,
    trained_at: mockTrainingReport.trained_at ?? null,
  },
  winner_by_accuracy: null,
  winner_by_brier: null,
  note: "Le modèle ML candidat est évalué mais n'est pas encore utilisé en production.",
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
  note: 'La comparaison des modèles repose sur les snapshots de prédiction stockés.',
};

export const mockPredictionSnapshots: PredictionSnapshot[] = [];

export const mockBacktestingReport: BacktestingReport = {
  model_version: 'elo-poisson-calibrated-v1',
  previous_model_version: 'elo-poisson-v1',
  comparison_note: 'La comparaison historique nécessite des snapshots de prédiction stockés.',
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
  note: 'Le backtesting est calculé sur les matchs terminés avec scores disponibles.',
};

export type GovernanceGate = {
  passed: boolean;
  reason: string;
  recommendation?: string;
  status?: string;
  evaluated_matches?: number;
  shadow_accuracy?: number;
  production_accuracy?: number;
};

export type ModelGovernanceReport = {
  status: string;
  generated_at: string;
  production_model: {
    version: string;
    family: string;
    status: string;
    locked: boolean;
    description: string;
  };
  candidate_model: {
    version: string | null;
    family: string | null;
    status: string;
    candidate_is_production: boolean;
    rows_used: number;
    accuracy: number | null;
    brier_score_1x2: number | null;
    trained_at: string | null;
  };
  governance_gates: Record<string, GovernanceGate>;
  promotion_readiness: {
    ready: boolean;
    level: string;
    score: number;
    blocking_reasons: string[];
    warnings: string[];
    next_actions: string[];
  };
  version_history: {
    version: string;
    family: string;
    status: string;
    notes: string;
  }[];
  policy: {
    automatic_promotion: boolean;
    requires_manual_review: boolean;
    production_model_locked: boolean;
    note: string;
  };
};

export const mockModelGovernance: ModelGovernanceReport = {
  status: 'ok',
  generated_at: '2026-05-03T13:00:00Z',
  production_model: {
    version: 'elo-poisson-calibrated-v1',
    family: 'elo_poisson',
    status: 'production',
    locked: true,
    description: 'Modèle officiel Elo/Poisson calibré.',
  },
  candidate_model: {
    version: 'ml-candidate-v1',
    family: 'random_forest',
    status: 'not_trained',
    candidate_is_production: false,
    rows_used: 0,
    accuracy: null,
    brier_score_1x2: null,
    trained_at: null,
  },
  governance_gates: {
    dataset_quality: { passed: false, reason: 'Dataset non vérifié.' },
    training: { passed: false, reason: 'Modèle candidat non entraîné.' },
    shadow_backtesting: { passed: false, reason: 'Shadow backtesting insuffisant.' },
    monitoring: { passed: true, reason: 'Monitoring disponible.' },
    hybrid_review: { passed: false, reason: 'Revue hybride insuffisante.' },
  },
  promotion_readiness: {
    ready: false,
    level: 'not_ready',
    score: 0,
    blocking_reasons: ['Modèle candidat non entraîné.'],
    warnings: [],
    next_actions: ['Valider le dataset puis entraîner le modèle candidat.'],
  },
  version_history: [
    { version: 'elo-poisson-v1', family: 'elo_poisson', status: 'previous', notes: 'Modèle initial.' },
    { version: 'elo-poisson-calibrated-v1', family: 'elo_poisson', status: 'production', notes: 'Modèle officiel.' },
    { version: 'ml-candidate-v1', family: 'random_forest', status: 'not_trained', notes: 'Candidat ML.' },
  ],
  policy: {
    automatic_promotion: false,
    requires_manual_review: true,
    production_model_locked: true,
    note: 'Le modèle ML ne peut pas remplacer automatiquement le modèle officiel.',
  },
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
  feature_set_version: mockFeatureSummary.feature_set_version,
  advanced_feature_coverage: mockFeatureSummary.advanced_feature_coverage,
  feature_columns_count: mockFeatureSummary.feature_names.length,
  feature_store_ready: mockFeatureSummary.snapshots_count > 0,
  ml_candidate: mockTrainingReport,
  ml_comparison: mockMlComparison,
  ml_shadow_summary: mockMlShadowSummary,
  explainability_summary: mockExplainabilitySummary,
  candidate_is_production: false,
  dataset_quality: mockFeatureQualityReport,
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
  model_governance: mockModelGovernance,
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
    upcoming_matches_count: matches.filter((match) => match.status !== 'FINISHED').length,
    historical_matches_count: matches.filter((match) => match.status === 'FINISHED').length,
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
    feature_set_version: mockFeatureSummary.feature_set_version,
    advanced_feature_coverage: mockFeatureSummary.advanced_feature_coverage,
    feature_store_ready: mockFeatureSummary.snapshots_count > 0,
    ml_candidate_status: mockMlStatus.status,
    ml_candidate_accuracy: mockTrainingReport.accuracy,
    ml_candidate_model_version: mockTrainingReport.model_version,
    ml_shadow_summary: mockMlShadowSummary,
    shadow_disagreement_count: mockMlShadowSummary.disagreement_count,
    shadow_high_disagreement_count: mockMlShadowSummary.high_disagreement_count,
    explainability_version: mockExplainabilitySummary.version,
    high_risk_explanations_count: mockExplainabilitySummary.high_risk_count,
    trap_risk_explanations_count: mockExplainabilitySummary.trap_risk_count,
    dataset_quality_safe_for_training: mockFeatureQualityReport.safe_for_training,
    dataset_quality_score: mockFeatureQualityReport.average_quality_score,
    dataset_quality_recommendation: mockFeatureQualityReport.recommendation,
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
    model_governance_level: mockModelGovernance.promotion_readiness.level,
    model_governance_score: mockModelGovernance.promotion_readiness.score,
    model_governance_blockers_count: mockModelGovernance.promotion_readiness.blocking_reasons.length,
    model_promotion_ready: false,
    admin_alerts_status: mockAdminAlertsReport.overall_status,
    admin_alerts_count: mockAdminAlertsReport.alerts_count,
    admin_critical_alerts_count: mockAdminAlertsReport.critical_count,
  };
}

export function isAvoidStatus(status: string) {
  return status === 'À ÉVITER';
}

export function getMockPrediction(id: string) {
  const prediction = (
    predictions.find((prediction) => prediction.id === id || prediction.match_id === id || prediction.slug === id) ??
    predictions[0]
  );
  return { ...prediction, explainability: prediction.explainability ?? mockPredictionExplainability };
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

export type MlShadowBacktestingEvaluation = {
  match_id: string;
  actual_result: 'home' | 'draw' | 'away' | string;
  production_pick: 'home' | 'draw' | 'away' | null;
  shadow_pick: 'home' | 'draw' | 'away' | null;
  production_correct: boolean | null;
  shadow_correct: boolean | null;
  same_pick: boolean | null;
  winner: 'production' | 'shadow' | 'both' | 'none' | 'unknown' | string;
  disagreement_level: 'none' | 'low' | 'medium' | 'high' | 'unknown' | string;
  production_brier_score: number | null;
  shadow_brier_score: number | null;
  competition?: string;
  home_team?: string;
  away_team?: string;
  kickoff?: string;
};

export type MlShadowBacktesting = {
  status: 'ok' | 'empty' | string;
  evaluated_matches: number;
  production_accuracy: number;
  shadow_accuracy: number;
  production_average_brier: number | null;
  shadow_average_brier: number | null;
  same_pick_count: number;
  disagreement_count: number;
  high_disagreement_count: number;
  shadow_wins_on_disagreement: number;
  production_wins_on_disagreement: number;
  both_wrong_on_disagreement: number;
  activation_score: number;
  activation_recommendation:
    | 'do_not_activate'
    | 'keep_shadow'
    | 'consider_hybrid'
    | 'candidate_ready_for_limited_rollout'
    | string;
  recommendation_reason: string;
  competition_breakdown: Record<string, unknown>;
  recent_evaluations: MlShadowBacktestingEvaluation[];
  candidate_is_production: boolean;
  note: string;
};

export const mockMlShadowBacktesting = {
  status: 'empty',
  evaluated_matches: 0,
  production_accuracy: 0,
  shadow_accuracy: 0,
  production_average_brier: null,
  shadow_average_brier: null,
  same_pick_count: 0,
  disagreement_count: 0,
  high_disagreement_count: 0,
  shadow_wins_on_disagreement: 0,
  production_wins_on_disagreement: 0,
  both_wrong_on_disagreement: 0,
  activation_score: 0,
  activation_recommendation: 'do_not_activate',
  recommendation_reason: "Aucune prédiction shadow évaluable pour le moment.",
  competition_breakdown: {},
  recent_evaluations: [],
  candidate_is_production: false,
  note: "Le backtesting shadow mesure le modèle ML candidat sans l'activer en production.",
};










export const mockHybridDecision: HybridDecision = {
  mode: 'official_with_shadow_advisory',
  official_model_version: 'elo-poisson-calibrated-v1',
  candidate_model_version: null,
  candidate_is_production: false,
  production_pick: 'home',
  shadow_pick: null,
  agreement: 'unknown',
  consensus_score: 50,
  decision_label: 'shadow_indisponible',
  risk_adjustment: 0,
  display_message: 'Signal ML shadow indisponible. La lecture officielle reste Elo/Poisson.',
  explanation: ['Le modèle officiel Elo/Poisson reste la seule prédiction utilisée.'],
};

export const mockHybridSummary: HybridSummary = {
  mode: 'official_with_shadow_advisory',
  candidate_is_production: false,
  production_model_version: 'elo-poisson-calibrated-v1',
  shadow_summary: mockMlShadowSummary,
  shadow_backtesting: mockMlShadowBacktesting,
  recommendation: 'insufficient_data',
  reason: 'Donn?es shadow insuffisantes pour recommander un usage hybride.',
};



export const mockRefreshJobStatus: RefreshJobStatus = {
  job_id: null,
  status: 'idle',
  started_at: null,
  finished_at: null,
  duration_ms: null,
  result: null,
  error: null,
};

export const mockAdminWorkflowStatus: AdminWorkflowStatus = {
  refresh: { last_refresh_at: null, storage: 'memory', matches_imported: 0, predictions_imported: 0 },
  feature_store: { ready: false, snapshots_count: 0, training_rows_available: 0, target_coverage: 0 },
  feature_engineering: { feature_set_version: 'pre-match-advanced-v1', advanced_feature_coverage: 0 },
  candidate_model: { trained: false, status: 'not_trained', model_version: null, accuracy: null },
  shadow_predictions: { generated: false, count: 0, disagreement_count: 0 },
  shadow_backtesting: { ready: false, evaluated_matches: 0, shadow_accuracy: 0, activation_recommendation: 'do_not_activate' },
  hybrid: { mode: 'official_with_shadow_advisory', recommendation: 'insufficient_data' },
  dataset_quality: {
    safe_for_training: mockFeatureQualityReport.safe_for_training,
    recommendation: mockFeatureQualityReport.recommendation,
    average_quality_score: mockFeatureQualityReport.average_quality_score,
    blocked_rows: mockFeatureQualityReport.blocked_rows,
    warning_rows: mockFeatureQualityReport.warning_rows,
  },
  latest_refresh_job: mockRefreshJobStatus,
  latest_feature_store_job: mockRefreshJobStatus,
  next_step: 'refresh_data',
  admin_alerts: {
  overall_status: mockAdminAlertsReport.overall_status,
  alerts_count: mockAdminAlertsReport.alerts_count,
  critical_count: mockAdminAlertsReport.critical_count,
  warning_count: mockAdminAlertsReport.warning_count,
  next_best_action: mockAdminAlertsReport.next_best_action,
},
};


export const mockHybridEngineDecision: HybridEngineDecision = {
  engine_version: 'hybrid-engine-v1',
  mode: 'official_with_hybrid_advisory',
  candidate_is_production: false,
  official_prediction_stays_primary: true,
  production_model_version: 'elo-poisson-calibrated-v1',
  candidate_model_version: null,
  production_pick: 'home',
  shadow_pick: null,
  agreement: 'unknown',
  consensus_score: 45,
  risk_adjustment: 0,
  decision_level: 'unknown',
  decision_label: 'shadow_indisponible',
  action: 'insufficient_shadow_data',
  display_title: 'Signal ML indisponible',
  display_message: 'Le modèle officiel Elo/Poisson reste la référence.',
  explanation: ['Le moteur hybride ne remplace pas la prédiction officielle.'],
  warnings: ['Signal shadow indisponible.'],
  evidence: {
    production_confidence: null,
    shadow_confidence: null,
    confidence_delta: null,
    disagreement_level: null,
    shadow_backtesting_status: 'empty',
    shadow_accuracy: null,
    production_accuracy: null,
    activation_recommendation: 'do_not_activate',
  },
};

export const mockHybridEngineSummary: HybridEngineSummary = {
  engine_version: 'hybrid-engine-v1',
  mode: 'official_with_hybrid_advisory',
  candidate_is_production: false,
  official_prediction_stays_primary: true,
  production_model_version: 'elo-poisson-calibrated-v1',
  limit: 200,
  view: 'upcoming',
  processed_predictions: 0,
  duration_ms: 0,
  shadow_evaluated_matches: 0,
  shadow_accuracy: 0,
  shadow_activation_recommendation: 'do_not_activate',
  shadow_backtesting: mockMlShadowBacktesting,
  summary: { strong_count: 0, medium_count: 0, weak_count: 0, avoid_count: 0, unknown_count: 0 },
  recommendation: 'insufficient_shadow_data',
  reason: 'Aucune donn?e shadow suffisante pour alimenter le moteur hybride.',
};
