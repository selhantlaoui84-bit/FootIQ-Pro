import type { NextApiRequest, NextApiResponse } from 'next';

const REFRESH_TIMEOUT_MS = 20_000;

function getApiUrl() {
  return process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? '';
}

async function parseBackendBody(response: Response) {
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
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const apiUrl = getApiUrl();
  const adminApiKey = process.env.ADMIN_API_KEY;

  if (!adminApiKey) {
    return res.status(500).json({ detail: 'ADMIN_API_KEY missing on Vercel server environment' });
  }

  if (!apiUrl) {
    return res.status(500).json({ detail: 'NEXT_PUBLIC_API_URL missing on Vercel environment' });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REFRESH_TIMEOUT_MS);

  try {
    const response = await fetch(`${apiUrl}/admin/refresh-data`, {
      method: 'POST',
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'X-Admin-Key': adminApiKey,
      },
    });

    const body = await parseBackendBody(response);
    const responseContentType = response.headers.get('content-type');

    if (responseContentType) {
      res.setHeader('Content-Type', responseContentType);
    }

    return res.status(response.status).json(body);
  } catch (error) {
    const isTimeout = error instanceof Error && error.name === 'AbortError';

    return res.status(isTimeout ? 504 : 500).json({
      detail: isTimeout
        ? 'Backend refresh timed out after 20 seconds'
        : error instanceof Error
          ? error.message
          : 'Admin refresh proxy failed',
    });
  } finally {
    clearTimeout(timeout);
  }
}
