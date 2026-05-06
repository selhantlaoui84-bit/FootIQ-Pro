import type { NextApiRequest, NextApiResponse } from 'next';

type ProxyOptions = {
  backendPath: string;
  method?: 'GET' | 'POST';
  requireAdminKey?: boolean;
  timeoutMs?: number;
  timeoutDetail?: string;
};

type BackendBody = Record<string, unknown> | unknown[] | string | null;

function parseBackendBody(text: string, fallback: string): BackendBody {
  if (!text) return { detail: fallback };

  try {
    return JSON.parse(text) as BackendBody;
  } catch {
    return { detail: text };
  }
}

export async function proxyBackendRequest(
  req: NextApiRequest,
  res: NextApiResponse,
  options: ProxyOptions,
) {
  const method = options.method ?? 'GET';

  if (req.method !== method) {
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');
  const adminKey = process.env.ADMIN_API_KEY;

  if (!apiUrl) {
    return res.status(500).json({ detail: 'NEXT_PUBLIC_API_URL missing on Vercel environment' });
  }

  if (options.requireAdminKey && !adminKey) {
    return res.status(500).json({ detail: 'ADMIN_API_KEY missing on Vercel server environment' });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? 15000);
  const headers: Record<string, string> = { Accept: 'application/json' };

  if (options.requireAdminKey && adminKey) {
    headers['X-Admin-Key'] = adminKey;
  }

  try {
    const response = await fetch(`${apiUrl}${options.backendPath}`, {
      method,
      headers,
      signal: controller.signal,
    });
    const text = await response.text();
    const body = parseBackendBody(text, response.statusText || 'Backend response is empty');

    return res.status(response.status).json(body);
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      return res.status(504).json({ detail: options.timeoutDetail ?? 'Backend request timed out' });
    }

    return res.status(500).json({
      detail: error instanceof Error ? error.message : 'Backend proxy failed',
    });
  } finally {
    clearTimeout(timeout);
  }
}
