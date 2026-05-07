import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

function firstQueryValue(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ status: 'error', detail: 'Method not allowed' });
  }

  const rawModelType = firstQueryValue(req.query.model_type) ?? firstQueryValue(req.query.modelType);
  const rawLimit = firstQueryValue(req.query.limit);
  const rawBypassQualityGate = firstQueryValue(req.query.bypass_quality_gate) ?? firstQueryValue(req.query.bypassQualityGate);

  const modelType = encodeURIComponent(rawModelType ?? 'random_forest');
  const limit = encodeURIComponent(rawLimit ?? '500');
  const bypassQualityGate = encodeURIComponent(rawBypassQualityGate ?? 'false');

  return proxyAdminRequest(req, res, {
    backendPath:
      `/admin/train-candidate-model?model_type=${modelType}` +
      `&limit=${limit}` +
      `&bypass_quality_gate=${bypassQualityGate}`,
    method: 'POST',
    timeoutMs: 60000,
    requireAdminKey: true,
    timeoutDetail: 'Backend candidate training timed out',
  });
}
