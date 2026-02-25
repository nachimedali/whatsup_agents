import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, Conversation } from '../api/client';
import { ArrowLeft, Bot, User } from 'lucide-react';
import { format } from 'date-fns';

export default function ConversationDetail() {
  const { id } = useParams<{ id: string }>();
  const [conv, setConv] = useState<Conversation | null>(null);

  useEffect(() => {
    if (id) api.conversations.get(id).then(setConv).catch(() => {});
  }, [id]);

  if (!conv) return <div className="p-6 text-gray-500">Loading…</div>;

  return (
    <div className="p-6 space-y-5 max-w-3xl">
      <div className="flex items-center gap-3">
        <Link to="/conversations" className="btn-ghost">
          <ArrowLeft size={15} /> Conversations
        </Link>
        <div>
          <h1 className="text-lg font-semibold text-white">
            {conv.sender_name || conv.sender_id}
          </h1>
          <p className="text-sm text-gray-500">
            @{conv.agent_id} · {conv.channel} · {conv.messages.length} messages
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {conv.messages.map(msg => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
              msg.role === 'user' ? 'bg-brand-600/20' : 'bg-gray-800'
            }`}>
              {msg.role === 'user'
                ? <User size={14} className="text-brand-400" />
                : <Bot size={14} className="text-gray-400" />
              }
            </div>
            <div className={`max-w-[80%] ${msg.role === 'user' ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
              <div className={`rounded-xl px-4 py-3 text-sm whitespace-pre-wrap ${
                msg.role === 'user' ? 'bg-brand-600 text-white' : 'bg-gray-800 text-gray-100'
              }`}>
                {msg.content}
              </div>
              <span className="text-xs text-gray-600 px-1">
                {format(new Date(msg.created_at), 'MMM d, HH:mm')}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
