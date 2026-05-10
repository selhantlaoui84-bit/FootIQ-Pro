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

function fulfilledBody(result: PromiseSettledResult<{ status: number; body: JsonObject }>): JsonObject {
  return result.status === 'fulfilled' && result.value.status < 500 ? result.value.body : {};
}

function buildMonitoringFallback(
  modelVersions: JsonObject,
  feedback: JsonObject,
  calibration: JsonObject,
  featureSummary: JsonObject,
  shadowBacktesting: JsonObject = {},
): JsonObject {
  const productionModel = (modelVersions.current_production_model as JsonObject | undefined) ?? {};
  const candidateModel = candidateFrom(modelVersions);
  const alerts: string[] = [];
  const storage = String(modelVersions.storage ?? featureSummary.storage ?? 'unknown');
  const featureSnapshots = numberFrom(featureSummary.snapshots_count);
  const trainingRows = numberFrom(featureSummary.with_target_count);
  const shadowTotal = numberFrom(shadowBacktesting.shadow_predictions_total);
  const shadowEvaluable = numberFrom(shadowBacktesting.evaluable_predictions ?? shadowBacktesting.evaluated_matches);
  const shadowPending = numberFrom(shadowBacktesting.pending_predictions);

  if (storage !== 'postgresql') alerts.push('Registre model_versions non confirme en PostgreSQL.');
  if (!candidateModel.model_version) alerts.push('Aucun modele candidat enregistre.');
  if (featureSnapshots === 0 && trainingRows === 0) alerts.push('Feature Store vide ou non disponible.');

  let nextBestAction: JsonObject;
  if (!candidateModel.model_version) {
    nextBestAction = { label: 'Entrainer un modele candidat', href: '/admin' };
  } else if (shadowTotal === 0) {
    nextBestAction = { label: 'Generer les predictions shadow', href: '/admin' };
  } else if (shadowPending > 0 && shadowEvaluable === 0) {
    nextBestAction = { label: 'Attendre les resultats des matchs', href: '/admin' };
  } else if (shadowEvaluable < 30) {
    nextBestAction = { label: 'Continuer le shadow testing', href: '/admin' };
  } else {
    nextBestAction = { label: 'Revue manuelle de promotion', href: '/admin' };
  }

  return {
    status: alerts.length > 0 ? 'warning' : 'ok',
    storage,
    feedback_status: String(feedback.status ?? 'unknown'),
    calibration_status: String(calibration.status ?? 'unknown'),
    model_versions_status: String(modelVersions.status ?? 'unknown'),
    governance_status: candidateModel.model_version ? 'candidate_available' : 'no_candidate',
    feature_store_status: featureSnapshots > 0 || trainingRows > 0 ? 'ok' : 'empty',
    latest_feedback_at: feedback.generated_at ?? null,
    latest_calibration_version: calibration.calibration_version ?? null,
    model_versions_count: numberFrom(modelVersions.versions_count),
    production_model_version: productionModel.model_version ?? 'elo-poisson-calibrated-v1',
    latest_candidate_model_version: candidateModel.model_version ?? null,
    shadow_backtesting_status: shadowBacktesting.backtesting_status ?? shadowBacktesting.status ?? null,
    shadow_predictions_total: shadowTotal,
    shadow_evaluable_predictions: shadowEvaluable,
    latest_shadow_backtesting_at: shadowBacktesting.generated_at ?? null,
    governance_recommendation: shadowBacktesting.recommendation ?? null,
    alerts,
    next_best_action: nextBestAction,
    fallback_source: 'models-versions-learning-feedback-calibration-feature-summary',
  };
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const method = 'GET';
  const timeoutMs: 45000 = 45000;

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
    const [monitoring, modelVersions, feedback, calibration, featureSummary, shadowBacktesting] = await Promise.allSettled([
      fetchBackendJson(apiUrl, '/learning/monitoring', serverAdminKey, timeoutMs),
      fetchBackendJson(apiUrl, '/models/versions', serverAdminKey, 30000),
      fetchBackendJson(apiUrl, '/learning/feedback', serverAdminKey, 8000),
      fetchBackendJson(apiUrl, '/learning/calibration', serverAdminKey, 8000),
      fetchBackendJson(apiUrl, '/features/summary', serverAdminKey, 8000),
      fetchBackendJson(apiUrl, '/shadow/backtesting', serverAdminKey, 30000),
    ]);

    if (monitoring.status === 'fulfilled' && monitoring.value.status < 500) {
      return res.status(200).json(monitoring.value.body);
    }

    return res.status(200).json(
      buildMonitoringFallback(
        fulfilledBody(modelVersions),
        fulfilledBody(feedback),
        fulfilledBody(calibration),
        fulfilledBody(featureSummary),
        fulfilledBody(shadowBacktesting),
      ),
    );
  } catch (error) {
    return res.status(200).json({
      ...buildMonitoringFallback({}, {}, {}, {}),
      detail: error instanceof Error ? error.message : 'Learning monitoring synthesized with empty fallback.',
    });
  }
}
