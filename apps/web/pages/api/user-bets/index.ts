import type { NextApiRequest, NextApiResponse } from 'next';

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (!API_URL) return res.status(500).json({ detail: 'NEXT_PUBLIC_API_URL missing' });
  if (!['GET', 'POST'].includes(req.method ?? '')) return res.status(405).json({ detail: 'Method not allowed' });

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  const userId = typeof req.headers['x-user-id'] === 'string' ? req.headers['x-user-id'] : 'local-user';

  try {
    const response = await fetch(`${API_URL}/user-bets`, {
      method: req.method,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-User-Id': userId,
      },
      body: req.method === 'POST' ? JSON.stringify(req.body ?? {}) : undefined,
      signal: controller.signal,
    });
    const body = await response.json();
    return res.status(response.status).json(body);
  } catch (error) {
    return res.status(504).json({ status: 'error', detail: error instanceof Error ? error.message : 'User bets unavailable' });
  } finally {
    clearTimeout(timeout);
  }
}
