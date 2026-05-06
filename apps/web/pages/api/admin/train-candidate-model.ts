import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const modelType = typeof req.query.model_type === 'string' ? req.query.model_type : 'random_forest';
  const limit = typeof req.query.limit === 'string' ? req.query.limit : '5000';
  const bypassQualityGate =
    typeof req.query.bypass_quality_gate === 'string' ? req.query.bypass_quality_gate : 'false';

  return proxyBackendRequest(req, res, {
    backendPath:
      `/admin/train-candidate-model?model_type=${encodeURIComponent(modelType)}` +
      `&limit=${encodeURIComponent(limit)}` +
      `&bypass_quality_gate=${encodeURIComponent(bypassQualityGate)}`,
    method: 'POST',
    requireAdminKey: true,
    timeoutMs: 60000,
    timeoutDetail: 'Backend candidate training timed out',
  });
}
