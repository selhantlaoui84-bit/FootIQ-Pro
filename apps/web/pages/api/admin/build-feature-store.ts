import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ status: 'error', detail: 'Method not allowed' });
  }

  const rawLimit = Array.isArray(req.query.limit) ? req.query.limit[0] : req.query.limit;
  const rawForce = Array.isArray(req.query.force) ? req.query.force[0] : req.query.force;

  const limit = encodeURIComponent(rawLimit ?? '500');
  const force = encodeURIComponent(rawForce ?? 'false');

  return proxyAdminRequest(req, res, {
    backendPath: `/admin/build-feature-store?limit=${limit}&force=${force}`,
    method: 'POST',
    timeoutMs: 60000,
    timeoutMessage: 'Backend Feature Store build timed out',
    requireAdminKey: true,
  });
}

