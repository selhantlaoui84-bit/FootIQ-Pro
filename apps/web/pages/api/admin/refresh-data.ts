import type { NextApiRequest, NextApiResponse } from 'next';

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'https://footiq-pro-production.up.railway.app';
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  if (!ADMIN_API_KEY) {
    return res.status(500).json({ detail: 'ADMIN_API_KEY is missing on Vercel server environment.' });
  }

  try {
    const response = await fetch(`${API_URL}/admin/refresh-data`, {
      method: 'POST',
      headers: {
        'X-Admin-Key': ADMIN_API_KEY,
      },
    });

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
      detail: error instanceof Error ? error.message : 'Admin refresh proxy failed',
    });
  }
}