import type { NextApiRequest, NextApiResponse } from 'next';

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') return res.status(405).json({ detail: 'Method not allowed' });
  if (!API_URL) return res.status(500).json({ detail: 'NEXT_PUBLIC_API_URL missing' });

  const userId = typeof req.headers['x-user-id'] === 'string' ? req.headers['x-user-id'] : 'local-user';
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(`${API_URL}/user-bets/summary`, {
      headers: { Accept: 'application/json', 'X-User-Id': userId },
      signal: controller.signal,
    });
    const body = await response.json();
    return res.status(response.status).json(body);
  } catch (error) {
    return res.status(504).json({ status: 'error', detail: error instanceof Error ? error.message : 'User betting summary unavailable' });
  } finally {
    clearTimeout(timeout);
  }
}
