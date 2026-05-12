import type { NextApiRequest, NextApiResponse } from 'next';

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') return res.status(405).json({ detail: 'Method not allowed' });
  if (!API_URL) return res.status(500).json({ detail: 'NEXT_PUBLIC_API_URL missing' });

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(req.query)) {
    if (Array.isArray(value)) value.forEach((item) => params.append(key, item));
    else if (value != null) params.set(key, String(value));
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${API_URL}/value-bets${params.toString() ? `?${params.toString()}` : ''}`, {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
    const body = await response.json();
    return res.status(response.status).json(body);
  } catch (error) {
    return res.status(504).json({ status: 'error', detail: error instanceof Error ? error.message : 'Value bets unavailable' });
  } finally {
    clearTimeout(timeout);
  }
}
