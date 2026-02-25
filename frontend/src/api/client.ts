const BASE = '/api';

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
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

// ── Types ──────────────────────────────────────────────────────────────────

export interface Agent {
  id: string;
  name: string;
  provider: string;
  model: string;
  soul: string;
  team_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface ModelEntry { id: string; label: string; }
export interface ProviderEntry { label: string; models: ModelEntry[]; }

export interface Team {
  id: string;
  name: string;
  leader_agent_id: string | null;
  created_at: string;
  agents: Agent[];
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  agent_id: string;
  sender_id: string;
  sender_name: string | null;
  channel: string;
  created_at: string;
  updated_at: string;
  messages: Message[];
  message_count?: number;
}

export interface Task {
  id: string;
  agent_id: string;
  sender_id: string;
  channel: string;
  raw_message: string;
  status: 'queued' | 'processing' | 'done' | 'failed';
  result: string | null;
  error: string | null;
  parent_task_id: string | null;
  created_at: string;
  updated_at: string;
}

// ── Agents ─────────────────────────────────────────────────────────────────

export const api = {
  agents: {
    list: () => req<Agent[]>('GET', '/agents'),
    get: (id: string) => req<Agent>('GET', `/agents/${id}`),
    catalogue: () => req<Record<string, ProviderEntry>>('GET', '/agents/catalogue/models'),
    create: (d: { id: string; name: string; provider: string; model: string; soul?: string; team_id?: string }) =>
      req<Agent>('POST', '/agents', d),
    update: (id: string, d: Partial<Agent>) => req<Agent>('PATCH', `/agents/${id}`, d),
    updateSoul: (id: string, soul: string) => req<Agent>('PUT', `/agents/${id}/soul`, { soul }),
    delete: (id: string) => req<void>('DELETE', `/agents/${id}`),
  },

  teams: {
    list: () => req<Team[]>('GET', '/teams'),
    get: (id: string) => req<Team>('GET', `/teams/${id}`),
    create: (d: { id: string; name: string; leader_agent_id?: string }) =>
      req<Team>('POST', '/teams', d),
    update: (id: string, d: Partial<Team>) => req<Team>('PATCH', `/teams/${id}`, d),
    addAgent: (teamId: string, agentId: string) =>
      req<Team>('POST', `/teams/${teamId}/agents/${agentId}`),
    removeAgent: (teamId: string, agentId: string) =>
      req<Team>('DELETE', `/teams/${teamId}/agents/${agentId}`),
    delete: (id: string) => req<void>('DELETE', `/teams/${id}`),
  },

  conversations: {
    list: (params?: { agent_id?: string; channel?: string }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      return req<Conversation[]>('GET', `/conversations${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => req<Conversation>('GET', `/conversations/${id}`),
    delete: (id: string) => req<void>('DELETE', `/conversations/${id}`),
  },

  tasks: {
    list: (params?: { agent_id?: string; status?: string; limit?: number }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      return req<Task[]>('GET', `/tasks${qs ? `?${qs}` : ''}`);
    },
    get: (id: string) => req<Task>('GET', `/tasks/${id}`),
  },

  messages: {
    chat: (agent_id: string, message: string) =>
      req<{ task_id: string; agent_id: string; status: string }>('POST', '/messages/chat', {
        agent_id,
        message,
      }),
  },
};
