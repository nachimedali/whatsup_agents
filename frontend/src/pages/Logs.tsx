import React, { useState, useRef, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { Trash2, PauseCircle, PlayCircle } from 'lucide-react';

interface LogEntry {
  level: string;
  text: string;
  ts: number;
}

const levelColor: Record<string, string> = {
  ERROR: 'text-red-400',
  WARN:  'text-yellow-400',
  INFO:  'text-gray-400',
  DEBUG: 'text-gray-600',
};

export default function LogsPage() {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const pausedRef = useRef(paused);
  pausedRef.current = paused;

  useWebSocket((e) => {
    if (e.type === 'log' && !pausedRef.current) {
      setLogs(prev => [...prev, { level: e.level, text: e.text, ts: Date.now() }].slice(-500));
    }
  });

  useEffect(() => {
    if (!paused) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs, paused]);

  const filtered = filter
    ? logs.filter(l => l.text.toLowerCase().includes(filter.toLowerCase()) || l.level.includes(filter.toUpperCase()))
    : logs;

  return (
    <div className="p-6 space-y-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">System Logs</h1>
        <div className="flex gap-2">
          <input
            className="input w-48"
            placeholder="Filter logs…"
            value={filter}
            onChange={e => setFilter(e.target.value)}
          />
          <button className="btn-ghost" onClick={() => setPaused(p => !p)}>
            {paused
              ? <><PlayCircle size={15} className="text-green-400" /> Resume</>
              : <><PauseCircle size={15} /> Pause</>
            }
          </button>
          <button className="btn-ghost" onClick={() => setLogs([])}>
            <Trash2 size={15} /> Clear
          </button>
        </div>
      </div>

      <div className="card flex-1 font-mono text-xs overflow-auto min-h-0">
        {filtered.length === 0 && (
          <p className="text-gray-600 text-center mt-8">No logs yet. Start the system and send a message.</p>
        )}
        <div className="space-y-0.5">
          {filtered.map((log, i) => (
            <div key={i} className="flex gap-3 hover:bg-gray-800/40 px-2 py-0.5 rounded">
              <span className="text-gray-700 flex-shrink-0">
                {new Date(log.ts).toLocaleTimeString()}
              </span>
              <span className={`flex-shrink-0 w-12 ${levelColor[log.level] || 'text-gray-400'}`}>
                [{log.level}]
              </span>
              <span className="text-gray-300">{log.text}</span>
            </div>
          ))}
        </div>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
