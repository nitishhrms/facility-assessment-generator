import { useEffect, useRef, useState } from 'react';

// Healthcare RAG assistant tab. Streams answers from the FastAPI backend (POST
// /api/chat -> SSE) and shows the pipeline's "route trace" so you can see which tier
// answered (warehouse SQL / PubMed RAG / web search) and the retrieval similarity.

// Dev uses the Vite proxy (/api/chat -> :8000). In production, set VITE_CHAT_API_URL
// to a hosted backend (e.g. an HF Space) to point the deployed UI at it.
const CHAT_URL = import.meta.env.VITE_CHAT_API_URL || '/api/chat';

let _id = 0;
const nextId = () => `m${++_id}`;

// Tier -> human label + chip colors (matches the app's Tailwind palette).
const TIER_BADGE = {
  T1: { label: 'SQL · warehouse', cls: 'bg-sky-50 text-sky-700' },
  T2: { label: 'RAG · PubMed', cls: 'bg-emerald-50 text-emerald-700' },
  T3: { label: 'Web search', cls: 'bg-violet-50 text-violet-700' },
  blocked: { label: 'Blocked', cls: 'bg-red-50 text-red-700' },
  out_of_domain: { label: 'Out of scope', cls: 'bg-amber-50 text-amber-700' },
};

const SUGGESTIONS = [
  'What is the overall rating for facility 015009?',
  'What role do mitochondria play in programmed cell death?',
  'What are the latest 2025 guidelines for sepsis treatment?',
];

export default function ChatPanel() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages]);

  // Merge fields into the assistant message with the given id.
  function patch(id, fields) {
    setMessages((ms) => ms.map((m) => (m.id === id ? { ...m, ...fields } : m)));
  }

  async function send(text) {
    const q = (text ?? input).trim();
    if (!q || streaming) return;
    setInput('');

    const botId = nextId();
    setMessages((ms) => [
      ...ms,
      { id: nextId(), role: 'user', text: q },
      { id: botId, role: 'assistant', text: '', trace: null, tier: null, citations: [], pending: true },
    ]);
    setStreaming(true);

    try {
      const res = await fetch(CHAT_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: q }),
      });
      if (!res.ok || !res.body) throw new Error(`Backend error (${res.status})`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let sep;
        while ((sep = buffer.indexOf('\n\n')) >= 0) {
          const frame = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          const line = frame.split('\n').find((l) => l.startsWith('data:'));
          if (!line) continue;
          applyEvent(botId, JSON.parse(line.slice(5).trim()));
        }
      }
    } catch (err) {
      patch(botId, { text: `⚠ ${err.message || 'Request failed.'} Is the backend running on :8000?`, tier: 'blocked' });
    } finally {
      patch(botId, { pending: false });
      setStreaming(false);
    }
  }

  function applyEvent(botId, ev) {
    if (ev.type === 'trace') {
      patch(botId, { trace: ev.trace, tier: ev.trace?.router?.tier ?? null });
    } else if (ev.type === 'delta') {
      setMessages((ms) => ms.map((m) => (m.id === botId ? { ...m, text: m.text + ev.text } : m)));
    } else if (ev.type === 'final') {
      patch(botId, {
        text: ev.answer || '',
        tier: ev.tier ?? null,
        citations: ev.citations || [],
      });
    }
  }

  return (
    <section className="card flex h-[32rem] flex-col p-0">
      <header className="border-b border-neutral-200 px-5 py-3">
        <h2 className="text-lg font-semibold">Healthcare Assistant</h2>
        <p className="text-xs text-subtle">
          Facility data, PubMed evidence, and web fallback — gated and grounded, with its routing shown.
        </p>
      </header>

      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center text-subtle">
            <p className="text-sm">Ask about a facility, a medical topic, or current guidelines.</p>
            <div className="flex flex-col gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="rounded-full border border-neutral-200 px-3 py-1.5 text-xs text-ink hover:border-accent hover:text-accent"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((m) => <Message key={m.id} m={m} />)
        )}
      </div>

      <form
        className="flex items-center gap-3 border-t border-neutral-200 px-5 py-3"
        onSubmit={(e) => {
          e.preventDefault();
          send();
        }}
      >
        <input
          className="field-input flex-1"
          placeholder="Ask a question…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={streaming}
          aria-label="Chat message"
        />
        <button className="btn-primary px-5" type="submit" disabled={streaming || !input.trim()}>
          {streaming ? '…' : 'Send'}
        </button>
      </form>
    </section>
  );
}

function Message({ m }) {
  if (m.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-sm bg-accent px-4 py-2 text-sm text-white">
          {m.text}
        </div>
      </div>
    );
  }

  const badge = m.tier && TIER_BADGE[m.tier];
  const sim = m.trace?.router?.top_similarity;

  return (
    <div className="flex flex-col items-start gap-1.5">
      {(badge || m.pending) && (
        <div className="flex items-center gap-2">
          {badge && (
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.cls}`}>{badge.label}</span>
          )}
          {typeof sim === 'number' && (
            <span className="text-xs text-subtle">similarity {sim.toFixed(3)}</span>
          )}
        </div>
      )}

      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-bl-sm bg-neutral-100 px-4 py-2 text-sm text-ink">
        {m.text || (m.pending ? <span className="text-subtle">thinking…</span> : '')}
      </div>

      {m.citations?.length > 0 && <Citations items={m.citations} />}
    </div>
  );
}

function Citations({ items }) {
  return (
    <div className="max-w-[85%] rounded-xl border border-neutral-200 bg-neutral-50 px-3 py-2">
      <div className="text-xs font-semibold uppercase tracking-wide text-subtle">Sources</div>
      <ul className="mt-1 space-y-0.5">
        {items.map((c, i) => (
          <li key={i} className="text-xs">
            <a
              href={c.source_url || c.url}
              target="_blank"
              rel="noreferrer"
              className="text-accent hover:underline"
            >
              {c.pmid ? `PMID ${c.pmid}${c.section ? ` (${c.section})` : ''}` : c.title || c.url}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
