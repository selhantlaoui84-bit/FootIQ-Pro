import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const id = String(req.query.id ?? '');
  return proxyBackendRequest(req, res, {
    backendPath: `/super-admin/plans/${encodeURIComponent(id)}`,
    method: 'PATCH',
    requireBearerToken: true,
    timeoutMs: 15000,
  });
}
