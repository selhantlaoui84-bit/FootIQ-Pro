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

function buildWorkflowFallback(featureSummary: JsonObject, refreshStatus: JsonObject, warning: string): JsonObject {
  const snapshotsCount = numberFrom(featureSummary.snapshots_count);
  const trainingRowsAvailable = numberFrom(featureSummary.with_target_count);
  const featureReady = snapshotsCount > 0 || trainingRowsAvailable > 0;
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
    candidate_model: { trained: false, status: 'unknown', model_version: null, accuracy: null },
    shadow_predictions: { generated: false, count: 0, disagreement_count: 0 },
    shadow_backtesting: {
      ready: false,
      evaluated_matches: 0,
      shadow_accuracy: 0,
      activation_recommendation: 'unknown',
    },
    hybrid: { mode: 'official_with_shadow_advisory', recommendation: 'workflow_fallback' },
    next_step: featureReady ? 'train_candidate_model' : dataImported ? 'build_feature_store' : 'refresh_data',
    warning,
    fallback_source: 'feature-summary-and-refresh-status',
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

  try {
    const workflow = await fetchBackendJson(
      apiUrl,
      '/admin/workflow-status',
      serverAdminKey,
      workflowAttemptTimeoutMs,
    );
    if (workflow.status < 500) {
      return res.status(workflow.status).json(workflow.body);
    }
  } catch {
    // The fallback below uses real backend sources that are cheaper and already authoritative for the admin UI.
  }

  try {
    const [featureSummary, refreshStatus] = await Promise.all([
      fetchBackendJson(apiUrl, '/features/summary', serverAdminKey, 15000),
      fetchBackendJson(apiUrl, '/admin/refresh-status', serverAdminKey, 15000),
    ]);

    if (featureSummary.status >= 400) {
      return res.status(featureSummary.status).json(featureSummary.body);
    }

    const fallback = buildWorkflowFallback(
      featureSummary.body,
      refreshStatus.status < 400 ? refreshStatus.body : {},
      'Backend workflow-status timed out; workflow synthesized from /features/summary and /admin/refresh-status.',
    );

    return res.status(200).json(fallback);
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      return res.status(504).json({ detail: 'Backend workflow-status timed out' });
    }

    return res.status(500).json({
      detail: error instanceof Error ? error.message : 'Backend workflow-status proxy failed',
    });
  }
}
