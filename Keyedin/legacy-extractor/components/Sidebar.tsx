import React from 'react';
import { LayoutGrid, Network, MessageSquareCode, ShieldAlert, Settings, Power } from 'lucide-react';
import { AppView, NavItem } from '../types';
import clsx from 'clsx';

interface SidebarProps {
  currentView: AppView;
  onChangeView: (view: AppView) => void;
  onKillSession?: () => void;
}

const NAV_ITEMS: NavItem[] = [
  { id: AppView.DASHBOARD, label: 'Command Center', icon: <LayoutGrid size={20} /> },
  { id: AppView.MAP, label: 'Deep Map', icon: <Network size={20} /> },
  { id: AppView.QUERY, label: 'ERP Chat', icon: <MessageSquareCode size={20} /> },
  { id: AppView.AUDIT, label: 'Audit Logs', icon: <ShieldAlert size={20} /> },
];

export const Sidebar: React.FC<SidebarProps> = ({ currentView, onChangeView, onKillSession }) => {
  return (
    <div className="w-64 h-screen bg-slate-950 border-r border-slate-800 flex flex-col">
      {/* Logo */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800">
        <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold font-mono">L</span>
            </div>
            <div>
                <h1 className="text-slate-100 font-bold text-sm tracking-tight">LegacyLink</h1>
                <p className="text-[10px] text-slate-500 font-mono">ERP CONNECTOR v2.4</p>
            </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-6 px-3 space-y-1">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            onClick={() => onChangeView(item.id as AppView)}
            className={clsx(
              "w-full flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200",
              currentView === item.id 
                ? "bg-slate-900 text-blue-400 shadow-sm ring-1 ring-slate-800" 
                : "text-slate-400 hover:text-slate-200 hover:bg-slate-900/50"
            )}
          >
            <span className={clsx(
                "mr-3 transition-colors",
                currentView === item.id ? "text-blue-500" : "text-slate-500"
            )}>{item.icon}</span>
            {item.label}
          </button>
        ))}
      </nav>

      {/* Bottom Actions */}
      <div className="p-4 border-t border-slate-800 space-y-2">
        <button 
          onClick={() => onChangeView(AppView.SETTINGS)}
          className={clsx(
            "w-full flex items-center px-3 py-2 rounded-lg text-xs font-medium transition-colors",
            currentView === AppView.SETTINGS 
                ? "bg-slate-900 text-blue-400" 
                : "text-slate-500 hover:text-slate-300 hover:bg-slate-900/50"
        )}>
          <Settings size={16} className="mr-3" />
          Settings
        </button>
        <div className="pt-4 mt-4 border-t border-slate-800/50">
            <button 
                onClick={onKillSession}
                className="w-full flex items-center justify-between px-3 py-2 bg-red-500/5 border border-red-500/10 rounded-lg hover:bg-red-500/10 transition-colors group"
            >
                <span className="text-red-400 text-xs font-medium group-hover:text-red-300">Kill Session</span>
                <Power size={14} className="text-red-500 cursor-pointer group-hover:text-red-300" />
            </button>
        </div>
      </div>
    </div>
  );
};