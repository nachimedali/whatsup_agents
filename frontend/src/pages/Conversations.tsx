import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, Conversation } from '../api/client';
import { MessageSquare, Trash2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const CHANNEL_COLORS: Record<string, string> = {
  whatsapp: 'bg-green-900/40 text-green-400',
  telegram: 'bg-blue-900/40 text-blue-400',
  discord:  'bg-purple-900/40 text-purple-400',
  dashboard:'bg-gray-800 text-gray-400',
};

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [filter, setFilter] = useState('');

  const load = async () => setConversations(await api.conversations.list());
  useEffect(() => { load(); }, []);

  const remove = async (id: string) => {
    if (!confirm('Delete this conversation?')) return;
    await api.conversations.delete(id);
    load();
  };

  const filtered = conversations.filter(c =>
    !filter ||
    c.agent_id.includes(filter) ||
    (c.sender_name || '').toLowerCase().includes(filter.toLowerCase()) ||
    c.sender_id.includes(filter)
  );

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Conversations</h1>
        <input
          className="input w-56"
          placeholder="Search by agent or sender…"
          value={filter}
          onChange={e => setFilter(e.target.value)}
        />
      </div>

      {filtered.length === 0 && (
        <div className="card text-center py-12">
          <MessageSquare size={40} className="mx-auto text-gray-700 mb-3" />
          <p className="text-gray-500">No conversations yet.</p>
        </div>
      )}

      <div className="space-y-2">
        {filtered.map(conv => (
          <div key={conv.id} className="card flex items-center gap-4 hover:border-gray-700 transition-colors">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-white">{conv.sender_name || conv.sender_id}</span>
                <span className={`badge ${CHANNEL_COLORS[conv.channel] || 'bg-gray-800 text-gray-400'}`}>
                  {conv.channel}
                </span>
                <span className="text-xs text-gray-500">→ @{conv.agent_id}</span>
              </div>
              <div className="text-xs text-gray-600 mt-0.5">
                {conv.message_count} messages · updated {formatDistanceToNow(new Date(conv.updated_at), { addSuffix: true })}
              </div>
            </div>
            <div className="flex gap-2">
              <Link to={`/conversations/${conv.id}`} className="btn-ghost text-xs">
                View
              </Link>
              <button className="btn-danger" onClick={() => remove(conv.id)}>
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
