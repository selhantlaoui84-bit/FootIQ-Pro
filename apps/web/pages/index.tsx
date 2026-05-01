import { useEffect, useState } from "react";

type ApiState = {
  status: "checking" | "ok" | "error";
  message: string;
};

const API = process.env.NEXT_PUBLIC_API_URL;

export default function Home() {
  const [apiState, setApiState] = useState<ApiState>({
    status: "checking",
    message: "Checking API...",
  });

  useEffect(() => {
    if (!API) {
      setApiState({
        status: "error",
        message: "Missing NEXT_PUBLIC_API_URL",
      });
      return;
    }

    fetch(`${API}/health`)
      .then((r) => r.json())
      .then((data) =>
        setApiState({
          status: "ok",
          message: data.status,
        })
      )
      .catch((e) =>
        setApiState({
          status: "error",
          message: String(e),
        })
      );
  }, []);

  return (
    <main style={{ padding: 40, fontFamily: "system-ui" }}>
      <h1>FootIQ Pro</h1>
      <p>Status: {apiState.message}</p>
    </main>
  );
}