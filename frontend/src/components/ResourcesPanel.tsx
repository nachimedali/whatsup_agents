import React, { useEffect, useState } from 'react';
import { Database, FolderGit2, Plus, Trash2, TestTube2, ChevronDown, ChevronRight, Loader } from 'lucide-react';

interface Resource {
  id: string;
  agent_id: string;
  name: string;
  kind: 'repository' | 'database';
  repo_path: string | null;
  repo_globs: string[];
  db_url: string | null;
  db_tables: string[];
  created_at: string;
  updated_at: string;
}

interface TestResult {
  ok: boolean;
  message: string;
  files?: string[];
  schema?: string;
}

// ── API helpers ──────────────────────────────────────────────────────────────

async function fetchResources(agentId: string): Promise<Resource[]> {
  const res = await fetch(`/api/agents/${agentId}/resources`);
  return res.json();
}

async function createResource(agentId: string, payload: Partial<Resource>): Promise<Resource> {
  const res = await fetch(`/api/agents/${agentId}/resources`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error((await res.json()).detail || res.statusText);
  return res.json();
}

async function deleteResource(agentId: string, resId: string): Promise<void> {
  await fetch(`/api/agents/${agentId}/resources/${resId}`, { method: 'DELETE' });
}

async function testResource(agentId: string, resId: string): Promise<TestResult> {
  const res = await fetch(`/api/agents/${agentId}/resources/${resId}/test`, { method: 'POST' });
  return res.json();
}


// ── Create modal ─────────────────────────────────────────────────────────────

function CreateResourceModal({
  agentId,
  onClose,
  onCreated,
}: {
  agentId: string;
  onClose: () => void;
  onCreated: () => void;
}) {
  const [kind, setKind] = useState<'repository' | 'database'>('repository');
  const [name, setName] = useState('');
  const [repoPath, setRepoPath] = useState('');
  const [repoGlobs, setRepoGlobs] = useState('');
  const [dbUrl, setDbUrl] = useState('');
  const [dbTables, setDbTables] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await createResource(agentId, {
        name,
        kind,
        repo_path: kind === 'repository' ? repoPath : undefined,
        repo_globs: kind === 'repository'
          ? repoGlobs.split('\n').map(s => s.trim()).filter(Boolean)
          : undefined,
        db_url: kind === 'database' ? dbUrl : undefined,
        db_tables: kind === 'database'
          ? dbTables.split('\n').map(s => s.trim()).filter(Boolean)
          : undefined,
      });
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
      <div className="card w-full max-w-lg">
        <h2 className="text-lg font-semibold text-white mb-5">Attach Resource</h2>
        <form onSubmit={submit} className="space-y-4">
          {/* Kind toggle */}
          <div className="flex gap-2">
            {(['repository', 'database'] as const).map(k => (
              <button
                key={k}
                type="button"
                onClick={() => setKind(k)}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm border transition-colors ${
                  kind === k
                    ? 'bg-brand-600/20 border-brand-500 text-brand-300'
                    : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200'
                }`}
              >
                {k === 'repository' ? <FolderGit2 size={15} /> : <Database size={15} />}
                {k}
              </button>
            ))}
          </div>

          <div>
            <label className="label">Resource Name</label>
            <input className="input" placeholder="e.g. Auth Repo" value={name}
              onChange={e => setName(e.target.value)} required />
          </div>

          {kind === 'repository' && (
            <>
              <div>
                <label className="label">Repository Path <span className="text-gray-600">(absolute path on the server)</span></label>
                <input className="input font-mono text-xs" placeholder="/home/user/projects/myapp"
                  value={repoPath} onChange={e => setRepoPath(e.target.value)} required />
              </div>
              <div>
                <label className="label">
                  Glob Patterns <span className="text-gray-600">(one per line — empty = entire repo)</span>
                </label>
                <textarea
                  className="input font-mono text-xs resize-none h-24"
                  placeholder={"src/auth/**\nsrc/routes/auth.ts\nREADME.md"}
                  value={repoGlobs}
                  onChange={e => setRepoGlobs(e.target.value)}
                />
                <p className="text-xs text-gray-600 mt-1">
                  Tip: be specific. Injecting 500 files wastes the context window.
                </p>
              </div>
            </>
          )}

          {kind === 'database' && (
            <>
              <div>
                <label className="label">Connection String</label>
                <input
                  className="input font-mono text-xs"
                  placeholder="sqlite:///./myapp.db  or  postgresql+psycopg2://user:pass@host/db"
                  value={dbUrl}
                  onChange={e => setDbUrl(e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="label">
                  Allowed Tables <span className="text-gray-600">(one per line — empty = all tables)</span>
                </label>
                <textarea
                  className="input font-mono text-xs resize-none h-24"
                  placeholder={"apartments\nbookings\ntenants"}
                  value={dbTables}
                  onChange={e => setDbTables(e.target.value)}
                />
                <p className="text-xs text-gray-600 mt-1">
                  Restricting tables prevents Claude from accessing sensitive data.
                </p>
              </div>
            </>
          )}

          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="flex gap-3 pt-2">
            <button type="button" className="btn-ghost flex-1" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary flex-1" disabled={loading}>
              {loading ? 'Attaching…' : 'Attach Resource'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}


// ── Resource card ─────────────────────────────────────────────────────────────

function ResourceCard({
  resource,
  onDelete,
}: {
  resource: Resource;
  onDelete: () => void;
}) {
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [testing, setTesting] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const runTest = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await testResource(resource.agent_id, resource.id);
      setTestResult(result);
      setExpanded(true);
    } finally {
      setTesting(false);
    }
  };

  const isRepo = resource.kind === 'repository';

  return (
    <div className="bg-gray-800/60 rounded-xl border border-gray-700 overflow-hidden">
      <div className="flex items-center gap-3 p-4">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
          isRepo ? 'bg-green-900/30' : 'bg-blue-900/30'
        }`}>
          {isRepo
            ? <FolderGit2 size={17} className="text-green-400" />
            : <Database size={17} className="text-blue-400" />
          }
        </div>

        <div className="flex-1 min-w-0">
          <div className="font-medium text-white text-sm">{resource.name}</div>
          <div className="text-xs text-gray-500 font-mono truncate">
            {isRepo ? resource.repo_path : resource.db_url}
          </div>
          {isRepo && resource.repo_globs.length > 0 && (
            <div className="text-xs text-gray-600 mt-0.5">
              Globs: {resource.repo_globs.join(', ')}
            </div>
          )}
          {!isRepo && resource.db_tables.length > 0 && (
            <div className="text-xs text-gray-600 mt-0.5">
              Tables: {resource.db_tables.join(', ')}
            </div>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            className="btn-ghost text-xs"
            onClick={runTest}
            disabled={testing}
          >
            {testing
              ? <Loader size={13} className="animate-spin" />
              : <TestTube2 size={13} />
            }
            Test
          </button>
          <button
            className="btn-danger"
            onClick={() => confirm(`Remove resource "${resource.name}"?`) && onDelete()}
          >
            <Trash2 size={13} />
          </button>
          {testResult && (
            <button className="btn-ghost" onClick={() => setExpanded(e => !e)}>
              {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>
          )}
        </div>
      </div>

      {/* Test results */}
      {testResult && expanded && (
        <div className={`px-4 pb-4 border-t ${testResult.ok ? 'border-green-900/40' : 'border-red-900/40'}`}>
          <div className={`mt-3 text-xs font-medium ${testResult.ok ? 'text-green-400' : 'text-red-400'}`}>
            {testResult.ok ? '✓' : '✗'} {testResult.message}
          </div>
          {testResult.schema && (
            <pre className="mt-2 text-xs text-gray-400 font-mono whitespace-pre-wrap bg-gray-900 rounded p-2 max-h-40 overflow-auto">
              {testResult.schema}
            </pre>
          )}
          {testResult.files && testResult.files.length > 0 && (
            <div className="mt-2 text-xs text-gray-400 font-mono space-y-0.5 max-h-40 overflow-auto">
              {testResult.files.map(f => <div key={f}>{f}</div>)}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// ── Main panel ───────────────────────────────────────────────────────────────

export default function ResourcesPanel({ agentId }: { agentId: string }) {
  const [resources, setResources] = useState<Resource[]>([]);
  const [showCreate, setShowCreate] = useState(false);

  const load = async () => setResources(await fetchResources(agentId));
  useEffect(() => { load(); }, [agentId]);

  const remove = async (resId: string) => {
    await deleteResource(agentId, resId);
    load();
  };

  return (
    <div className="card space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="font-medium text-white">Resources</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Repositories and databases this agent can access when answering tasks.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={14} /> Attach Resource
        </button>
      </div>

      {resources.length === 0 && (
        <div className="text-center py-8 border border-dashed border-gray-700 rounded-xl">
          <div className="flex justify-center gap-3 mb-3">
            <FolderGit2 size={24} className="text-gray-700" />
            <Database size={24} className="text-gray-700" />
          </div>
          <p className="text-gray-600 text-sm">No resources attached.</p>
          <p className="text-gray-700 text-xs mt-1">
            Attach a repository or database to let this agent access external context.
          </p>
        </div>
      )}

      <div className="space-y-3">
        {resources.map(res => (
          <ResourceCard key={res.id} resource={res} onDelete={() => remove(res.id)} />
        ))}
      </div>

      {/* Usage hint */}
      {resources.length > 0 && (
        <div className="text-xs text-gray-600 bg-gray-800/40 rounded-lg p-3 space-y-1">
          <p className="text-gray-500 font-medium">How resources are used:</p>
          {resources.filter(r => r.kind === 'repository').length > 0 && (
            <p>
              <span className="text-green-500">Repositories</span> — file contents are injected into
              the prompt automatically when you send a task to this agent.
            </p>
          )}
          {resources.filter(r => r.kind === 'database').length > 0 && (
            <p>
              <span className="text-blue-500">Databases</span> — Claude receives{' '}
              <code className="text-gray-400">list_tables</code> and{' '}
              <code className="text-gray-400">query_database</code> tools and decides when to call
              them to answer your question.
            </p>
          )}
        </div>
      )}

      {showCreate && (
        <CreateResourceModal
          agentId={agentId}
          onClose={() => setShowCreate(false)}
          onCreated={load}
        />
      )}
    </div>
  );
}
