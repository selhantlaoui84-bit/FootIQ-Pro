import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const limit = typeof req.query.limit === 'string' ? req.query.limit : '100';
  return proxyAdminRequest(req, res, {
    backendPath: `/pipeline/jobs?limit=${encodeURIComponent(limit)}`,
    method: 'GET',
    requireAdminKey: true,
    timeoutMs: 45000,
    timeoutDetail: 'Backend pipeline jobs timed out after 45000 ms.',
  });
}
