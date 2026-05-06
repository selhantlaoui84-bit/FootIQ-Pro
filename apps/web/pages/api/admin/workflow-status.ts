import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ status: 'error', detail: 'Method not allowed' });
  }

  return proxyAdminRequest(req, res, {
    backendPath: '/admin/workflow-status',
    method: 'GET',
    timeoutMs: 15000,
    requireAdminKey: true,
  });
}

