import type { NextApiRequest, NextApiResponse } from 'next';

const DEFAULT_API_URL = 'https://footiq-pro-production.up.railway.app';

function getApiUrl() {
  return (process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL).replace(/\/$/, '');
}

async function parseJsonSafely(response: Response) {
  const contentType = response.headers.get('content-type') ?? '';
  const text = await response.text();

  if (!contentType.includes('application/json')) {
    return { status: 'error', detail: text || 'Non JSON response from backend' };
  }

  try {
    return JSON.parse(text);
  } catch {
    return { status: 'error', detail: 'Invalid JSON response from backend' };
  }
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ status: 'error', detail: 'Method not allowed' });
  }

  const adminKey = process.env.ADMIN_API_KEY || process.env.NEXT_PUBLIC_ADMIN_API_KEY;

  if (!adminKey) {
    return res.status(500).json({
      status: 'error',
      detail: 'ADMIN_API_KEY is not configured on the web server',
    });
  }

  try {
    const backendResponse = await fetch(`${getApiUrl()}/admin/refresh-data`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'X-Admin-Key': adminKey,
      },
    });

    const body = await parseJsonSafely(backendResponse);

    return res.status(backendResponse.status).json(body);
  } catch (error) {
    return res.status(502).json({
      status: 'error',
      detail: error instanceof Error ? error.message : 'Refresh proxy failed',
    });
  }
}
