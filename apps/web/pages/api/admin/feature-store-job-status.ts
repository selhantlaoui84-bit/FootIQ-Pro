import type { NextApiRequest, NextApiResponse } from 'next';

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://footiq-pro-production.up.railway.app';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const jobId = typeof req.query.job_id === 'string' ? req.query.job_id : '';
  const url = jobId
    ? `${API_URL}/admin/feature-store-job-status?job_id=${encodeURIComponent(jobId)}`
    : `${API_URL}/admin/feature-store-job-status`;

  try {
    const response = await fetch(url);
    const text = await response.text();

    let data: unknown;
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: text || response.statusText };
    }

    return res.status(response.status).json(data);
  } catch (error) {
    return res.status(500).json({
      detail: error instanceof Error ? error.message : 'Feature Store job status proxy failed',
    });
  }
}