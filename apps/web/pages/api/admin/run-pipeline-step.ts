import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  return proxyAdminRequest(req, res, {
    backendPath: '/pipeline/run-step',
    method: 'POST',
    requireAdminKey: true,
    timeoutMs: 60000,
    timeoutDetail: 'Backend pipeline step timed out after 60000 ms.',
  });
}
