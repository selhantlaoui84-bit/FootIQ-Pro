import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const rawLimit = Array.isArray(req.query.limit) ? req.query.limit[0] : req.query.limit;
  const limit = rawLimit ?? '1000';

  return proxyBackendRequest(req, res, {
    backendPath: `/features/quality-report?limit=${encodeURIComponent(limit)}`,
    method: 'GET',
    includeAdminKey: true,
    timeoutMs: 15000,
  });
}
