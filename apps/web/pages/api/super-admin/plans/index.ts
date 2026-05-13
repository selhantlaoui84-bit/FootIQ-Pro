import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  return proxyBackendRequest(req, res, {
    backendPath: '/super-admin/plans',
    method: req.method === 'POST' ? 'POST' : 'GET',
    requireBearerToken: true,
    timeoutMs: 15000,
  });
}
