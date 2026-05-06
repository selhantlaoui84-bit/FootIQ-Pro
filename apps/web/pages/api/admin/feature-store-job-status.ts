import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyAdminRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const jobId = typeof req.query.job_id === 'string' ? req.query.job_id : '';
  const backendPath = jobId
    ? `/admin/feature-store-job-status?job_id=${encodeURIComponent(jobId)}`
    : '/admin/feature-store-job-status';

  return proxyAdminRequest(req, res, {
    backendPath,
    method: 'GET',
    timeoutMs: 10000,
    requireAdminKey: true,
  });
}

