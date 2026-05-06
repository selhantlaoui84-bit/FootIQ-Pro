import type { NextApiRequest, NextApiResponse } from 'next';

type ProxyRequestOptions = {
  backendPath: string;
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  timeoutMs?: number;
  requireAdminKey?: boolean;
  timeoutMessage?: string;
};

async function proxyRequest(
  req: NextApiRequest,
  res: NextApiResponse,
  options: ProxyRequestOptions,
) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');

  if (!apiUrl) {
    return res.status(500).json({
      status: 'error',
      detail: 'NEXT_PUBLIC_API_URL missing on Vercel environment',
    });
  }

  const adminKey = process.env.ADMIN_API_KEY;

  if (options.requireAdminKey && !adminKey) {
    return res.status(500).json({
      status: 'error',
      detail: 'ADMIN_API_KEY missing on Vercel server environment',
    });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), options.timeoutMs ?? 15000);

  try {
    const headers: Record<string, string> = {
      Accept: 'application/json',
    };

    if (options.requireAdminKey && adminKey) {
      headers['X-Admin-Key'] = adminKey;
    }

    const response = await fetch(`${apiUrl}${options.backendPath}`, {
      method: options.method ?? req.method ?? 'GET',
      signal: controller.signal,
      headers,
    });

    const text = await response.text();

    let body: unknown;
    try {
      body = JSON.parse(text);
    } catch {
      body = {
        status: response.ok ? 'ok' : 'error',
        detail: text || response.statusText,
      };
    }

    return res.status(response.status).json(body);
  } catch (error) {
    const isTimeout = error instanceof Error && error.name === 'AbortError';

    return res.status(isTimeout ? 504 : 500).json({
      status: 'error',
      detail: isTimeout
        ? options.timeoutMessage ?? 'Backend request timed out'
        : error instanceof Error
          ? error.message
          : 'Admin proxy request failed',
    });
  } finally {
    clearTimeout(timeout);
  }
}

export async function proxyAdminRequest(
  req: NextApiRequest,
  res: NextApiResponse,
  options: ProxyRequestOptions,
) {
  return proxyRequest(req, res, {
    ...options,
    requireAdminKey: options.requireAdminKey ?? true,
  });
}

export async function proxyBackendRequest(
  req: NextApiRequest,
  res: NextApiResponse,
  options: ProxyRequestOptions,
) {
  return proxyRequest(req, res, {
    ...options,
    requireAdminKey: options.requireAdminKey ?? true,
  });
}
