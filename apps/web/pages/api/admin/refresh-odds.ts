import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).json({ detail: 'Method not allowed' });

  return proxyAdminRequest(req, res, {
    backendPath: '/odds/refresh',
    method: 'POST',
    requireAdminKey: true,
    timeoutMs: 60000,
  });
}
