import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ status: 'error', detail: 'Method not allowed' });
  }

  const modelType = Array.isArray(req.query.model_type) ? req.query.model_type[0] : req.query.model_type;
  const limit = Array.isArray(req.query.limit) ? req.query.limit[0] : req.query.limit;
  const bypassQualityGate = Array.isArray(req.query.bypass_quality_gate)
    ? req.query.bypass_quality_gate[0]
    : req.query.bypass_quality_gate;

  const params = new URLSearchParams();
  if (modelType) params.set('model_type', modelType);
  if (limit) params.set('limit', limit);
  if (bypassQualityGate) params.set('bypass_quality_gate', bypassQualityGate);

  const query = params.toString();

  return proxyAdminRequest(req, res, {
    backendPath: `/admin/train-candidate-model${query ? `?${query}` : ''}`,
    method: 'POST',
    timeoutMs: 60000,
    requireAdminKey: true,
  });
}

