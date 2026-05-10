import type { NextApiRequest, NextApiResponse } from 'next';

type JsonObject = Record<string, unknown>;

function parseBody(text: string, fallback: string): JsonObject {
  if (!text) return { detail: fallback };

  try {
    const parsed = JSON.parse(text) as unknown;
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? (parsed as JsonObject)
      : { detail: parsed ?? fallback };
  } catch {
    return { detail: text };
  }
}

function numberFrom(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function candidateFrom(modelVersions: JsonObject): JsonObject {
  const directCandidate = modelVersions.latest_candidate_model;
  if (directCandidate && typeof directCandidate === 'object' && !Array.isArray(directCandidate)) {
    return directCandidate as JsonObject;
  }

  const versions = Array.isArray(modelVersions.versions) ? modelVersions.versions : [];
  const candidate = versions.find((version) => {
    if (!version || typeof version !== 'object' || Array.isArray(version)) return false;
    const item = version as JsonObject;
    return String(item.status ?? '').toLowerCase() === 'candidate' && Boolean(item.model_version);
  });

  return candidate && typeof candidate === 'object' && !Array.isArray(candidate) ? (candidate as JsonObject) : {};
}

async function fetchBackendJson(
  apiUrl: string,
  path: string,
  adminKey: string,
  timeoutMs: number,
): Promise<{ status: number; body: JsonObject }> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${apiUrl}${path}`, {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        'X-Admin-Key': adminKey,
      },
      signal: controller.signal,
    });
    const text = await response.text();
    return { status: response.status, body: parseBody(text, response.statusText || 'Backend response is empty') };
  } finally {
    clearTimeout(timeout);
  }
}

function buildWorkflowFallback(
  featureSummary: JsonObject,
  refreshStatus: JsonObject,
  modelVersions: JsonObject,
  warning: string,
): JsonObject {
  const snapshotsCount = numberFrom(featureSummary.snapshots_count);
  const trainingRowsAvailable = numberFrom(featureSummary.with_target_count);
  const featureReady = snapshotsCount > 0 || trainingRowsAvailable > 0;
  const candidate = candidateFrom(modelVersions);
  const candidateMetrics =
    candidate.metrics && typeof candidate.metrics === 'object' && !Array.isArray(candidate.metrics)
      ? (candidate.metrics as JsonObject)
      : {};
  const candidateStatus = String(candidate.status ?? 'not_trained');
  const candidateTrained =
    ['ok', 'trained', 'success', 'candidate', 'shadow'].includes(candidateStatus) ||
    numberFrom(candidate.rows_used) >= 30 ||
    Boolean(candidate.model_version);
  const shadowCount = numberFrom(candidateMetrics.shadow_predictions_saved);
  const disagreementCount = numberFrom(candidateMetrics.disagreement_count);
  const storage =
    featureSummary.storage === 'postgresql' || refreshStatus.storage === 'postgresql'
      ? 'postgresql'
      : String(featureSummary.storage ?? refreshStatus.storage ?? 'unknown');
  const dataImported = storage === 'postgresql' && numberFrom(refreshStatus.matches_imported) > 0;

  return {
    refresh: {
      data_imported: dataImported,
      last_refresh_at: refreshStatus.last_refresh_at ?? null,
      source: refreshStatus.source ?? 'football-data.org',
      storage,
      matches_imported: numberFrom(refreshStatus.matches_imported),
      teams_imported: numberFrom(refreshStatus.teams_imported),
      predictions_imported: numberFrom(refreshStatus.predictions_imported),
      predictions_generated: numberFrom(refreshStatus.predictions_generated),
      predictions_saved: numberFrom(refreshStatus.predictions_saved ?? refreshStatus.predictions_imported),
      predictions_failed: numberFrom(refreshStatus.predictions_failed),
    },
    feature_store: {
      ready: featureReady,
      snapshots_count: snapshotsCount,
      training_rows_available: trainingRowsAvailable,
      target_coverage: numberFrom(featureSummary.target_coverage),
      storage,
    },
    feature_engineering: {
      feature_set_version: featureSummary.feature_set_version ?? 'pre-match-advanced-v1',
      advanced_feature_coverage: numberFrom(
        (featureSummary.advanced_feature_coverage as JsonObject | undefined)?.coverage_percent,
      ),
    },
    candidate_model: {
      trained: candidateTrained,
      status: candidateTrained ? 'trained' : candidateStatus,
      model_version: candidate.model_version ?? null,
      accuracy: candidate.accuracy ?? null,
    },
    shadow_predictions: { generated: shadowCount > 0, count: shadowCount, disagreement_count: disagreementCount },
    shadow_backtesting: {
      ready: false,
      evaluated_matches: 0,
      shadow_accuracy: 0,
      activation_recommendation: 'unknown',
    },
    hybrid: { mode: 'official_with_shadow_advisory', recommendation: 'workflow_fallback' },
    next_step: candidateTrained && shadowCount > 0
      ? 'review_shadow_backtesting'
      : candidateTrained
      ? 'generate_shadow_predictions'
      : featureReady
        ? 'train_candidate_model'
        : dataImported
          ? 'build_feature_store'
          : 'refresh_data',
    warning,
    fallback_source: 'feature-summary-refresh-status-and-model-versions',
  };
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const method = 'GET';
  const timeoutMs: 45000 = 45000;
  const workflowAttemptTimeoutMs = 8000;

  if (req.method !== method) {
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
  const adminKey = process.env.ADMIN_API_KEY;
  const requireAdminKey: true = true;

  if (!apiUrl) {
    return res.status(500).json({ detail: 'NEXT_PUBLIC_API_URL missing on Vercel environment' });
  }

  if (requireAdminKey && !adminKey) {
    return res.status(500).json({ detail: 'ADMIN_API_KEY missing on Vercel server environment' });
  }

  const serverAdminKey = adminKey as string;
  const backendWorkflowPath = '/admin/workflow-status';
  void backendWorkflowPath;
  void workflowAttemptTimeoutMs;

  try {
    const [featureSummaryResult, refreshStatusResult, modelVersionsResult] = await Promise.allSettled([
      fetchBackendJson(apiUrl, '/features/summary', serverAdminKey, 8000),
      fetchBackendJson(apiUrl, '/admin/refresh-status', serverAdminKey, 8000),
      fetchBackendJson(apiUrl, '/models/versions', serverAdminKey, 30000),
    ]);

    const featureSummary =
      featureSummaryResult.status === 'fulfilled' && featureSummaryResult.value.status < 500
        ? featureSummaryResult.value.body
        : {};
    const refreshStatus =
      refreshStatusResult.status === 'fulfilled' && refreshStatusResult.value.status < 500
        ? refreshStatusResult.value.body
        : {};
    const modelVersions =
      modelVersionsResult.status === 'fulfilled' && modelVersionsResult.value.status < 500
        ? modelVersionsResult.value.body
        : {};

    const fallback = buildWorkflowFallback(
      featureSummary,
      refreshStatus,
      modelVersions,
      'Workflow status synthesized from lightweight backend endpoints.',
    );

    return res.status(200).json(fallback);
  } catch (error) {
    return res.status(200).json(
      buildWorkflowFallback(
        {},
        {},
        {},
        error instanceof Error ? error.message : 'Workflow status synthesized with empty fallback.',
      ),
    );
  }
}
