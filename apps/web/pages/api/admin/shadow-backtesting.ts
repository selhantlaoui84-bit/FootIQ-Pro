import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const rawLimit = Array.isArray(req.query.limit) ? req.query.limit[0] : req.query.limit;
  const limit = rawLimit ?? '2000';

  return proxyBackendRequest(req, res, {
    backendPath: `/shadow/backtesting?limit=${encodeURIComponent(limit)}`,
    method: 'GET',
    requireAdminKey: true,
    timeoutMs: 60000,
    timeoutDetail: 'Backend shadow backtesting timed out',
  });
}
