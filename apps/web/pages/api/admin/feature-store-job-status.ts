import type { NextApiRequest, NextApiResponse } from "next";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "https://footiq-pro-production.up.railway.app";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== "GET") {
    return res.status(405).json({
      status: "error",
      detail: "Method not allowed",
    });
  }

  const rawJobId = Array.isArray(req.query.job_id) ? req.query.job_id[0] : req.query.job_id;
  const query = rawJobId ? `?job_id=${encodeURIComponent(rawJobId)}` : "";

  try {
    const response = await fetch(`${API_URL}/admin/feature-store-job-status${query}`, {
      method: "GET",
      headers: { Accept: "application/json" },
    });
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
      detail: error instanceof Error ? error.message : "Feature Store job status proxy failed",
    });
  }
}
