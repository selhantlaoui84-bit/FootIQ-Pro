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

function fulfilledBody(result: PromiseSettledResult<{ status: number; body: JsonObject }>): JsonObject {
  return result.status === 'fulfilled' && result.value.status < 500 ? result.value.body : {};
}

function buildMonitoringFallback(
  modelVersions: JsonObject,
  feedback: JsonObject,
  calibration: JsonObject,
  featureSummary: JsonObject,
): JsonObject {
  const productionModel = (modelVersions.current_production_model as JsonObject | undefined) ?? {};
  const candidateModel = (modelVersions.latest_candidate_model as JsonObject | undefined) ?? {};
  const alerts: string[] = [];
  const storage = String(modelVersions.storage ?? featureSummary.storage ?? 'unknown');
  const featureSnapshots = numberFrom(featureSummary.snapshots_count);
  const trainingRows = numberFrom(featureSummary.with_target_count);

  if (storage !== 'postgresql') alerts.push('Registre model_versions non confirmé en PostgreSQL.');
  if (!candidateModel.model_version) alerts.push('Aucun modèle candidat enregistré.');
  if (featureSnapshots === 0 && trainingRows === 0) alerts.push('Feature Store vide ou non disponible.');

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
    alerts,
    next_best_action: candidateModel.model_version
      ? { label: 'Générer les prédictions shadow', href: '/admin' }
      : { label: 'Entraîner un modèle candidat', href: '/admin' },
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
  void timeoutMs;

  try {
    const [modelVersions, feedback, calibration, featureSummary] = await Promise.allSettled([
      fetchBackendJson(apiUrl, '/models/versions', serverAdminKey, 8000),
      fetchBackendJson(apiUrl, '/learning/feedback', serverAdminKey, 8000),
      fetchBackendJson(apiUrl, '/learning/calibration', serverAdminKey, 8000),
      fetchBackendJson(apiUrl, '/features/summary', serverAdminKey, 8000),
    ]);

    return res.status(200).json(
      buildMonitoringFallback(
        fulfilledBody(modelVersions),
        fulfilledBody(feedback),
        fulfilledBody(calibration),
        fulfilledBody(featureSummary),
      ),
    );
  } catch (error) {
    return res.status(200).json({
      ...buildMonitoringFallback({}, {}, {}, {}),
      detail: error instanceof Error ? error.message : 'Learning monitoring synthesized with empty fallback.',
    });
  }
}
