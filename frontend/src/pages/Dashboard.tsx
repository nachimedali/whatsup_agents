import React, { useEffect, useState, useCallback } from 'react';
import { api, Task, Agent } from '../api/client';
import { useWebSocket } from '../hooks/useWebSocket';
import { formatDistanceToNow } from 'date-fns';
import { Activity, Bot, CheckCircle, XCircle, Clock, Loader } from 'lucide-react';

function statusBadge(status: string) {
  const map: Record<string, string> = {
    queued:     'badge bg-yellow-900/40 text-yellow-400',
    processing: 'badge bg-blue-900/40 text-blue-400',
    done:       'badge bg-green-900/40 text-green-400',
    failed:     'badge bg-red-900/40 text-red-400',
  };
  return map[status] || 'badge bg-gray-800 text-gray-400';
}

function statusIcon(status: string) {
  if (status === 'done')       return <CheckCircle size={14} className="text-green-400" />;
  if (status === 'failed')     return <XCircle size={14} className="text-red-400" />;
  if (status === 'processing') return <Loader size={14} className="text-blue-400 animate-spin" />;
  return <Clock size={14} className="text-yellow-400" />;
}

export default function Dashboard() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [logs, setLogs] = useState<{ level: string; text: string; ts: number }[]>([]);

  const load = useCallback(async () => {
    const [t, a] = await Promise.all([api.tasks.list({ limit: 30 }), api.agents.list()]);
    setTasks(t);
    setAgents(a);
  }, []);

  useEffect(() => { load(); }, [load]);

  useWebSocket((e) => {
    if (e.type === 'task_update') {
      setTasks(prev => {
        const idx = prev.findIndex(t => t.id === (e.task as Task).id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = e.task as Task;
          return next;
        }
        return [e.task as Task, ...prev].slice(0, 50);
      });
    }
    if (e.type === 'log') {
      setLogs(prev => [{ level: e.level, text: e.text, ts: Date.now() }, ...prev].slice(0, 100));
    }
  });

  const done  = tasks.filter(t => t.status === 'done').length;
  const failed = tasks.filter(t => t.status === 'failed').length;
  const active = tasks.filter(t => t.status === 'processing').length;

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-xl font-semibold text-white">Dashboard</h1>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Agents',     value: agents.length,  color: 'text-brand-400' },
          { label: 'Active',     value: active,          color: 'text-blue-400' },
          { label: 'Completed',  value: done,            color: 'text-green-400' },
          { label: 'Failed',     value: failed,          color: 'text-red-400' },
        ].map(s => (
          <div key={s.label} className="card">
            <div className={`text-3xl font-bold ${s.color}`}>{s.value}</div>
            <div className="text-sm text-gray-500 mt-1">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Task Feed */}
        <div className="card space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
            <Activity size={15} />
            Live Task Feed
          </div>
          {tasks.length === 0 && (
            <p className="text-gray-600 text-sm">No tasks yet. Send a message on WhatsApp to get started.</p>
          )}
          <div className="space-y-2 max-h-[420px] overflow-auto">
            {tasks.map(task => (
              <div key={task.id} className="bg-gray-800/60 rounded-lg p-3 space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {statusIcon(task.status)}
                    <span className="text-xs font-mono text-gray-400">@{task.agent_id}</span>
                    <span className={statusBadge(task.status)}>{task.status}</span>
                  </div>
                  <span className="text-xs text-gray-600">
                    {formatDistanceToNow(new Date(task.created_at), { addSuffix: true })}
                  </span>
                </div>
                <p className="text-xs text-gray-300 line-clamp-2">{task.raw_message}</p>
                {task.result && (
                  <p className="text-xs text-green-400/80 line-clamp-2">{task.result}</p>
                )}
                {task.error && (
                  <p className="text-xs text-red-400/80">{task.error}</p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Live Logs */}
        <div className="card space-y-3">
          <div className="flex items-center gap-2 text-sm font-medium text-gray-300">
            <Bot size={15} />
            System Logs
          </div>
          {logs.length === 0 && (
            <p className="text-gray-600 text-sm">Waiting for events…</p>
          )}
          <div className="space-y-1 max-h-[420px] overflow-auto font-mono text-xs">
            {logs.map((log, i) => (
              <div key={i} className="flex gap-2">
                <span className={
                  log.level === 'ERROR' ? 'text-red-400' :
                  log.level === 'WARN'  ? 'text-yellow-400' :
                  'text-gray-500'
                }>[{log.level}]</span>
                <span className="text-gray-300">{log.text}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
