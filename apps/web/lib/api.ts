import {
  getMockPrediction,
  getMockMatch,
  getMockTeam,
  mockBacktestingReport,
  mockFeatureDataset,
  mockFeatureSummary,
  mockMlFeatureImportance,
  mockMlStatus,
  mockModelComparison,
  mockModelsMetadata,
  mockPredictionSnapshots,
  mockTrainingReport,
  buildDashboardSummary,
  matches,
  performanceMetrics,
  predictions,
  teams,
  type Match,
  type BacktestingReport,
  type FeatureDatasetRow,
  type FeatureImportanceRow,
  type FeatureSummary,
  type MlStatus,
  type ModelComparison,
  type ModelsMetadata,
  type PredictionSnapshot,
  type DashboardSummary,
  type HealthResponse,
  type PerformanceMetrics,
  type Prediction,
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

export async function getBackendHealth(): Promise<HealthResponse | null> {
  return safeFetchJson<HealthResponse>('/health');
}

export async function getHealth() {
  return getBackendHealth();
}

export async function getPredictions(): Promise<Prediction[]> {
  const data = await safeFetchJson<Prediction[]>('/predictions');

  return Array.isArray(data) && data.length > 0 ? data : predictions;
}

export async function getPrediction(matchId: string): Promise<Prediction> {
  const data = await safeFetchJson<Prediction>(`/predictions/${encodeURIComponent(matchId)}`);

  return data ?? getMockPrediction(matchId);
}

export async function getMatches(): Promise<Match[]> {
  const data = await safeFetchJson<Match[]>('/matches');

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

export async function getMlStatus(): Promise<MlStatus> {
  const data = await safeFetchJson<MlStatus>('/ml/status');

  return data ?? mockMlStatus;
}

export async function getMlFeatureImportance(): Promise<FeatureImportanceRow[]> {
  const data = await safeFetchJson<FeatureImportanceRow[]>('/ml/feature-importance');

  return Array.isArray(data) ? data : mockMlFeatureImportance;
}

export async function trainCandidateModel(options?: { modelType?: string; limit?: number }): Promise<TrainingReport> {
  const modelType = options?.modelType ?? 'random_forest';
  const limit = Math.min(Math.max(Math.round(options?.limit ?? 5000), 1), 10000);

  try {
    const response = await fetch(
      `/api/admin/train-candidate-model?model_type=${encodeURIComponent(modelType)}&limit=${encodeURIComponent(String(limit))}`,
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
