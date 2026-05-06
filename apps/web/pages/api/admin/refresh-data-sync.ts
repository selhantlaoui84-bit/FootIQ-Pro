import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ status: 'error', detail: 'Method not allowed' });
  }

  return proxyAdminRequest(req, res, {
    backendPath: '/admin/refresh-data-sync',
    method: 'POST',
    timeoutMs: 60000,
    requireAdminKey: true,
  });
}

