import {
  getMockPrediction,
  getMockMatch,
  getMockTeam,
  buildDashboardSummary,
  matches,
  performanceMetrics,
  predictions,
  teams,
  type Match,
  type DashboardSummary,
  type HealthResponse,
  type PerformanceMetrics,
  type Prediction,
  type RefreshResponse,
  type Team,
} from '~/lib/mock-data';

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');

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
  const adminKey = process.env.NEXT_PUBLIC_ADMIN_API_KEY;

  if (!adminKey) {
    return {
      status: 'error',
      error: 'Admin key not configured',
    };
  }

  return safeFetchJson<RefreshResponse>('/admin/refresh-data', {
    method: 'POST',
    headers: {
      'X-Admin-Key': adminKey,
    },
  });
}
