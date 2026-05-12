import { useEffect, useState } from 'react';
import { ProtectedRoute } from '~/components/ProtectedRoute';
import { createUserBet, getUserBets, getUserBetSummary, settleUserBet } from '~/lib/api';
import type { UserBet, UserBetSummary } from '~/lib/mock-data';

const emptySummary: UserBetSummary = {
  status: 'ok',
  total_bets: 0,
  settled_bets: 0,
  pending_bets: 0,
  total_staked: 0,
  net_profit: null,
  roi: null,
  win_rate: null,
  average_odds: null,
  by_market: [],
  by_competition: [],
  insights: [],
};

export default function MyBetsPage() {
  const [bets, setBets] = useState<UserBet[]>([]);
  const [summary, setSummary] = useState<UserBetSummary>(emptySummary);
  const [statusFilter, setStatusFilter] = useState('all');
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({
    match_id: '',
    market: '1X2',
    selection: 'HOME_WIN',
    bookmaker: '',
    odds_decimal: '',
    stake: '',
    notes: '',
    manual: false,
  });

  async function reload() {
    const [betsResponse, summaryResponse] = await Promise.all([getUserBets(), getUserBetSummary()]);
    setBets(betsResponse.items ?? []);
    setSummary(summaryResponse);
  }

  useEffect(() => {
    reload().catch(() => setMessage('Impossible de charger vos paris pour le moment.'));
  }, []);

  const filtered = statusFilter === 'all' ? bets : bets.filter((bet) => bet.status === statusFilter);

  async function submitBet(event: React.FormEvent) {
    event.preventDefault();
    setMessage(null);
    const odds = Number(form.odds_decimal);
    const stake = Number(form.stake);
    if (!odds || odds <= 1 || !stake || stake <= 0) {
      setMessage('Cote réelle ou saisie manuelle explicite et mise positive requises.');
      return;
    }
    try {
      await createUserBet({
        match_id: form.match_id,
        market: form.market,
        selection: form.selection,
        bookmaker: form.bookmaker || 'Saisie utilisateur',
        odds_decimal: odds,
        odds_source: form.manual ? 'manual_user_input' : 'provider',
        stake,
        notes: form.notes,
        raw_context: { source: form.manual ? 'manual_user_input' : 'real_provider' },
        source: form.manual ? 'manual_user_input' : 'real_provider',
      } as any);
      setForm({ ...form, match_id: '', odds_decimal: '', stake: '', notes: '' });
      setMessage('Pari enregistré. Les résultats restent incertains et le risque doit rester maîtrisé.');
      await reload();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Création du pari impossible.');
    }
  }

  async function settle(id: string, status: 'won' | 'lost' | 'void') {
    await settleUserBet(id, { status });
    await reload();
  }

  return (
    <ProtectedRoute>
      <main className="pageShell">
        <section className="hero">
          <p className="eyebrow">Portefeuille personnel</p>
          <h1>Mes paris</h1>
          <p>Suivez vos mises, vos résultats et votre discipline. Les cotes doivent être réelles ou saisies manuellement par vous.</p>
        </section>

        {message && <section className="banner info">{message}</section>}

        <section className="compactDataGrid four">
          <div className="metric"><span>Paris</span><strong>{summary.total_bets}</strong></div>
          <div className="metric"><span>En cours</span><strong>{summary.pending_bets}</strong></div>
          <div className="metric"><span>Profit net</span><strong>{summary.net_profit == null ? 'Données insuffisantes' : `${summary.net_profit.toFixed(2)} €`}</strong></div>
          <div className="metric"><span>ROI</span><strong>{summary.roi == null ? 'Données insuffisantes' : `${(summary.roi * 100).toFixed(1)}%`}</strong></div>
        </section>

        <section className="sectionSplit">
          <form className="card formStack" onSubmit={submitBet}>
            <p className="eyebrow">Ajouter un pari</p>
            <h2>Enregistrer une cote réelle</h2>
            <label>Match<input value={form.match_id} onChange={(event) => setForm({ ...form, match_id: event.target.value })} placeholder="match_id" required /></label>
            <label>Marché<input value={form.market} onChange={(event) => setForm({ ...form, market: event.target.value })} required /></label>
            <label>Sélection<input value={form.selection} onChange={(event) => setForm({ ...form, selection: event.target.value })} required /></label>
            <label>Bookmaker<input value={form.bookmaker} onChange={(event) => setForm({ ...form, bookmaker: event.target.value })} placeholder="Bookmaker réel ou saisie utilisateur" /></label>
            <label>Cote réelle<input type="number" step="0.01" min="1.01" value={form.odds_decimal} onChange={(event) => setForm({ ...form, odds_decimal: event.target.value })} required /></label>
            <label>Mise<input type="number" step="0.01" min="0.01" value={form.stake} onChange={(event) => setForm({ ...form, stake: event.target.value })} required /></label>
            <label>Notes<input value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} /></label>
            <label className="checkboxRow"><input type="checkbox" checked={form.manual} onChange={(event) => setForm({ ...form, manual: event.target.checked })} /> Cote saisie manuellement par l’utilisateur</label>
            <div className="banner warning">Si aucune cote réelle n’est disponible, saisissez-la manuellement uniquement depuis votre bookmaker. FootIQ Pro n’invente aucune cote.</div>
            <button className="button" type="submit">Enregistrer le pari</button>
          </form>

          <section className="card">
            <p className="eyebrow">Historique</p>
            <h2>Paris utilisateur</h2>
            <div className="tabs">
              {['all', 'pending', 'won', 'lost', 'void', 'cancelled'].map((status) => (
                <button className={statusFilter === status ? 'active' : ''} key={status} onClick={() => setStatusFilter(status)} type="button">{status}</button>
              ))}
            </div>
            {filtered.length === 0 ? (
              <div className="emptyState">Commencez à suivre vos paris pour obtenir des conseils personnalisés.</div>
            ) : (
              <div className="metricTable">
                {filtered.map((bet) => (
                  <div className="metricTableRow bucketRow" key={bet.id}>
                    <span>{bet.match_id}<br /><small>{bet.market} - {bet.selection}</small></span>
                    <strong>{bet.odds_decimal}</strong>
                    <strong>{bet.stake} €</strong>
                    <span>{bet.status}</span>
                    {bet.status === 'pending' && (
                      <span className="inlineActions">
                        <button type="button" onClick={() => settle(bet.id, 'won')}>Won</button>
                        <button type="button" onClick={() => settle(bet.id, 'lost')}>Lost</button>
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </section>

        <section className="card">
          <p className="eyebrow">Assistant personnalisé</p>
          <h2>Retours intelligents</h2>
          {(summary.insights ?? []).length === 0 ? (
            <div className="emptyState">Données insuffisantes pour tirer une conclusion fiable.</div>
          ) : (
            <div className="dataList">{summary.insights?.map((item) => <span key={item}>{item}</span>)}</div>
          )}
        </section>
      </main>
    </ProtectedRoute>
  );
}
