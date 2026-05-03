import {
  getMockPrediction,
  getMockMatch,
  getMockTeam,
  mockBacktestingReport,
  mockBuildFeatureStoreResponse,
  mockFeatureDataset,
  mockFeatureQualityReport,
  mockFeatureSummary,
  mockMlFeatureImportance,
  mockMlComparison,
  mockMlShadowPredictions,
  mockMlShadowSummary,
  mockGenerateShadowPredictionsResponse,
  mockMlStatus,
  mockModelComparison,
  mockModelsMetadata,
  mockPredictionSnapshots,
  mockTrainingReport,
  mockMlShadowBacktesting,
  mockHybridSummary,
  mockHybridEngineSummary,
  mockExplainabilitySummary,
  mockAdminWorkflowStatus,
  mockRefreshJobStatus,
  buildDashboardSummary,
  matches,
  performanceMetrics,
  predictions,
  teams,
  mockModelGovernance,
  mockAdminAlertsReport,
  type AdminAlertsReport,
  type ModelGovernanceReport,
  type Match,
  type AdminWorkflowStatus,
  type BacktestingReport,
  type BuildFeatureStoreResponse,
  type DatasetQualityReport,
  type FeatureDatasetRow,
  type FeatureImportanceRow,
  type FeatureSummary,
  type MlStatus,
  type MlComparison,
  type MlShadowRow,
  type MlShadowSummary,
  type GenerateShadowPredictionsResponse,
  type MatchView,
  type ModelComparison,
  type ModelsMetadata,
  type PredictionSnapshot,
  type DashboardSummary,
  type HealthResponse,
  type HybridSummary,
  type HybridEngineSummary,
  type ExplainabilitySummary,
  type PerformanceMetrics,
  type Prediction,
  type RefreshJobStatus,
  type RefreshResponse,
  type Team,
  type TrainingReport,
} from '~/lib/mock-data';

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ||
  'https://footiq-pro-production.up.railway.app';

async function safeFetchJson<T>(path: string, init?: RequestInit): Promise<T | null> {
  if (!API_URL) {
    return null;
  }

  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { Accept: 'application/json', ...(init?.headers ?? {}) },
    });

    if (!response.ok) {
      return null;
    }

    const contentType = response.headers.get('content-type') ?? '';

    if (!contentType.includes('application/json')) {
      return null;
    }

    const data = (await response.json()) as T;

    return data;
  } catch {
    return null;
  }
}

export async function getAdminAlerts(): Promise<AdminAlertsReport> {
  const data = await safeFetchJson<AdminAlertsReport>('/admin/alerts');

  return data ?? mockAdminAlertsReport;
}

export async function getBackendHealth(): Promise<HealthResponse | null> {
  return safeFetchJson<HealthResponse>('/health');
}

export async function getHealth() {
  return getBackendHealth();
}

export async function getPredictions(options?: { includeHybridEngine?: boolean; includeExplainability?: boolean; limit?: number; view?: MatchView }): Promise<Prediction[]> {
  const params = new URLSearchParams();
  if (options?.includeHybridEngine) params.set('include_hybrid_engine', 'true');
  if (options?.includeExplainability) params.set('include_explainability', 'true');
  if (options?.limit) params.set('limit', String(Math.min(Math.max(Math.round(options.limit), 1), 500)));
  if (options?.view) params.set('view', options.view);
  const query = params.toString();
  const data = await safeFetchJson<Prediction[]>(`/predictions${query ? `?${query}` : ''}`);

  return Array.isArray(data) && data.length > 0 ? data : predictions;
}

export async function getPrediction(matchId: string): Promise<Prediction> {
  const data = await safeFetchJson<Prediction>(`/predictions/${encodeURIComponent(matchId)}`);

  return data ?? getMockPrediction(matchId);
}

export async function getMatches(options?: { view?: MatchView; q?: string; status?: string; includeFinished?: boolean }): Promise<Match[]> {
  const params = new URLSearchParams();
  if (options?.view) params.set('view', options.view);
  if (options?.q) params.set('q', options.q);
  if (options?.status) params.set('status', options.status);
  if (typeof options?.includeFinished === 'boolean') params.set('include_finished', String(options.includeFinished));
  const query = params.toString();
  const data = await safeFetchJson<Match[]>(`/matches${query ? `?${query}` : ''}`);

  return Array.isArray(data) && data.length > 0 ? data : matches;
}

export async function getMatch(matchId: string): Promise<Match> {
  const data = await safeFetchJson<Match>(`/matches/${encodeURIComponent(matchId)}`);

  return data ?? getMockMatch(matchId);
}

export async function getTeams(): Promise<Team[]> {
  const data = await safeFetchJson<Team[]>('/teams');

  return Array.isArray(data) && data.length > 0 ? data : teams;
}

export async function getTeam(teamId: string): Promise<Team> {
  const data = await safeFetchJson<Team>(`/teams/${encodeURIComponent(teamId)}`);

  return data ?? getMockTeam(teamId);
}


export async function getModels(): Promise<ModelsMetadata> {
  const data = await safeFetchJson<ModelsMetadata>('/models');

  return data ?? mockModelsMetadata;
}

export async function getModelComparison(): Promise<ModelComparison> {
  const data = await safeFetchJson<ModelComparison>('/models/comparison');

  return data ?? mockModelComparison;
}

export async function getPredictionSnapshots(): Promise<PredictionSnapshot[]> {
  const data = await safeFetchJson<PredictionSnapshot[]>('/predictions/snapshots');

  return Array.isArray(data) ? data : mockPredictionSnapshots;
}

export async function getBacktesting(): Promise<BacktestingReport> {
  const data = await safeFetchJson<BacktestingReport>('/backtesting');

  return data ?? mockBacktestingReport;
}

export async function getFeatureSummary(): Promise<FeatureSummary> {
  const data = await safeFetchJson<FeatureSummary>('/features/summary');

  return data ?? mockFeatureSummary;
}

export async function getFeatureDataset(limit = 100): Promise<FeatureDatasetRow[]> {
  const safeLimit = Math.min(Math.max(Math.round(limit), 1), 500);
  const data = await safeFetchJson<FeatureDatasetRow[]>(`/features/dataset?limit=${safeLimit}`);

  return Array.isArray(data) ? data : mockFeatureDataset;
}

export async function getFeatureQualityReport(limit = 1000): Promise<DatasetQualityReport> {
  const safeLimit = Math.min(Math.max(Math.round(limit), 1), 5000);
  const data = await safeFetchJson<DatasetQualityReport>(`/features/quality-report?limit=${safeLimit}`);

  return data ?? mockFeatureQualityReport;
}

export async function getMlStatus(): Promise<MlStatus> {
  const data = await safeFetchJson<MlStatus>('/ml/status');

  return data ?? mockMlStatus;
}

export async function getMlFeatureImportance(): Promise<FeatureImportanceRow[]> {
  const data = await safeFetchJson<FeatureImportanceRow[]>('/ml/feature-importance');

  return Array.isArray(data) ? data : mockMlFeatureImportance;
}

export async function getMlComparison(): Promise<MlComparison> {
  const data = await safeFetchJson<MlComparison>('/ml/comparison');

  return data ?? mockMlComparison;
}

export async function getMlShadowSummary(): Promise<MlShadowSummary> {
  const data = await safeFetchJson<MlShadowSummary>('/ml/shadow-summary');

  return data ?? mockMlShadowSummary;
}

export async function getMlShadowPredictions(limit = 100, view: MatchView = 'all'): Promise<MlShadowRow[]> {
  const safeLimit = Math.min(Math.max(Math.round(limit), 1), 500);
  const data = await safeFetchJson<MlShadowRow[]>(`/ml/shadow-predictions?limit=${safeLimit}&view=${encodeURIComponent(view)}`);

  return Array.isArray(data) ? data : mockMlShadowPredictions;
}

export async function generateShadowPredictions(options?: { limit?: number; force?: boolean; view?: MatchView }): Promise<GenerateShadowPredictionsResponse> {
  const limit = Math.min(Math.max(Math.round(options?.limit ?? 500), 1), 2000);
  const force = options?.force ?? false;
  const view = options?.view ?? 'upcoming';

  try {
    const response = await fetch(`/api/admin/generate-shadow-predictions?limit=${limit}&force=${force}&view=${encodeURIComponent(view)}`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });
    const contentType = response.headers.get('content-type') ?? '';
    const body = contentType.includes('application/json') ? await response.json() : null;

    if (!response.ok) {
      return {
        ...mockGenerateShadowPredictionsResponse,
        status: 'error',
        detail: body?.detail ?? `Shadow generation failed with status ${response.status}`,
      };
    }

    return (body as GenerateShadowPredictionsResponse) ?? mockGenerateShadowPredictionsResponse;
  } catch (error) {
    return {
      ...mockGenerateShadowPredictionsResponse,
      status: 'error',
      detail: error instanceof Error ? error.message : 'Shadow generation request failed',
    };
  }
}

export async function trainCandidateModel(options?: { modelType?: string; limit?: number; bypassQualityGate?: boolean }): Promise<TrainingReport> {
  const modelType = options?.modelType ?? 'random_forest';
  const limit = Math.min(Math.max(Math.round(options?.limit ?? 5000), 1), 10000);
  const bypassQualityGate = options?.bypassQualityGate ?? false;

  try {
    const response = await fetch(
      `/api/admin/train-candidate-model?model_type=${encodeURIComponent(modelType)}&limit=${encodeURIComponent(String(limit))}&bypass_quality_gate=${encodeURIComponent(String(bypassQualityGate))}`,
      {
        method: 'POST',
        headers: { Accept: 'application/json' },
      },
    );
    const contentType = response.headers.get('content-type') ?? '';
    const body = contentType.includes('application/json') ? await response.json() : null;

    if (!response.ok) {
      return {
        ...mockTrainingReport,
        status: 'error',
        detail: body?.detail ?? `Training failed with status ${response.status}`,
      };
    }

    return (body as TrainingReport) ?? mockTrainingReport;
  } catch (error) {
    return {
      ...mockTrainingReport,
      status: 'error',
      detail: error instanceof Error ? error.message : 'Candidate training request failed',
    };
  }
}

export async function getPerformance(): Promise<PerformanceMetrics> {
  const data = await safeFetchJson<PerformanceMetrics>('/performance');

  return data ?? performanceMetrics;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  const data = await safeFetchJson<DashboardSummary>('/dashboard/summary');

  return data ?? buildDashboardSummary();
}

export async function getRefreshStatus(): Promise<RefreshResponse | null> {
  return safeFetchJson<RefreshResponse>('/admin/refresh-status');
}


export async function getHybridEngineSummary(options?: { limit?: number; view?: MatchView }): Promise<HybridEngineSummary> {
  const limit = Math.min(Math.max(Math.round(options?.limit ?? 200), 1), 1000);
  const view = options?.view ?? 'upcoming';
  const data = await safeFetchJson<HybridEngineSummary>(`/hybrid/engine-summary?limit=${limit}&view=${encodeURIComponent(view)}`);

  return data ?? mockHybridEngineSummary;
}

export async function getHybridSummary(): Promise<HybridSummary> {
  const data = await safeFetchJson<HybridSummary>('/hybrid/summary');

  return data ?? mockHybridSummary;
}

export async function getExplainabilitySummary(limit = 200, view: MatchView = 'upcoming'): Promise<ExplainabilitySummary> {
  const safeLimit = Math.min(Math.max(Math.round(limit), 1), 1000);
  const data = await safeFetchJson<ExplainabilitySummary>(`/explainability/summary?limit=${safeLimit}&view=${encodeURIComponent(view)}`);

  return data ?? mockExplainabilitySummary;
}

export async function getAdminWorkflowStatus(): Promise<AdminWorkflowStatus> {
  const data = await safeFetchJson<AdminWorkflowStatus>('/admin/workflow-status');

  return data ?? mockAdminWorkflowStatus;
}


export async function getRefreshJobStatus(jobId?: string): Promise<RefreshJobStatus> {
  const query = jobId ? `?job_id=${encodeURIComponent(jobId)}` : '';
  try {
    const response = await fetch(`/api/admin/refresh-job-status${query}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    const contentType = response.headers.get('content-type') ?? '';
    const body = contentType.includes('application/json') ? await response.json() : null;

    if (!response.ok) {
      return { ...mockRefreshJobStatus, status: 'error', error: body?.detail ?? `Job status failed with status ${response.status}` };
    }

    return (body as RefreshJobStatus) ?? mockRefreshJobStatus;
  } catch (error) {
    return { ...mockRefreshJobStatus, status: 'error', error: error instanceof Error ? error.message : 'Refresh job status failed' };
  }
}

export async function getFeatureStoreJobStatus(jobId?: string): Promise<RefreshJobStatus> {
  const query = jobId ? `?job_id=${encodeURIComponent(jobId)}` : '';
  try {
    const response = await fetch(`/api/admin/feature-store-job-status${query}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    const contentType = response.headers.get('content-type') ?? '';
    const body = contentType.includes('application/json') ? await response.json() : null;

    if (!response.ok) {
      return { ...mockRefreshJobStatus, status: 'error', error: body?.detail ?? `Feature Store job status failed with status ${response.status}` };
    }

    return (body as RefreshJobStatus) ?? mockRefreshJobStatus;
  } catch (error) {
    return { ...mockRefreshJobStatus, status: 'error', error: error instanceof Error ? error.message : 'Feature Store job status failed' };
  }
}

export async function refreshData(): Promise<RefreshResponse | null> {
  try {
    const response = await fetch('/api/admin/refresh-data', {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });

    const contentType = response.headers.get('content-type') ?? '';
    const body = contentType.includes('application/json') ? await response.json() : null;

    if (!response.ok) {
      return {
        status: 'error',
        detail: body?.detail ?? `Refresh failed with status ${response.status}`,
      };
    }

    return body as RefreshResponse;
  } catch (error) {
    return {
      status: 'error',
      detail: error instanceof Error ? error.message : 'Refresh request failed',
    };
  }
}

export async function buildFeatureStore(options?: { limit?: number; force?: boolean }): Promise<BuildFeatureStoreResponse> {
  const limit = Math.min(Math.max(Math.round(options?.limit ?? 500), 1), 2000);
  const force = options?.force ?? false;

  try {
    const response = await fetch(`/api/admin/build-feature-store?limit=${limit}&force=${force}`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });
    const contentType = response.headers.get('content-type') ?? '';
    const body = contentType.includes('application/json') ? await response.json() : null;

    if (!response.ok) {
      return {
        ...mockBuildFeatureStoreResponse,
        status: 'error',
        detail: body?.detail ?? `Feature Store failed with status ${response.status}`,
      };
    }

    return (body as BuildFeatureStoreResponse) ?? mockBuildFeatureStoreResponse;
  } catch (error) {
    return {
      ...mockBuildFeatureStoreResponse,
      status: 'error',
      detail: error instanceof Error ? error.message : 'Feature Store request failed',
    };
  }
}

export async function getMlShadowBacktesting(limit = 500) {
  const data = await safeFetchJson<typeof mockMlShadowBacktesting>(
    `/ml/shadow-backtesting?limit=${encodeURIComponent(String(limit))}`
  );

  return data ?? mockMlShadowBacktesting;
}

export async function getModelGovernance(): Promise<ModelGovernanceReport> {
  const data = await safeFetchJson<ModelGovernanceReport>('/models/governance');

  return data ?? mockModelGovernance;
}