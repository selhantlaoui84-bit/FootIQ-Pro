import type { NextApiRequest, NextApiResponse } from 'next';

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ||
  'https://footiq-pro-production.up.railway.app';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ status: 'error', detail: 'Method not allowed' });
  }

  const adminKey = process.env.ADMIN_API_KEY || process.env.NEXT_PUBLIC_ADMIN_API_KEY;

  if (!adminKey) {
    return res.status(500).json({
      status: 'error',
      detail: 'ADMIN_API_KEY is not configured on the web server',
    });
  }

  const rawLimit = Array.isArray(req.query.limit) ? req.query.limit[0] : req.query.limit;
  const rawForce = Array.isArray(req.query.force) ? req.query.force[0] : req.query.force;
  const rawView = Array.isArray(req.query.view) ? req.query.view[0] : req.query.view;

  const limit = rawLimit ?? '500';
  const force = rawForce ?? 'false';
  const view = rawView ?? 'upcoming';

  try {
    const response = await fetch(
      `${API_URL}/admin/generate-shadow-predictions?limit=${encodeURIComponent(limit)}&force=${encodeURIComponent(force)}&view=${encodeURIComponent(view)}`,
      {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'X-Admin-Key': adminKey,
        },
      },
    );

    const text = await response.text();
    let body: unknown;

    try {
      body = JSON.parse(text);
    } catch {
      body = { status: 'error', detail: text || 'Non JSON response from backend' };
    }

    return res.status(response.status).json(body);
  } catch (error) {
    return res.status(500).json({
      status: 'error',
      detail: error instanceof Error ? error.message : 'Shadow prediction proxy failed',
    });
  }
}
