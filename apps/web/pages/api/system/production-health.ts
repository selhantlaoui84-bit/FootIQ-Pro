import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  return proxyBackendRequest(req, res, {
    backendPath: '/system/production-health',
    method: 'GET',
    timeoutMs: 10000,
    timeoutDetail: 'Production health request timed out.',
  });
}
