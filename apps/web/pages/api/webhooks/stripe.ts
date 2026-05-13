import type { NextApiRequest, NextApiResponse } from 'next';

export const config = {
  api: {
    bodyParser: false,
  },
};

const API_URL = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '');

async function readRawBody(req: NextApiRequest): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) {
    chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk));
  }
  return Buffer.concat(chunks);
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') return res.status(405).json({ status: 'error', detail: 'Method not allowed.' });
  if (!API_URL) return res.status(500).json({ status: 'error', detail: 'Backend API URL missing.' });

  const signature = req.headers['stripe-signature'];
  if (!signature || Array.isArray(signature)) {
    return res.status(400).json({ status: 'invalid_signature', detail: 'Stripe signature header missing.' });
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  try {
    const rawBody = await readRawBody(req);
    const response = await fetch(`${API_URL}/billing/webhook`, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
        'Stripe-Signature': signature,
      },
      body: rawBody.toString('utf8'),
      signal: controller.signal,
    });
    const body = await response.json().catch(() => ({ status: 'error', detail: 'Webhook response was empty.' }));
    return res.status(response.status).json(body);
  } catch (error) {
    return res.status(502).json({ status: 'error', detail: error instanceof Error ? error.message : 'Stripe webhook proxy failed.' });
  } finally {
    clearTimeout(timeout);
  }
}
