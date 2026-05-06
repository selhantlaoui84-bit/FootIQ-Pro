import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ status: 'error', detail: 'Method not allowed' });
  }

  const limit = Array.isArray(req.query.limit) ? req.query.limit[0] : req.query.limit;
  const force = Array.isArray(req.query.force) ? req.query.force[0] : req.query.force;
  const view = Array.isArray(req.query.view) ? req.query.view[0] : req.query.view;

  const params = new URLSearchParams();
  if (limit) params.set('limit', limit);
  if (force) params.set('force', force);
  if (view) params.set('view', view);

  const query = params.toString();

  return proxyAdminRequest(req, res, {
    backendPath: `/admin/generate-shadow-predictions${query ? `?${query}` : ''}`,
    method: 'POST',
    timeoutMs: 60000,
    requireAdminKey: true,
  });
}

