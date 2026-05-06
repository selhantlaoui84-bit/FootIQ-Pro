import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  return proxyBackendRequest(req, res, {
    backendPath: '/dashboard/summary',
    method: 'GET',
    includeAdminKey: true,
    timeoutMs: 15000,
  });
}
