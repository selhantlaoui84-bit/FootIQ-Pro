import {
  getMockPrediction,
  getMockMatch,
  getMockTeam,
  mockBacktestingReport,
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
  buildDashboardSummary,
  matches,
  performanceMetrics,
  predictions,
  teams,
  mockModelGovernance,
  mockAdminAlertsReport,
  type AdminAlertsReport,
  type AdminDiagnosticsResponse,
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

const IS_BUILD = process.env.NEXT_PHASE === 'phase-production-build';


async function fetchBackendJson<T>(path: string, init?: RequestInit, timeoutMs = 8000): Promise<T | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const url = path.startsWith('http') ? path : `${API_URL}${path}`;

    const response = await fetch(url, {
      ...init,
      signal: controller.signal,
    });

    if (!response.ok) {
      return null;
    }

    return (await response.json()) as T;
  } catch {
    return null;
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchProxyJson<T>(path: string, init?: RequestInit, timeoutMs = 15000): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const headers = new Headers(init?.headers);
    headers.set('Accept', 'application/json');

    const response = await fetch(path, {
      ...init,
      method: init?.method ?? 'GET',
      headers,
      signal: controller.signal,
    });
    const text = await response.text();
    let body: any = null;

    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = { detail: text };
      }
    }

    if (!response.ok) {
      throw new Error(body?.detail ?? body?.error ?? `Proxy request failed with status ${response.status}`);
    }

    if (!body) {
      throw new Error(`Proxy ${path} returned an empty response.`);
    }

    return body as T;
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error(`Proxy ${path} timed out after ${timeoutMs} ms.`);
    }

    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

export async function getAdminAlerts(): Promise<AdminAlertsReport> {
  if (IS_BUILD) return mockAdminAlertsReport;

  return fetchProxyJson<AdminAlertsReport>('/api/admin/alerts', undefined, 15000);
}

export async function getBackendHealth(): Promise<HealthResponse | null> {
  if (IS_BUILD) return null;

  return fetchBackendJson<HealthResponse>('/health', undefined, 3000);
}

export async function getHealth() {
  return getBackendHealth();
}

export async function getPredictions(options?: { includeHybridEngine?: boolean; includeExplainability?: boolean; limit?: number; view?: MatchView }): Promise<Prediction[]> {
  if (IS_BUILD) {
    return predictions;
  }

  const params = new URLSearchParams();
  if (options?.includeHybridEngine) params.set('include_hybrid_engine', 'true');
  if (options?.includeExplainability) params.set('include_explainability', 'true');
  if (options?.limit) params.set('limit', String(Math.min(Math.max(Math.round(options.limit), 1), 500)));
  if (options?.view) params.set('view', options.view);

  const query = params.toString();
  const data = await fetchBackendJson<Prediction[]>(`/predictions${query ? `?${query}` : ''}`, undefined, 3000);

  return Array.isArray(data) && data.length > 0 ? data : predictions;
}

export async function getPrediction(matchId: string): Promise<Prediction> {
  if (IS_BUILD) return getMockPrediction(matchId);

  const data = await fetchBackendJson<Prediction>(`/predictions/${encodeURIComponent(matchId)}`, undefined, 3000);

  return data ?? getMockPrediction(matchId);
}

export async function getMatches(options?: { view?: MatchView; q?: string; status?: string; includeFinished?: boolean }): Promise<Match[]> {
  if (IS_BUILD) {
    return matches;
  }

  const params = new URLSearchParams();
  if (options?.view) params.set('view', options.view);
  if (options?.q) params.set('q', options.q);
  if (options?.status) params.set('status', options.status);
  if (typeof options?.includeFinished === 'boolean') params.set('include_finished', String(options.includeFinished));

  const query = params.toString();
  const data = await fetchBackendJson<Match[]>(`/matches${query ? `?${query}` : ''}`, undefined, 3000);

  return Array.isArray(data) && data.length > 0 ? data : matches;
}

export async function getMatch(matchId: string): Promise<Match> {
  if (IS_BUILD) return getMockMatch(matchId);

  const data = await fetchBackendJson<Match>(`/matches/${encodeURIComponent(matchId)}`, undefined, 3000);

  return data ?? getMockMatch(matchId);
}

export async function getTeams(): Promise<Team[]> {
  if (IS_BUILD) {
    return teams;
  }

  const data = await fetchBackendJson<Team[]>('/teams', undefined, 3000);

  return Array.isArray(data) && data.length > 0 ? data : teams;
}

export async function getTeam(teamId: string): Promise<Team> {
  if (IS_BUILD) return getMockTeam(teamId);

  const data = await fetchBackendJson<Team>(`/teams/${encodeURIComponent(teamId)}`, undefined, 3000);

  return data ?? getMockTeam(teamId);
}


export async function getModels(): Promise<ModelsMetadata> {
  if (IS_BUILD) return mockModelsMetadata;

  const data = await fetchBackendJson<ModelsMetadata>('/models', undefined, 3000);

  return data ?? mockModelsMetadata;
}

export async function getModelComparison(): Promise<ModelComparison> {
  if (IS_BUILD) return mockModelComparison;

  const data = await fetchBackendJson<ModelComparison>('/models/comparison', undefined, 3000);

  return data ?? mockModelComparison;
}

export async function getPredictionSnapshots(): Promise<PredictionSnapshot[]> {
  if (IS_BUILD) return mockPredictionSnapshots;

  const data = await fetchBackendJson<PredictionSnapshot[]>('/predictions/snapshots', undefined, 3000);

  return Array.isArray(data) ? data : mockPredictionSnapshots;
}

export async function getBacktesting(): Promise<BacktestingReport> {
  if (IS_BUILD) return mockBacktestingReport;

  const data = await fetchBackendJson<BacktestingReport>('/backtesting', undefined, 3000);
  return data ?? mockBacktestingReport;
}

export async function getFeatureSummary(): Promise<FeatureSummary> {
  if (IS_BUILD) return mockFeatureSummary;

  try {
    return await fetchProxyJson<FeatureSummary>('/api/admin/feature-summary', undefined, 15000);
  } catch (error) {
    throw new Error(
      error instanceof Error
        ? `Impossible de charger /features/summary depuis le backend. ${error.message}`
        : 'Impossible de charger /features/summary depuis le backend.',
    );
  }
}

export async function getFeatureDataset(limit = 100): Promise<FeatureDatasetRow[]> {
  if (IS_BUILD) return mockFeatureDataset;

  const safeLimit = Math.min(Math.max(Math.round(limit), 1), 500);
  const data = await fetchBackendJson<FeatureDatasetRow[]>(`/features/dataset?limit=${safeLimit}`, undefined, 3000);

  return Array.isArray(data) ? data : mockFeatureDataset;
}

export async function getFeatureQualityReport(limit = 1000): Promise<DatasetQualityReport> {
  if (IS_BUILD) return mockFeatureQualityReport;

  const safeLimit = Math.min(Math.max(Math.round(limit), 1), 5000);
  return fetchProxyJson<DatasetQualityReport>(`/api/admin/feature-quality-report?limit=${safeLimit}`, undefined, 15000);
}

export async function getMlStatus(): Promise<MlStatus> {
  if (IS_BUILD) return mockMlStatus;

  const data = await fetchBackendJson<MlStatus>('/ml/status', undefined, 3000);
  return data ?? mockMlStatus;
}

export async function getMlFeatureImportance(): Promise<FeatureImportanceRow[]> {
  if (IS_BUILD) return mockMlFeatureImportance;

  const data = await fetchBackendJson<FeatureImportanceRow[]>('/ml/feature-importance', undefined, 3000);
  return data ?? mockMlFeatureImportance;
}

export async function getMlComparison(): Promise<MlComparison> {
  if (IS_BUILD) return mockMlComparison;

  const data = await fetchBackendJson<MlComparison>('/ml/comparison', undefined, 3000);
  return data ?? mockMlComparison;
}

export async function getMlShadowSummary(): Promise<MlShadowSummary> {
  if (IS_BUILD) return mockMlShadowSummary;

  const data = await fetchBackendJson<MlShadowSummary>('/ml/shadow-summary', undefined, 3000);
  return data ?? mockMlShadowSummary;
}

export async function getMlShadowPredictions(limit = 100, view: MatchView = 'all'): Promise<MlShadowRow[]> {
  if (IS_BUILD) return mockMlShadowPredictions;

  const safeLimit = Math.min(Math.max(Math.round(limit), 1), 500);
  const data = await fetchBackendJson<MlShadowRow[]>(
    `/ml/shadow-predictions?limit=${safeLimit}&view=${encodeURIComponent(view)}`,
    undefined,
    3000,
  );

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

export async function getShadowPredictionJobStatus(jobId?: string): Promise<RefreshJobStatus> {
  const query = jobId ? `?job_id=${encodeURIComponent(jobId)}` : '';
  return fetchProxyJson<RefreshJobStatus>(`/api/admin/shadow-prediction-job-status${query}`, undefined, 10000);
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
  if (IS_BUILD) {
    return performanceMetrics;
  }

  const data = await fetchBackendJson<PerformanceMetrics>('/performance', undefined, 3000);

  return data ?? performanceMetrics;
}

export async function getDashboardSummary(): Promise<DashboardSummary> {
  if (IS_BUILD) {
    return buildDashboardSummary();
  }

  return fetchProxyJson<DashboardSummary>('/api/admin/dashboard-summary', undefined, 15000);
}

export async function getRefreshStatus(): Promise<RefreshResponse | null> {
  if (IS_BUILD) return null;

  return fetchProxyJson<RefreshResponse>('/api/admin/refresh-status', undefined, 15000);
}

export async function getAdminDiagnostics(): Promise<AdminDiagnosticsResponse | null> {
  if (IS_BUILD) return null;

  try {
    const response = await fetch('/api/admin/diagnostics', {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    const contentType = response.headers.get('content-type') ?? '';
    const body = contentType.includes('application/json') ? await response.json() : null;

    if (!response.ok) {
      return {
        hasApiUrl: false,
        apiUrlHost: '',
        hasAdminApiKey: false,
        backendHealth: { status: 'error', error: body?.detail ?? `Diagnostics failed with status ${response.status}` },
        refreshStatus: { status: 'error', error: body?.detail ?? `Diagnostics failed with status ${response.status}` },
      };
    }

    return body as AdminDiagnosticsResponse;
  } catch (error) {
    return {
      hasApiUrl: false,
      apiUrlHost: '',
      hasAdminApiKey: false,
      backendHealth: { status: 'error', error: error instanceof Error ? error.message : 'Diagnostics request failed' },
      refreshStatus: { status: 'error', error: error instanceof Error ? error.message : 'Diagnostics request failed' },
    };
  }
}

export async function resetStaleJobs(options?: { force?: boolean }): Promise<{ status: string; reset_count?: number; detail?: string }> {
  try {
    const query = options?.force ? '?force=true' : '';
    const response = await fetch(`/api/admin/reset-stale-jobs${query}`, {
      method: 'POST',
      headers: { Accept: 'application/json' },
    });
    const contentType = response.headers.get('content-type') ?? '';
    const body = contentType.includes('application/json') ? await response.json() : null;

    if (!response.ok) {
      return { status: 'error', detail: body?.detail ?? `Reset stale jobs failed with status ${response.status}` };
    }

    return body as { status: string; reset_count?: number };
  } catch (error) {
    return { status: 'error', detail: error instanceof Error ? error.message : 'Reset stale jobs request failed' };
  }
}


export async function getHybridEngineSummary(options?: { limit?: number; view?: MatchView }): Promise<HybridEngineSummary> {
  if (IS_BUILD) return mockHybridEngineSummary;

  const limit = Math.min(Math.max(Math.round(options?.limit ?? 200), 1), 1000);
  const view = options?.view ?? 'upcoming';
  const data = await fetchBackendJson<HybridEngineSummary>(
    `/hybrid/engine-summary?limit=${limit}&view=${encodeURIComponent(view)}`,
    undefined,
    3000,
  );

  return data ?? mockHybridEngineSummary;
}

export async function getHybridSummary(): Promise<HybridSummary> {
  if (IS_BUILD) return mockHybridSummary;

  const data = await fetchBackendJson<HybridSummary>('/hybrid/summary', undefined, 3000);

  return data ?? mockHybridSummary;
}

export async function getExplainabilitySummary(limit = 200, view: MatchView = 'upcoming'): Promise<ExplainabilitySummary> {
  if (IS_BUILD) return mockExplainabilitySummary;

  const safeLimit = Math.min(Math.max(Math.round(limit), 1), 1000);
  const data = await fetchBackendJson<ExplainabilitySummary>(
    `/explainability/summary?limit=${safeLimit}&view=${encodeURIComponent(view)}`,
    undefined,
    3000
  );

  return data ?? mockExplainabilitySummary;
}

export async function getAdminWorkflowStatus(): Promise<AdminWorkflowStatus> {
  if (IS_BUILD) return mockAdminWorkflowStatus;

  return fetchProxyJson<AdminWorkflowStatus>('/api/admin/workflow-status', undefined, 45000);
}


export async function getRefreshJobStatus(jobId?: string): Promise<RefreshJobStatus> {
  const query = jobId ? `?job_id=${encodeURIComponent(jobId)}` : '';
  return fetchProxyJson<RefreshJobStatus>(`/api/admin/refresh-job-status${query}`, undefined, 10000);
}

export async function getFeatureStoreJobStatus(jobId?: string): Promise<RefreshJobStatus> {
  const query = jobId ? `?job_id=${encodeURIComponent(jobId)}` : '';
  return fetchProxyJson<RefreshJobStatus>(`/api/admin/feature-store-job-status${query}`, undefined, 10000);
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
        status: 'error',
        detail: body?.detail ?? `Feature Store failed with status ${response.status}`,
      };
    }

    return body as BuildFeatureStoreResponse;
  } catch (error) {
    return {
      status: 'error',
      detail: error instanceof Error ? error.message : 'Feature Store request failed',
    };
  }
}

export async function getMlShadowBacktesting(limit = 500) {
  if (IS_BUILD) return mockMlShadowBacktesting;

  const data = await fetchBackendJson<typeof mockMlShadowBacktesting>(
    `/ml/shadow-backtesting?limit=${encodeURIComponent(String(limit))}`,
    undefined,
    3000,
  );

  return data ?? mockMlShadowBacktesting;
}

export async function getModelGovernance(): Promise<ModelGovernanceReport> {
  if (IS_BUILD) return mockModelGovernance;

  return fetchProxyJson<ModelGovernanceReport>('/api/admin/model-governance', undefined, 15000);
}
