import type { NextApiRequest, NextApiResponse } from 'next';

const CRON_TIMEOUT_MS = 60_000;

function isAuthorizedCron(req: NextApiRequest, cronSecret: string) {
  const authorization = req.headers.authorization ?? '';
  const userAgent = String(req.headers['user-agent'] ?? '').toLowerCase();
  const vercelCron = req.headers['x-vercel-cron'] === '1' || userAgent.includes('vercel-cron');

  return authorization === `Bearer ${cronSecret}` || vercelCron;
}

async function parseBody(response: Response) {
  const contentType = response.headers.get('content-type') ?? '';
  const text = await response.text();

  if (contentType.includes('application/json')) {
    try {
      return JSON.parse(text);
    } catch {
      return { detail: text || 'Invalid JSON response from backend' };
    }
  }

  return { detail: text || response.statusText };
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST' && req.method !== 'GET') {
    res.setHeader('Allow', 'GET, POST');
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
  const adminApiKey = process.env.ADMIN_API_KEY;
  const cronSecret = process.env.CRON_SECRET;

  if (!cronSecret) {
    return res.status(500).json({ detail: 'CRON_SECRET missing on Vercel server environment' });
  }

  if (!isAuthorizedCron(req, cronSecret)) {
    return res.status(401).json({ detail: 'Invalid cron authorization' });
  }

  if (!apiUrl) {
    return res.status(500).json({ detail: 'NEXT_PUBLIC_API_URL missing on Vercel environment' });
  }

  if (!adminApiKey) {
    return res.status(500).json({ detail: 'ADMIN_API_KEY missing on Vercel server environment' });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), CRON_TIMEOUT_MS);

  try {
    const response = await fetch(`${apiUrl}/admin/cron/hourly-refresh`, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Admin-Key': adminApiKey,
      },
    });
    const body = await parseBody(response);

    return res.status(response.status).json(body);
  } catch (error) {
    const isTimeout = error instanceof Error && error.name === 'AbortError';
    return res.status(isTimeout ? 504 : 500).json({
      detail: isTimeout ? 'Backend cron timed out after 60 seconds' : error instanceof Error ? error.message : 'Cron proxy failed',
    });
  } finally {
    clearTimeout(timeout);
  }
}
