import React, { useEffect, useState, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, Agent, Task } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';
import { ArrowLeft, Save, Send, Loader } from 'lucide-react';
import ResourcesPanel from '../components/ResourcesPanel';

function SoulEditor({ agent, onSaved }: { agent: Agent; onSaved: (a: Agent) => void }) {
  const [soul, setSoul] = useState(agent.soul);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api.agents.updateSoul(agent.id, soul);
      onSaved(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="card flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h2 className="font-medium text-white">Soul</h2>
          <p className="text-xs text-gray-500 mt-0.5">System prompt — defines who this agent is.</p>
        </div>
        <button className="btn-primary" onClick={save} disabled={saving}>
          {saving ? <Loader size={14} className="animate-spin" /> : <Save size={14} />}
          {saved ? 'Saved!' : 'Save Soul'}
        </button>
      </div>
      <textarea
        className="flex-1 input font-mono text-xs resize-none min-h-[360px]"
        value={soul}
        onChange={e => setSoul(e.target.value)}
        spellCheck={false}
        placeholder="Define this agent's personality, expertise, and working principles..."
      />
    </div>
  );
}

function ChatPanel({ agent }: { agent: Agent }) {
  const [messages, setMessages] = useState<{ role: string; content: string; pending?: boolean }[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [pendingTaskId, setPendingTaskId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useWebSocket(useCallback((e) => {
    if (e.type === 'task_update') {
      const task = e.task as Task;
      if (task.id === pendingTaskId && (task.status === 'done' || task.status === 'failed')) {
        setMessages(prev => {
          const next = prev.filter(m => !m.pending);
          if (task.result) next.push({ role: 'assistant', content: task.result });
          if (task.error) next.push({ role: 'assistant', content: `⚠️ Error: ${task.error}` });
          return next;
        });
        setPendingTaskId(null);
        setSending(false);
      }
    }
  }, [pendingTaskId]));

  const send = async () => {
    const msg = input.trim();
    if (!msg || sending) return;
    setInput('');
    setSending(true);
    setMessages(prev => [
      ...prev,
      { role: 'user', content: msg },
      { role: 'assistant', content: '…', pending: true },
    ]);
    try {
      const res = await api.messages.chat(agent.id, msg);
      setPendingTaskId(res.task_id);
    } catch (err) {
      setMessages(prev => {
        const next = prev.filter(m => !m.pending);
        next.push({ role: 'assistant', content: `⚠️ ${(err as Error).message}` });
        return next;
      });
      setSending(false);
    }
  };

  return (
    <div className="card flex flex-col h-full">
      <h2 className="font-medium text-white mb-3">Chat with {agent.name}</h2>
      <div className="flex-1 overflow-auto space-y-3 min-h-[360px] max-h-[360px] pr-1">
        {messages.length === 0 && (
          <p className="text-gray-600 text-sm text-center mt-10">
            Start a conversation — if this agent has resources, it will use them automatically.
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
              msg.role === 'user'
                ? 'bg-brand-600 text-white'
                : msg.pending
                  ? 'bg-gray-800 text-gray-400 animate-pulse'
                  : 'bg-gray-800 text-gray-100'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="flex gap-2 mt-3 pt-3 border-t border-gray-800">
        <input
          className="input flex-1"
          placeholder={`Message ${agent.name}…`}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          disabled={sending}
        />
        <button className="btn-primary" onClick={send} disabled={!input.trim() || sending}>
          {sending ? <Loader size={14} className="animate-spin" /> : <Send size={14} />}
        </button>
      </div>
    </div>
  );
}

type Tab = 'soul' | 'resources' | 'chat';

export default function AgentDetail() {
  const { id } = useParams<{ id: string }>();
  const [agent, setAgent] = useState<Agent | null>(null);
  const [tab, setTab] = useState<Tab>('soul');

  useEffect(() => {
    if (id) api.agents.get(id).then(setAgent).catch(() => {});
  }, [id]);

  if (!agent) {
    return <div className="p-6 text-gray-500">Loading…</div>;
  }

  const TABS: { key: Tab; label: string }[] = [
    { key: 'soul',      label: 'Soul' },
    { key: 'resources', label: 'Resources' },
    { key: 'chat',      label: 'Chat' },
  ];

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center gap-3">
        <Link to="/agents" className="btn-ghost">
          <ArrowLeft size={15} /> Agents
        </Link>
        <div>
          <h1 className="text-xl font-semibold text-white">{agent.name}</h1>
          <p className="text-sm text-gray-500 font-mono">@{agent.id} · {agent.provider} · {agent.model}</p>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 bg-gray-900 border border-gray-800 rounded-xl p-1 w-fit">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-1.5 rounded-lg text-sm transition-colors ${
              tab === key
                ? 'bg-brand-600 text-white font-medium'
                : 'text-gray-400 hover:text-gray-100'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div>
        {tab === 'soul'      && <SoulEditor agent={agent} onSaved={setAgent} />}
        {tab === 'resources' && <ResourcesPanel agentId={agent.id} />}
        {tab === 'chat'      && <ChatPanel agent={agent} />}
      </div>
    </div>
  );
}
