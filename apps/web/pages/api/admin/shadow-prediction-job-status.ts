import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const rawJobId = Array.isArray(req.query.job_id) ? req.query.job_id[0] : req.query.job_id;
  const query = rawJobId ? `?job_id=${encodeURIComponent(rawJobId)}` : '';

  return proxyAdminRequest(req, res, {
    backendPath: `/admin/shadow-prediction-job-status${query}`,
    method: 'GET',
    requireAdminKey: true,
    timeoutMs: 10000,
  });
}
