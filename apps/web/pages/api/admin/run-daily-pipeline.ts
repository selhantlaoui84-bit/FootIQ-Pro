import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  return proxyAdminRequest(req, res, {
    backendPath: '/pipeline/run-daily',
    method: 'POST',
    requireAdminKey: true,
    timeoutMs: 60000,
    timeoutDetail: 'Backend daily pipeline timed out after 60000 ms.',
  });
}
