import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  return proxyBackendRequest(req, res, {
    backendPath: '/admin/workflow-status',
    method: 'GET',
    requireAdminKey: true,
    timeoutMs: 45000,
  });
}
