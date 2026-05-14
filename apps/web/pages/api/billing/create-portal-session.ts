import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  return proxyBackendRequest(req, res, {
    backendPath: '/billing/create-portal-session',
    method: 'POST',
    requireBearerToken: true,
    timeoutMs: 20000,
    timeoutDetail: 'Stripe Portal request timed out.',
  });
}
