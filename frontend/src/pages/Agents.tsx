import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, Agent, ProviderEntry } from '../api/client';
import { Plus, Bot, Pencil, Trash2, ChevronRight } from 'lucide-react';

const PROVIDER_ICONS: Record<string, string> = {
  anthropic: '🟠',
  openai:    '🟢',
  google:    '🔵',
};

// ── Provider + Model picker ───────────────────────────────────────────────────

function ProviderModelPicker({
  catalogue,
  provider,
  model,
  onChange,
}: {
  catalogue: Record<string, ProviderEntry>;
  provider: string;
  model: string;
  onChange: (provider: string, model: string) => void;
}) {
  const providerEntry = catalogue[provider];
  const models = providerEntry?.models ?? [];

  const handleProviderChange = (p: string) => {
    const firstModel = catalogue[p]?.models[0]?.id ?? '';
    onChange(p, firstModel);
  };

  return (
    <div className="grid grid-cols-2 gap-3">
      <div>
        <label className="label">Provider</label>
        <select
          className="input"
          value={provider}
          onChange={e => handleProviderChange(e.target.value)}
        >
          {Object.entries(catalogue).map(([key, val]) => (
            <option key={key} value={key}>
              {PROVIDER_ICONS[key] ?? '🤖'} {val.label}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="label">Model</label>
        <select
          className="input"
          value={model}
          onChange={e => onChange(provider, e.target.value)}
        >
          {models.map(m => (
            <option key={m.id} value={m.id}>{m.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}


// ── Create modal ──────────────────────────────────────────────────────────────

function CreateModal({
  catalogue,
  onClose,
  onCreated,
}: {
  catalogue: Record<string, ProviderEntry>;
  onClose: () => void;
  onCreated: () => void;
}) {
  const defaultProvider = 'anthropic';
  const defaultModel = catalogue[defaultProvider]?.models[0]?.id ?? '';

  const [form, setForm] = useState({
    id: '',
    name: '',
    provider: defaultProvider,
    model: defaultModel,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.agents.create(form);
      onCreated();
      onClose();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
      <div className="card w-full max-w-md">
        <h2 className="text-lg font-semibold text-white mb-5">Create Agent</h2>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="label">Agent ID <span className="text-gray-600">(slug, e.g. "coder")</span></label>
            <input
              className="input"
              placeholder="coder"
              value={form.id}
              onChange={e => setForm(f => ({ ...f, id: e.target.value.toLowerCase().replace(/\s+/g, '-') }))}
              required
            />
          </div>
          <div>
            <label className="label">Display Name</label>
            <input
              className="input"
              placeholder="Coder"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              required
            />
          </div>
          <ProviderModelPicker
            catalogue={catalogue}
            provider={form.provider}
            model={form.model}
            onChange={(provider, model) => setForm(f => ({ ...f, provider, model }))}
          />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="flex gap-3 pt-2">
            <button type="button" className="btn-ghost flex-1" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary flex-1" disabled={loading}>
              {loading ? 'Creating…' : 'Create Agent'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


// ── Inline model editor ───────────────────────────────────────────────────────

function ModelBadge({
  agent,
  catalogue,
  onUpdated,
}: {
  agent: Agent;
  catalogue: Record<string, ProviderEntry>;
  onUpdated: (a: Agent) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [provider, setProvider] = useState(agent.provider);
  const [model, setModel] = useState(agent.model);
  const [saving, setSaving] = useState(false);

  if (!editing) {
    const providerLabel = catalogue[agent.provider]?.label ?? agent.provider;
    const modelLabel = catalogue[agent.provider]?.models.find(m => m.id === agent.model)?.label ?? agent.model;
    return (
      <button
        className="text-sm text-gray-500 hover:text-gray-300 transition-colors text-left"
        onClick={() => setEditing(true)}
        title="Click to change model"
      >
        {PROVIDER_ICONS[agent.provider] ?? '🤖'} {providerLabel} · {modelLabel}
      </button>
    );
  }

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api.agents.update(agent.id, { provider, model });
      onUpdated(updated);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex items-end gap-2 flex-wrap">
      <div className="flex-1 min-w-0">
        <ProviderModelPicker
          catalogue={catalogue}
          provider={provider}
          model={model}
          onChange={(p, m) => { setProvider(p); setModel(m); }}
        />
      </div>
      <div className="flex gap-1 pb-0.5">
        <button className="btn-primary text-xs px-2 py-1" onClick={save} disabled={saving}>
          {saving ? '…' : 'Save'}
        </button>
        <button className="btn-ghost text-xs px-2 py-1" onClick={() => setEditing(false)}>
          Cancel
        </button>
      </div>
    </div>
  );
}


// ── Main page ─────────────────────────────────────────────────────────────────

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [catalogue, setCatalogue] = useState<Record<string, ProviderEntry>>({});
  const [showCreate, setShowCreate] = useState(false);

  const load = async () => {
    const [a, c] = await Promise.all([api.agents.list(), api.agents.catalogue()]);
    setAgents(a);
    setCatalogue(c);
  };

  useEffect(() => { load(); }, []);

  const remove = async (id: string) => {
    if (!confirm(`Delete agent "${id}"? This will also delete all its conversations.`)) return;
    await api.agents.delete(id);
    load();
  };

  const updateAgent = (updated: Agent) => {
    setAgents(prev => prev.map(a => a.id === updated.id ? updated : a));
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Agents</h1>
        <button className="btn-primary" onClick={() => setShowCreate(true)} disabled={Object.keys(catalogue).length === 0}>
          <Plus size={15} /> New Agent
        </button>
      </div>

      {agents.length === 0 && (
        <div className="card text-center py-12">
          <Bot size={40} className="mx-auto text-gray-700 mb-3" />
          <p className="text-gray-500">No agents yet. Create your first agent to get started.</p>
          <button className="btn-primary mt-4 mx-auto" onClick={() => setShowCreate(true)}>
            <Plus size={15} /> Create Agent
          </button>
        </div>
      )}

      <div className="grid gap-3">
        {agents.map(agent => (
          <div key={agent.id} className="card space-y-3 hover:border-gray-700 transition-colors">
            <div className="flex items-center gap-4">
              <div className="w-10 h-10 rounded-xl bg-brand-600/20 flex items-center justify-center flex-shrink-0 text-lg">
                {PROVIDER_ICONS[agent.provider] ?? '🤖'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-white">{agent.name}</span>
                  <span className="font-mono text-gray-500 text-sm">@{agent.id}</span>
                  {agent.team_id && (
                    <span className="badge bg-brand-900/40 text-brand-400">team: {agent.team_id}</span>
                  )}
                </div>
                {Object.keys(catalogue).length > 0 && (
                  <ModelBadge
                    agent={agent}
                    catalogue={catalogue}
                    onUpdated={updateAgent}
                  />
                )}
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <Link to={`/agents/${agent.id}`} className="btn-ghost">
                  <Pencil size={14} /> Edit Soul
                </Link>
                <button className="btn-danger" onClick={() => remove(agent.id)}>
                  <Trash2 size={14} />
                </button>
                <Link to={`/agents/${agent.id}`} className="btn-ghost">
                  <ChevronRight size={14} />
                </Link>
              </div>
            </div>
          </div>
        ))}
      </div>

      {showCreate && Object.keys(catalogue).length > 0 && (
        <CreateModal
          catalogue={catalogue}
          onClose={() => setShowCreate(false)}
          onCreated={load}
        />
      )}
    </div>
  );
}
