import React, { useEffect, useState } from 'react';
import { Users2, RefreshCw, ToggleLeft, ToggleRight, Trash2, Loader, Wifi, WifiOff } from 'lucide-react';

interface Group {
  id: string;
  group_id: string;
  group_name: string | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export default function GroupsPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);
  const [bridgeOk, setBridgeOk] = useState<boolean | null>(null);
  const [error, setError] = useState('');

  const load = async () => {
    try {
      const data = await req<Group[]>('GET', '/groups');
      setGroups(data);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const checkBridge = async () => {
    try {
      const res = await fetch('/api/groups/bridge-status');
      const data = await res.json();
      setBridgeOk(data.reachable && data.status === 'connected');
    } catch {
      setBridgeOk(false);
    }
  };

  useEffect(() => {
    load();
    checkBridge();
  }, []);

  const sync = async () => {
    setSyncing(true);
    setSyncResult(null);
    setError('');
    try {
      const data = await req<{ added: number; groups: Group[] }>('POST', '/groups/sync');
      setGroups(data.groups);
      setSyncResult(
        data.added > 0
          ? `Synced — ${data.added} new group(s) found. Enable the ones you want below.`
          : 'Synced — no new groups found.'
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSyncing(false);
    }
  };

  const toggle = async (group: Group) => {
    try {
      const endpoint = group.enabled
        ? `/groups/${encodeURIComponent(group.group_id)}/disable`
        : `/groups/${encodeURIComponent(group.group_id)}/enable`;
      const updated = await req<Group>('PATCH', endpoint);
      setGroups(prev => prev.map(g => g.group_id === updated.group_id ? updated : g));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const remove = async (group: Group) => {
    if (!confirm(`Remove group "${group.group_name || group.group_id}"?`)) return;
    try {
      await req('DELETE', `/groups/${encodeURIComponent(group.group_id)}`);
      setGroups(prev => prev.filter(g => g.group_id !== group.group_id));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const enabledCount = groups.filter(g => g.enabled).length;

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">WhatsApp Groups</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Choose which groups your agents listen and respond in.
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={sync}
          disabled={syncing || bridgeOk === false}
        >
          {syncing
            ? <><Loader size={14} className="animate-spin" /> Syncing…</>
            : <><RefreshCw size={14} /> Sync from WhatsApp</>
          }
        </button>
      </div>

      {/* Bridge status */}
      <div className={`flex items-center gap-3 rounded-xl px-4 py-3 border text-sm ${
        bridgeOk === true  ? 'bg-green-900/20 border-green-800 text-green-400' :
        bridgeOk === false ? 'bg-red-900/20 border-red-800 text-red-400' :
                             'bg-gray-800 border-gray-700 text-gray-500'
      }`}>
        {bridgeOk === true  ? <Wifi size={16} /> :
         bridgeOk === false ? <WifiOff size={16} /> :
                              <Loader size={16} className="animate-spin" />}
        <span>
          {bridgeOk === true  ? 'WhatsApp bridge connected — ready to sync groups.' :
           bridgeOk === false ? 'WhatsApp bridge not reachable. Start it with: cd whatsapp-bridge && npm start' :
                                'Checking bridge…'}
        </span>
        <button className="ml-auto text-xs underline opacity-70 hover:opacity-100" onClick={checkBridge}>
          Recheck
        </button>
      </div>

      {/* Feedback */}
      {syncResult && (
        <div className="bg-brand-600/10 border border-brand-600/30 rounded-xl px-4 py-3 text-sm text-brand-300">
          {syncResult}
        </div>
      )}
      {error && (
        <div className="bg-red-900/20 border border-red-800 rounded-xl px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* How it works */}
      <div className="card text-sm space-y-2 text-gray-400">
        <p className="font-medium text-gray-300">How this works</p>
        <ol className="space-y-1.5 list-decimal list-inside text-gray-500">
          <li>Create a WhatsApp group and add yourself.</li>
          <li>
            The bot number (the one you scanned the QR with) is already listening —
            click <strong className="text-gray-300">Sync from WhatsApp</strong> to discover groups.
          </li>
          <li>Enable the groups you want agents to respond in.</li>
          <li>
            In the group, send <code className="text-brand-400 bg-gray-800 px-1 rounded">@agentid your task</code>{' '}
            — only messages starting with <code className="text-brand-400 bg-gray-800 px-1 rounded">@</code> are processed.
          </li>
          <li>The agent replies directly into the group.</li>
        </ol>
      </div>

      {/* Groups list */}
      {groups.length === 0 ? (
        <div className="card text-center py-12">
          <Users2 size={40} className="mx-auto text-gray-700 mb-3" />
          <p className="text-gray-500">No groups synced yet.</p>
          <p className="text-gray-600 text-sm mt-1">
            Make sure the WhatsApp bridge is running, then click "Sync from WhatsApp".
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-sm text-gray-500">
            <span>{groups.length} group(s) · {enabledCount} enabled</span>
          </div>
          {groups.map(group => (
            <div
              key={group.group_id}
              className={`card flex items-center gap-4 transition-colors ${
                group.enabled ? 'border-gray-700' : 'opacity-60'
              }`}
            >
              {/* Icon */}
              <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                group.enabled ? 'bg-green-900/30' : 'bg-gray-800'
              }`}>
                <Users2 size={18} className={group.enabled ? 'text-green-400' : 'text-gray-600'} />
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="font-medium text-white text-sm">
                  {group.group_name || 'Unnamed Group'}
                </div>
                <div className="text-xs text-gray-600 font-mono truncate mt-0.5">
                  {group.group_id}
                </div>
              </div>

              {/* Status badge */}
              <div className={`badge ${
                group.enabled
                  ? 'bg-green-900/40 text-green-400'
                  : 'bg-gray-800 text-gray-500'
              }`}>
                {group.enabled ? 'active' : 'disabled'}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2">
                <button
                  className="btn-ghost"
                  onClick={() => toggle(group)}
                  title={group.enabled ? 'Disable' : 'Enable'}
                >
                  {group.enabled
                    ? <ToggleRight size={20} className="text-green-400" />
                    : <ToggleLeft size={20} className="text-gray-500" />
                  }
                </button>
                <button
                  className="btn-danger"
                  onClick={() => remove(group)}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Usage hint for enabled groups */}
      {enabledCount > 0 && (
        <div className="text-xs text-gray-600 bg-gray-800/40 rounded-lg p-3 space-y-1">
          <p className="text-gray-400 font-medium">Sending messages in an enabled group:</p>
          <p><code className="text-brand-400">@coder fix the signup bug</code> → routes to the <code>coder</code> agent</p>
          <p><code className="text-brand-400">@assistant list empty apartments next month</code> → routes to <code>assistant</code></p>
          <p><code className="text-brand-400">@devteam run a standup</code> → routes to the team leader of <code>devteam</code></p>
          <p className="text-gray-700 mt-1">Messages without an <code>@</code> prefix are ignored.</p>
        </div>
      )}
    </div>
  );
}
