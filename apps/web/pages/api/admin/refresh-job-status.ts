import type { NextApiRequest, NextApiResponse } from 'next';

const DEFAULT_API_URL = 'https://footiq-pro-production.up.railway.app';

function getApiUrl() {
  return (process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL).replace(/\/$/, '');
}

async function parseJsonSafely(response: Response) {
  const contentType = response.headers.get('content-type') ?? '';
  const text = await response.text();

  if (!contentType.includes('application/json')) {
    return { status: 'error', detail: text || 'Non JSON response from backend' };
  }

  try {
    return JSON.parse(text);
  } catch {
    return { status: 'error', detail: 'Invalid JSON response from backend' };
  }
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ status: 'error', detail: 'Method not allowed' });
  }

  const rawJobId = Array.isArray(req.query.job_id) ? req.query.job_id[0] : req.query.job_id;
  const query = rawJobId ? `?job_id=${encodeURIComponent(rawJobId)}` : '';

  try {
    const backendResponse = await fetch(`${getApiUrl()}/admin/refresh-job-status${query}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
    });
    const body = await parseJsonSafely(backendResponse);
    return res.status(backendResponse.status).json(body);
  } catch (error) {
    return res.status(502).json({
      status: 'error',
      detail: error instanceof Error ? error.message : 'Refresh job status proxy failed',
    });
  }
}
