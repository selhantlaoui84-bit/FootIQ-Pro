import type { NextApiRequest, NextApiResponse } from 'next';
import { proxyBackendRequest } from '~/lib/server/admin-proxy';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const jobId = typeof req.query.job_id === 'string' ? req.query.job_id : '';
  const backendPath = jobId
    ? `/admin/refresh-job-status?job_id=${encodeURIComponent(jobId)}`
    : '/admin/refresh-job-status';

  return proxyBackendRequest(req, res, {
    backendPath,
    method: 'GET',
    requireAdminKey: true,
    timeoutMs: 10000,
    timeoutDetail: 'Backend refresh job status timed out',
  });
}
