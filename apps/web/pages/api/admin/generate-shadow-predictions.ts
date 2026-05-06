import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const rawLimit = Array.isArray(req.query.limit) ? req.query.limit[0] : req.query.limit;
  const rawForce = Array.isArray(req.query.force) ? req.query.force[0] : req.query.force;
  const rawView = Array.isArray(req.query.view) ? req.query.view[0] : req.query.view;
  const limit = rawLimit ?? '500';
  const force = rawForce ?? 'false';
  const view = rawView ?? 'upcoming';

  return proxyBackendRequest(req, res, {
    backendPath: `/admin/generate-shadow-predictions?limit=${encodeURIComponent(limit)}&force=${encodeURIComponent(force)}&view=${encodeURIComponent(view)}`,
    method: 'POST',
    requireAdminKey: true,
    timeoutMs: 60000,
    timeoutDetail: 'Backend shadow prediction generation timed out',
  });
}
