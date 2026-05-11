import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  return proxyAdminRequest(req, res, {
    backendPath: '/pipeline/status',
    method: 'GET',
    requireAdminKey: true,
    timeoutMs: 45000,
    timeoutDetail: 'Backend pipeline status timed out after 45000 ms.',
  });
}
