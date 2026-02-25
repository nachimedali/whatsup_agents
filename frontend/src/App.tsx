import React from 'react';
import { BrowserRouter, Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Bot, Users, MessageSquare, Activity, LayoutDashboard, MessagesSquare } from 'lucide-react';
import Dashboard from './pages/Dashboard';
import GroupsPage from './pages/Groups';
import AgentsPage from './pages/Agents';
import AgentDetail from './pages/AgentDetail';
import TeamsPage from './pages/Teams';
import ConversationsPage from './pages/Conversations';
import ConversationDetail from './pages/ConversationDetail';
import LogsPage from './pages/Logs';

const NAV = [
  { to: '/',              label: 'Dashboard',      icon: LayoutDashboard, exact: true },
  { to: '/agents',        label: 'Agents',         icon: Bot },
  { to: '/teams',         label: 'Teams',          icon: Users },
  { to: '/groups',        label: 'Groups',         icon: MessagesSquare },
  { to: '/conversations', label: 'Conversations',  icon: MessageSquare },
  { to: '/logs',          label: 'Logs',           icon: Activity },
];

function Sidebar() {
  return (
    <aside className="w-56 flex-shrink-0 bg-gray-900 border-r border-gray-800 flex flex-col">
      <div className="px-5 py-4 border-b border-gray-800">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-brand-600 rounded-lg flex items-center justify-center">
            <Bot size={16} className="text-white" />
          </div>
          <span className="font-semibold text-white">AgentFlow</span>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV.map(({ to, label, icon: Icon, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-brand-600/20 text-brand-400 font-medium'
                  : 'text-gray-400 hover:text-gray-100 hover:bg-gray-800'
              }`
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden">
        <Sidebar />
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/agents" element={<AgentsPage />} />
            <Route path="/agents/:id" element={<AgentDetail />} />
            <Route path="/teams" element={<TeamsPage />} />
            <Route path="/groups" element={<GroupsPage />} />
            <Route path="/conversations" element={<ConversationsPage />} />
            <Route path="/conversations/:id" element={<ConversationDetail />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
