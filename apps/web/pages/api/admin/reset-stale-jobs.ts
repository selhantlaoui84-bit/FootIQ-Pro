import type { NextApiRequest, NextApiResponse } from 'next';

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? '';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const adminApiKey = process.env.ADMIN_API_KEY;

  if (!adminApiKey) {
    return res.status(500).json({ detail: 'ADMIN_API_KEY missing on Vercel server environment' });
  }

  if (!API_URL) {
    return res.status(500).json({ detail: 'NEXT_PUBLIC_API_URL missing on Vercel environment' });
  }

  try {
    const force = req.query.force === 'true' ? '?force=true' : '';
    const response = await fetch(`${API_URL}/admin/reset-stale-jobs${force}`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Admin-Key': adminApiKey,
      },
    });
    const body = await response.json().catch(() => ({ detail: response.statusText }));

    return res.status(response.status).json(body);
  } catch (error) {
    return res.status(500).json({
      detail: error instanceof Error ? error.message : 'Reset stale jobs proxy failed',
    });
  }
}

