import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') return res.status(405).json({ detail: 'Method not allowed' });
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
  if (!apiUrl) return res.status(500).json({ detail: 'NEXT_PUBLIC_API_URL missing' });
  const params = new URLSearchParams();
  for (const key of ['match_id', 'market', 'selection']) {
    const value = req.query[key];
    if (typeof value === 'string') params.set(key, value);
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(`${apiUrl}/odds/prediction?${params.toString()}`, {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
    const body = await response.json();
    return res.status(response.status).json(body);
  } catch (error) {
    return res.status(504).json({ status: 'error', detail: error instanceof Error ? error.message : 'Odds unavailable' });
  } finally {
    clearTimeout(timeout);
  }
}
