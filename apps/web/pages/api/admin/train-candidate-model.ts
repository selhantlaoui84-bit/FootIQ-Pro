import type { NextApiRequest, NextApiResponse } from "next";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "https://footiq-pro-production.up.railway.app";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "POST") {
    return res.status(405).json({
      status: "error",
      detail: "Method not allowed",
    });
  }

  const adminKey = process.env.ADMIN_API_KEY || process.env.NEXT_PUBLIC_ADMIN_API_KEY;

  if (!adminKey) {
    return res.status(500).json({
      status: "error",
      detail: "ADMIN_API_KEY is not configured on the web server",
    });
  }

  const rawModelType = Array.isArray(req.query.model_type) ? req.query.model_type[0] : req.query.model_type;
  const rawLimit = Array.isArray(req.query.limit) ? req.query.limit[0] : req.query.limit;
  const rawBypass = Array.isArray(req.query.bypass_quality_gate) ? req.query.bypass_quality_gate[0] : req.query.bypass_quality_gate;
  const modelType = rawModelType ?? "random_forest";
  const limit = rawLimit ?? "5000";
  const bypass = rawBypass ?? "false";

  try {
    const response = await fetch(
      `${API_URL}/admin/train-candidate-model?model_type=${encodeURIComponent(modelType)}&limit=${encodeURIComponent(limit)}&bypass_quality_gate=${encodeURIComponent(bypass)}`,
      {
        method: "POST",
        headers: {
          Accept: "application/json",
          "X-Admin-Key": adminKey,
        },
      }
    );

    const text = await response.text();
    let body: unknown;

    try {
      body = JSON.parse(text);
    } catch {
      body = {
        status: "error",
        detail: text || "Non JSON response from backend",
      };
    }

    return res.status(response.status).json(body);
  } catch (error) {
    return res.status(500).json({
      status: "error",
      detail: error instanceof Error ? error.message : "Candidate training proxy failed",
    });
  }
}
