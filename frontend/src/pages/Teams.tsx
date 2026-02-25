import React, { useEffect, useState } from 'react';
import { api, Team, Agent } from '../api/client';
import { Plus, Users, Trash2, UserPlus, UserMinus } from 'lucide-react';

function CreateTeamModal({ onClose, onCreated, agents }: {
  onClose: () => void;
  onCreated: () => void;
  agents: Agent[];
}) {
  const [form, setForm] = useState({ id: '', name: '', leader_agent_id: '' });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.teams.create({
        id: form.id,
        name: form.name,
        leader_agent_id: form.leader_agent_id || undefined,
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
      <div className="card w-full max-w-md">
        <h2 className="text-lg font-semibold text-white mb-5">Create Team</h2>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="label">Team ID <span className="text-gray-600">(slug, e.g. "dev")</span></label>
            <input
              className="input"
              placeholder="dev"
              value={form.id}
              onChange={e => setForm(f => ({ ...f, id: e.target.value.toLowerCase() }))}
              required
            />
          </div>
          <div>
            <label className="label">Display Name</label>
            <input
              className="input"
              placeholder="Dev Team"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              required
            />
          </div>
          <div>
            <label className="label">Leader Agent (optional)</label>
            <select
              className="input"
              value={form.leader_agent_id}
              onChange={e => setForm(f => ({ ...f, leader_agent_id: e.target.value }))}
            >
              <option value="">— none —</option>
              {agents.map(a => <option key={a.id} value={a.id}>{a.name} (@{a.id})</option>)}
            </select>
          </div>
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <div className="flex gap-3 pt-2">
            <button type="button" className="btn-ghost flex-1" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn-primary flex-1" disabled={loading}>
              {loading ? 'Creating…' : 'Create Team'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function TeamsPage() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showCreate, setShowCreate] = useState(false);

  const load = async () => {
    const [t, a] = await Promise.all([api.teams.list(), api.agents.list()]);
    setTeams(t);
    setAgents(a);
  };

  useEffect(() => { load(); }, []);

  const unassignedAgents = (team: Team) =>
    agents.filter(a => !team.agents.some(ta => ta.id === a.id));

  const removeTeam = async (id: string) => {
    if (!confirm(`Delete team "${id}"?`)) return;
    await api.teams.delete(id);
    load();
  };

  const addAgent = async (teamId: string, agentId: string) => {
    await api.teams.addAgent(teamId, agentId);
    load();
  };

  const removeAgent = async (teamId: string, agentId: string) => {
    await api.teams.removeAgent(teamId, agentId);
    load();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">Teams</h1>
        <button className="btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> New Team
        </button>
      </div>

      {teams.length === 0 && (
        <div className="card text-center py-12">
          <Users size={40} className="mx-auto text-gray-700 mb-3" />
          <p className="text-gray-500">No teams yet. Teams let agents collaborate with each other.</p>
        </div>
      )}

      <div className="space-y-4">
        {teams.map(team => (
          <div key={team.id} className="card space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-white">{team.name}</h2>
                <p className="text-sm text-gray-500">
                  <span className="font-mono">@{team.id}</span>
                  {team.leader_agent_id && (
                    <><span className="mx-2">·</span>Leader: <span className="text-brand-400">@{team.leader_agent_id}</span></>
                  )}
                </p>
              </div>
              <button className="btn-danger" onClick={() => removeTeam(team.id)}>
                <Trash2 size={14} />
              </button>
            </div>

            <div>
              <p className="text-xs text-gray-500 mb-2">Members ({team.agents.length})</p>
              <div className="flex flex-wrap gap-2">
                {team.agents.map(agent => (
                  <div key={agent.id} className="flex items-center gap-1.5 bg-gray-800 rounded-lg px-3 py-1.5 text-sm">
                    <span className="text-gray-200">{agent.name}</span>
                    <span className="text-gray-500 font-mono text-xs">@{agent.id}</span>
                    {agent.id === team.leader_agent_id && (
                      <span className="badge bg-brand-900/40 text-brand-400 ml-1">leader</span>
                    )}
                    <button
                      className="ml-1 text-gray-600 hover:text-red-400 transition-colors"
                      onClick={() => removeAgent(team.id, agent.id)}
                    >
                      <UserMinus size={12} />
                    </button>
                  </div>
                ))}

                {/* Add agent dropdown */}
                {unassignedAgents(team).length > 0 && (
                  <select
                    className="bg-gray-800 border border-dashed border-gray-700 rounded-lg px-3 py-1.5 text-sm text-gray-500 cursor-pointer"
                    value=""
                    onChange={e => e.target.value && addAgent(team.id, e.target.value)}
                  >
                    <option value="">+ Add agent</option>
                    {unassignedAgents(team).map(a => (
                      <option key={a.id} value={a.id}>{a.name} (@{a.id})</option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            <div className="text-xs text-gray-600 bg-gray-800/40 rounded-lg px-3 py-2">
              Route to this team: send <code className="text-brand-400">@{team.id} your message</code>
              {team.leader_agent_id && ` → handled by @${team.leader_agent_id}`}
            </div>
          </div>
        ))}
      </div>

      {showCreate && (
        <CreateTeamModal
          onClose={() => setShowCreate(false)}
          onCreated={load}
          agents={agents}
        />
      )}
    </div>
  );
}
