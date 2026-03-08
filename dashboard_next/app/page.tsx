'use client';

import { useState, useEffect, useCallback } from 'react';

// --- Types ---
interface Event {
  id: string;
  workflowId: string;
  workflowName: string;
  error: string;
  timestamp: string;
  status: 'Detected' | 'Resolved' | 'Explained' | 'Running';
  fixAttempted: boolean;
}

interface HealEvent {
  execution_id: string;
  workflow_name: string;
  error: string;
  heal_status: string;
  heal_message: string;
  timestamp: string;
}

// --- API Base URL ---
const API_BASE = typeof window !== 'undefined' && window.location.port === '3000'
  ? 'http://localhost:8000' // Dev mode (Next.js dev server)
  : '';                      // Production (same origin)

// --- Helper: localStorage ---
function loadCreds(): { url: string; key: string; geminiKey: string } {
  if (typeof window === 'undefined') return { url: '', key: '', geminiKey: '' };
  return {
    url: localStorage.getItem('heas_n8n_url') || '',
    key: localStorage.getItem('heas_n8n_key') || '',
    geminiKey: localStorage.getItem('heas_gemini_key') || '',
  };
}
function saveCreds(url: string, key: string, geminiKey: string) {
  localStorage.setItem('heas_n8n_url', url);
  localStorage.setItem('heas_n8n_key', key);
  localStorage.setItem('heas_gemini_key', geminiKey);
}
function clearCreds() {
  localStorage.removeItem('heas_n8n_url');
  localStorage.removeItem('heas_n8n_key');
  localStorage.removeItem('heas_gemini_key');
}

// --- Main Component ---
export default function Home() {
  // Connection state
  const [n8nUrl, setN8nUrl] = useState('');
  const [n8nKey, setN8nKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [connected, setConnected] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connectError, setConnectError] = useState('');

  // Data state
  const [events, setEvents] = useState<Event[]>([]);
  const [heals, setHeals] = useState<HealEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [healingId, setHealingId] = useState<string | null>(null);

  // Load saved credentials on mount
  useEffect(() => {
    const saved = loadCreds();
    if (saved.url && saved.key) {
      setN8nUrl(saved.url);
      setN8nKey(saved.key);
      setGeminiKey(saved.geminiKey);
      // Auto-connect with saved creds
      handleConnect(saved.url, saved.key, saved.geminiKey);
    }
  }, []);

  // Connect handler
  const handleConnect = async (url?: string, key?: string, gKey?: string) => {
    const connectUrl = url || n8nUrl;
    const connectKey = key || n8nKey;
    const connectGemini = gKey || geminiKey;

    if (!connectUrl || !connectKey) {
      setConnectError('n8n URL and API Key are required.');
      return;
    }

    setConnecting(true);
    setConnectError('');

    try {
      const res = await fetch(`${API_BASE}/api/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          n8nUrl: connectUrl,
          n8nApiKey: connectKey,
          geminiApiKey: connectGemini
        }),
      });

      if (res.ok) {
        saveCreds(connectUrl, connectKey, connectGemini);
        setConnected(true);
        setConnectError('');
        fetchEvents(connectUrl, connectKey);
      } else {
        const err = await res.json();
        setConnectError(err.detail || 'Connection failed.');
        setConnected(false);
      }
    } catch (e) {
      setConnectError('Could not reach the HEAS server. Is the backend running?');
      setConnected(false);
    } finally {
      setConnecting(false);
    }
  };

  // Disconnect handler
  const handleDisconnect = () => {
    clearCreds();
    setConnected(false);
    setEvents([]);
    setHeals([]);
  };

  // Fetch events
  const fetchEvents = useCallback(async (url?: string, key?: string) => {
    const fetchUrl = url || n8nUrl;
    const fetchKey = key || n8nKey;
    if (!fetchUrl || !fetchKey) return;

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ n8nUrl: fetchUrl, n8nApiKey: fetchKey }),
      });
      if (res.ok) {
        const data: Event[] = await res.json();
        const relevantEvents = data.filter(e =>
          e.workflowName !== 'Self-Healing: Error Monitor' &&
          e.status !== 'Resolved'
        );
        setEvents(relevantEvents);
      }

      const healRes = await fetch(`${API_BASE}/api/heals`);
      if (healRes.ok) {
        setHeals(await healRes.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [n8nUrl, n8nKey]);

  // Poll events when connected
  useEffect(() => {
    if (!connected) return;
    fetchEvents();
    const interval = setInterval(() => fetchEvents(), 5000);
    return () => clearInterval(interval);
  }, [connected, fetchEvents]);

  // Heal handler
  const handleHeal = async (event: Event) => {
    setHealingId(event.id);
    try {
      const res = await fetch(`${API_BASE}/api/heal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          executionId: event.id,
          workflowId: event.workflowId,
          error: event.error,
          n8nUrl,
          n8nApiKey: n8nKey,
          geminiApiKey: geminiKey,
        }),
      });

      const result = await res.json();
      setEvents(prev => prev.map(e => {
        if (e.id === event.id) {
          return {
            ...e,
            status: result.status === 'resolved' ? 'Resolved' : 'Explained',
            error: result.message,
          };
        }
        return e;
      }));
    } catch (err) {
      alert('Healing Failed: ' + err);
    } finally {
      setHealingId(null);
    }
  };

  // Stats
  const activeCount = events.length;
  const healedCount = heals.filter(h => h.heal_status === 'resolved').length;
  const totalIncidents = activeCount + heals.length;
  const recoveryRate = totalIncidents ? Math.round((healedCount / totalIncidents) * 100) : 100;

  return (
    <div className="min-h-screen p-6 md:p-8 font-sans selection:bg-indigo-500/30">

      {/* HEADER */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-cyan-400 tracking-tight">
            n8n // AGENTIC HEALER
          </h1>
          <p className="text-sm text-slate-400 mt-1 font-medium tracking-wide">
            AUTONOMOUS WORKFLOW RELIABILITY ENGINE
          </p>
        </div>
        {connected ? (
          <div className="flex items-center gap-3 px-4 py-2 bg-indigo-500/10 rounded-full border border-indigo-500/20 shadow-[0_0_15px_rgba(99,102,241,0.2)]">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <span className="text-indigo-300 text-xs font-bold tracking-wider">CONNECTED</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 px-4 py-2 bg-slate-800/50 rounded-full border border-slate-700/50">
            <span className="h-3 w-3 rounded-full bg-slate-600"></span>
            <span className="text-slate-500 text-xs font-bold tracking-wider">DISCONNECTED</span>
          </div>
        )}
      </header>

      {/* CONNECTION PANEL */}
      {!connected ? (
        <div className="backdrop-blur-xl bg-slate-900/60 rounded-2xl border border-indigo-500/20 p-8 mb-10 shadow-2xl shadow-indigo-500/5 max-w-2xl mx-auto">
          <div className="text-center mb-6">
            <div className="text-5xl mb-4">🔗</div>
            <h2 className="text-xl font-bold text-white mb-2">Connect Your n8n Instance</h2>
            <p className="text-slate-400 text-sm">
              Enter your n8n URL and API key to see the self-healing system in action.
              <br />
              <span className="text-slate-500 text-xs">Your credentials are stored in your browser only — never on our server.</span>
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">n8n Instance URL</label>
              <input
                type="url"
                placeholder="https://your-n8n.app.n8n.cloud"
                value={n8nUrl}
                onChange={(e) => setN8nUrl(e.target.value)}
                className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono text-sm transition-colors"
              />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">n8n API Key</label>
                <input
                  type="password"
                  placeholder="n8n_api_..."
                  value={n8nKey}
                  onChange={(e) => setN8nKey(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono text-sm transition-colors"
                />
              </div>
              <div>
                <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Gemini API Key (Optional)</label>
                <input
                  type="password"
                  placeholder="AIzaSy..."
                  value={geminiKey}
                  onChange={(e) => setGeminiKey(e.target.value)}
                  className="w-full bg-slate-800/80 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 font-mono text-sm transition-colors"
                />
              </div>
            </div>

            {connectError && (
              <div className="bg-rose-950/50 border border-rose-500/30 rounded-lg p-3 text-rose-300 text-sm font-mono">
                ⚠️ {connectError}
              </div>
            )}

            <button
              onClick={() => handleConnect()}
              disabled={connecting || !n8nUrl || !n8nKey}
              className="w-full bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-bold py-3 px-6 rounded-lg transition-all shadow-lg shadow-indigo-900/30 text-sm tracking-wide"
            >
              {connecting ? '⏳ CONNECTING...' : '🔌 CONNECT & SCAN'}
            </button>
          </div>

          <div className="mt-6 pt-6 border-t border-slate-800">
            <p className="text-slate-500 text-xs text-center">
              💡 <strong className="text-slate-400">Don&apos;t have n8n?</strong>{' '}
              <a href="https://n8n.io/cloud" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300 underline">
                Get a free n8n Cloud instance
              </a>{' '}
              and generate an API key in Settings → API.
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* CONNECTED BAR */}
          <div className="flex items-center justify-between bg-slate-900/40 rounded-xl border border-slate-800 p-4 mb-8">
            <div className="flex items-center gap-3 text-sm">
              <span className="text-slate-500">Connected to:</span>
              <code className="text-indigo-300 bg-indigo-500/10 px-2 py-1 rounded font-mono text-xs">{n8nUrl}</code>
            </div>
            <button
              onClick={handleDisconnect}
              className="text-xs text-slate-500 hover:text-rose-400 font-bold uppercase tracking-wider transition-colors"
            >
              Disconnect
            </button>
          </div>

          {/* STATS GRID */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-10">
            <StatCard label="Active Faults" value={activeCount} color="text-rose-500" bg="bg-rose-500/5 border-rose-500/20" />
            <StatCard label="Total Heals" value={healedCount} color="text-emerald-400" bg="bg-emerald-500/5 border-emerald-500/20" />
            <StatCard label="Success Rate" value={`${recoveryRate}%`} color="text-cyan-400" bg="bg-cyan-500/5 border-cyan-500/20" />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">

            {/* ACTIVE INCIDENTS */}
            <div className="backdrop-blur-xl bg-slate-900/40 rounded-2xl border border-white/5 overflow-hidden shadow-xl">
              <div className="px-6 py-5 border-b border-white/5 bg-white/5 flex justify-between items-center">
                <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <span className="text-xl">🔥</span> Active Incidents
                </h2>
                {activeCount > 0 && (
                  <span className="text-xs bg-rose-500 text-white px-2 py-0.5 rounded-full font-bold">
                    {activeCount}
                  </span>
                )}
              </div>

              {loading && events.length === 0 ? (
                <div className="p-12 text-center text-slate-500 animate-pulse">Scanning workflows...</div>
              ) : (
                <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
                  <table className="w-full text-left text-sm">
                    <tbody className="divide-y divide-white/5">
                      {events.length === 0 ? (
                        <tr>
                          <td className="p-12 text-center">
                            <div className="text-emerald-500/50 text-6xl mb-4">✓</div>
                            <p className="text-slate-400 font-medium">All Systems Nominal.</p>
                            <p className="text-slate-600 text-xs mt-1">No active workflow errors detected.</p>
                          </td>
                        </tr>
                      ) : (
                        events.map((event) => (
                          <tr key={event.id} className="hover:bg-white/5 transition-colors group">
                            <td className="px-6 py-5">
                              <div className="flex justify-between items-start mb-1">
                                <span className="text-white font-semibold group-hover:text-indigo-300 transition-colors">
                                  {event.workflowName}
                                </span>
                                <span className={`text-xs font-mono px-2 py-1 rounded border ${event.status === 'Resolved'
                                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                                  : event.status === 'Explained'
                                    ? 'text-blue-400 bg-blue-500/10 border-blue-500/20'
                                    : 'text-rose-400 bg-rose-500/10 border-rose-500/20'
                                  }`}>
                                  {event.status.toUpperCase()}
                                </span>
                              </div>
                              <div className="text-slate-400 text-xs mb-2 font-mono opacity-60">
                                ID: {event.id} • {new Date(event.timestamp).toLocaleTimeString()}
                              </div>
                              <div className="text-rose-300/80 text-sm bg-rose-950/30 p-3 rounded border border-rose-500/10 font-mono break-all">
                                {event.error}
                              </div>
                              {event.status === 'Detected' && (
                                <button
                                  onClick={() => handleHeal(event)}
                                  disabled={healingId === event.id}
                                  className="mt-3 bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 disabled:opacity-50 text-white px-4 py-2 rounded-lg text-xs font-bold transition-all shadow-lg shadow-indigo-900/20"
                                >
                                  {healingId === event.id ? '🔄 HEALING...' : '🤖 HEAL WITH AI'}
                                </button>
                              )}
                              {event.status === 'Resolved' && <span className="mt-2 inline-block text-emerald-500 text-xs font-bold">✅ FIXED</span>}
                              {event.status === 'Explained' && <span className="mt-2 inline-block text-blue-400 text-xs font-bold">📋 EXPLAINED</span>}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* AI NEURAL LOGS */}
            <div className="backdrop-blur-xl bg-slate-900/40 rounded-2xl border border-white/5 overflow-hidden shadow-xl flex flex-col h-[600px]">
              <div className="px-6 py-5 border-b border-white/5 bg-white/5 flex justify-between items-center">
                <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                  <span className="text-xl">🤖</span> AI Neural Logs
                </h2>
                <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse"></span>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-4 scroll-smooth">
                {heals.length === 0 ? (
                  <div className="text-center text-slate-600 mt-20">
                    <p>No autonomous interventions yet.</p>
                    <p className="text-xs mt-2 text-slate-700">Healing events will appear here when the AI fixes a workflow.</p>
                  </div>
                ) : (
                  heals.slice().reverse().map((heal, i) => (
                    <div key={i} className="bg-slate-900/50 rounded-xl border border-white/5 p-4 hover:border-indigo-500/30 transition-all">
                      <div className="flex justify-between items-center mb-3">
                        <div className="flex items-center gap-2">
                          <span className={`h-2 w-2 rounded-full shadow-[0_0_8px_currentColor] ${heal.heal_status === 'resolved' ? 'bg-emerald-400 text-emerald-400' : 'bg-rose-500 text-rose-500'}`}></span>
                          <span className={`text-xs font-bold uppercase tracking-wider ${heal.heal_status === 'resolved' ? 'text-emerald-400' : 'text-rose-400'}`}>
                            {heal.heal_status}
                          </span>
                        </div>
                        <span className="text-xs text-slate-500 font-mono">
                          {new Date(heal.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      <div className="mb-2">
                        <h4 className="text-indigo-300 font-medium text-sm">{heal.workflow_name}</h4>
                        <p className="text-slate-500 text-xs truncate mt-0.5 opacity-70">
                          Issue: {heal.error}
                        </p>
                      </div>
                      <div className={`text-sm p-3 rounded-lg border font-mono leading-relaxed shadow-inner ${heal.heal_status === 'resolved'
                        ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-100'
                        : 'bg-rose-950/40 border-rose-500/30 text-rose-100'
                        }`}>
                        {heal.heal_message.split('**').map((part, index) =>
                          index % 2 === 1 ? <strong key={index} className="text-white">{part}</strong> : part
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>

          {/* FOOTER */}
          <footer className="mt-12 text-center text-slate-600 text-xs border-t border-slate-800/50 pt-6">
            <p>
              Built by <strong className="text-slate-400">Marshal Mutisi</strong> •{' '}
              <a href="https://github.com/MarshalMutisi/N8N-self-annealing" target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300">
                View Source on GitHub
              </a>
            </p>
            <p className="mt-1">N8N Self-Annealing System — FastAPI + Next.js + Gemini AI</p>
          </footer>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, color, bg }: { label: string, value: string | number, color: string, bg: string }) {
  return (
    <div className={`p-6 rounded-2xl border backdrop-blur-md ${bg} transition-transform hover:scale-[1.02]`}>
      <h3 className="text-slate-400 text-xs font-bold uppercase tracking-wider mb-2">{label}</h3>
      <div className={`text-4xl font-black ${color} tracking-tight`}>
        {value}
      </div>
    </div>
  );
}
