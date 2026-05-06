import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const rawLimit = Array.isArray(req.query.limit) ? req.query.limit[0] : req.query.limit;
  const rawForce = Array.isArray(req.query.force) ? req.query.force[0] : req.query.force;
  const limit = rawLimit ?? '500';
  const force = rawForce ?? 'false';

  return proxyBackendRequest(req, res, {
    backendPath: `/admin/build-feature-store?limit=${encodeURIComponent(limit)}&force=${encodeURIComponent(force)}`,
    method: 'POST',
    requireAdminKey: true,
    timeoutMs: 60000,
    timeoutDetail: 'Backend Feature Store build timed out',
  });
}
