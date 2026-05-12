import type { NextApiRequest, NextApiResponse } from 'next';

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');

function userId(req: NextApiRequest) {
  return String(req.headers['x-user-id'] || req.cookies.footiq_user_id || 'local-user');
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).json({ status: 'error', detail: 'Method not allowed.' });
  if (!API_URL) return res.status(500).json({ status: 'error', detail: 'Backend API URL missing.' });
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${API_URL}/billing/create-portal-session`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'X-User-Id': userId(req) },
      signal: controller.signal,
    });
    const body = await response.json().catch(() => null);
    return res.status(response.status).json(body ?? { status: 'error', detail: 'Portal response was empty.' });
  } catch (error) {
    return res.status(502).json({ status: 'error', detail: error instanceof Error ? error.message : 'Portal proxy failed.' });
  } finally {
    clearTimeout(timeout);
  }
}
