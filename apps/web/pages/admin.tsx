import { useState } from "react";

export default function Admin() {
  const [result, setResult] = useState<string>("Aucune action lancée.");

  async function refreshData() {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL;

      if (!apiUrl) {
        setResult("NEXT_PUBLIC_API_URL manquant.");
        return;
      }

      const response = await fetch(`${apiUrl}/admin/refresh-data`, {
        method: "POST",
      });

      const data = await response.json();

      setResult(JSON.stringify(data, null, 2));
    } catch (error) {
      setResult(String(error));
    }
  }

  return (
    <main className="page-shell">
      <section className="hero">
        <div className="hero-badge">Administration</div>
        <h1>Admin FootIQ Pro</h1>
        <p className="hero-subtitle">
          Lance une mise à jour des données et vérifie la connexion backend.
        </p>

        <div className="hero-actions">
          <button className="btn btn-primary" onClick={refreshData}>
            Refresh data
          </button>
        </div>

        <pre className="glass-card" style={{ marginTop: 24, whiteSpace: "pre-wrap" }}>
          {result}
        </pre>
      </section>
    </main>
  );
}
