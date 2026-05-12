import type { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') return res.status(405).json({ detail: 'Method not allowed' });
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
  const id = typeof req.query.id === 'string' ? req.query.id : '';
  if (!apiUrl) return res.status(500).json({ detail: 'NEXT_PUBLIC_API_URL missing' });
  if (!id) return res.status(400).json({ detail: 'Missing match id' });
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${apiUrl}/assistant/match/${encodeURIComponent(id)}`, {
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
    const body = await response.json();
    return res.status(response.status).json(body);
  } catch (error) {
    return res.status(504).json({ status: 'error', detail: error instanceof Error ? error.message : 'Assistant unavailable' });
  } finally {
    clearTimeout(timeout);
  }
}
