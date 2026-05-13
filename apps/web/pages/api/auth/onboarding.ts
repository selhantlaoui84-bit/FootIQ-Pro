import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  return proxyBackendRequest(req, res, {
    backendPath: '/auth/onboarding',
    method: 'POST',
    requireBearerToken: true,
    timeoutMs: 10000,
  });
}
