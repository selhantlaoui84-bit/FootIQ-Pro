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

  const modelType = typeof req.query.model_type === 'string' ? req.query.model_type : 'random_forest';
  const limit = typeof req.query.limit === 'string' ? req.query.limit : '5000';
  const bypassQualityGate =
    typeof req.query.bypass_quality_gate === 'string' ? req.query.bypass_quality_gate : 'false';

  const url =
    `${API_URL}/admin/train-candidate-model` +
    `?model_type=${encodeURIComponent(modelType)}` +
    `&limit=${encodeURIComponent(limit)}` +
    `&bypass_quality_gate=${encodeURIComponent(bypassQualityGate)}`;

  try {
    const response = await fetch(url, {
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
      detail: error instanceof Error ? error.message : 'Candidate training proxy failed',
    });
  }
}