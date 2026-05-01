import type { NextApiRequest, NextApiResponse } from "next";

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const API = process.env.NEXT_PUBLIC_API_URL;
  const r = await fetch(`${API}/health`);
  const data = await r.json();
  res.status(200).json(data);
}
