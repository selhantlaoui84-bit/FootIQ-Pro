import type { NextApiRequest, NextApiResponse } from 'next';

const DIAGNOSTIC_TIMEOUT_MS = 8_000;

type DiagnosticStatus =
  | { status: 'ok'; data: unknown }
  | { status: 'error'; error: string };

function getApiUrl() {
  return process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? '';
}

function getApiHost(apiUrl: string) {
  if (!apiUrl) return '';

  try {
    return new URL(apiUrl).host;
  } catch {
    return 'invalid-url';
  }
}

async function fetchJsonWithTimeout(url: string, init?: RequestInit): Promise<DiagnosticStatus> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DIAGNOSTIC_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...init?.headers,
      },
    });
    const contentType = response.headers.get('content-type') ?? '';
    const text = await response.text();
    const data = contentType.includes('application/json') ? JSON.parse(text) : { detail: text || response.statusText };

    if (!response.ok) {
      return { status: 'error', error: data?.detail ?? `HTTP ${response.status}` };
    }

    return { status: 'ok', data };
  } catch (error) {
    return {
      status: 'error',
      error:
        error instanceof Error && error.name === 'AbortError'
          ? 'Request timed out'
          : error instanceof Error
            ? error.message
            : 'Request failed',
    };
  } finally {
    clearTimeout(timeout);
  }
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ detail: 'Method not allowed' });
  }

  const apiUrl = getApiUrl();
  const adminApiKey = process.env.ADMIN_API_KEY;
  const cronSecret = process.env.CRON_SECRET;
  const base = {
    hasApiUrl: Boolean(apiUrl),
    apiUrlHost: getApiHost(apiUrl),
    hasAdminApiKey: Boolean(adminApiKey),
    hasCronSecret: Boolean(cronSecret),
    cronConfigured: Boolean(cronSecret),
  };

  if (!apiUrl) {
    return res.status(200).json({
      ...base,
      backendHealth: { status: 'error', error: 'NEXT_PUBLIC_API_URL missing on Vercel environment' },
      refreshStatus: { status: 'error', error: 'NEXT_PUBLIC_API_URL missing on Vercel environment' },
    });
  }

  const [backendHealth, refreshStatus] = await Promise.all([
    fetchJsonWithTimeout(`${apiUrl}/health`),
    fetchJsonWithTimeout(`${apiUrl}/admin/refresh-status`),
  ]);

  return res.status(200).json({
    ...base,
    backendHealth,
    refreshStatus,
  });
}

