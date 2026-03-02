import React, { useState, useEffect } from 'react';
import { Sidebar } from './components/Sidebar';
import { DashboardView } from './views/DashboardView';
import { ChatInterface } from './components/ChatInterface';
import { KnowledgeGraph } from './components/KnowledgeGraph';
import { TerminalLog } from './components/TerminalLog';
import { SettingsView } from './views/SettingsView';
import { AppView, AuditLog, AppSettings } from './types';
import { INITIAL_NODES, SAMPLE_LOGS, DEFAULT_SETTINGS } from './constants';
import { fetchSystemLogs, stopAgent } from './services/geminiService';

const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<AppView>(AppView.DASHBOARD);
  const [logs, setLogs] = useState<AuditLog[]>(SAMPLE_LOGS);
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);

  // REAL LOG POLLING: Connects to Python Backend
  useEffect(() => {
    if (!settings.useLiveAgent || !settings.agentEndpoint) return;

    const pollLogs = async () => {
        const realLogs = await fetchSystemLogs(settings.agentEndpoint);
        if (realLogs.length > 0) {
             // Merge logic: Add new logs that don't exist in state
             setLogs(prev => {
                 const existingIds = new Set(prev.map(l => l.id));
                 const newItems = realLogs.filter(l => !existingIds.has(l.id));
                 if (newItems.length === 0) return prev;
                 return [...prev.slice(Math.max(0, prev.length - 50 + newItems.length)), ...newItems];
             });
        }
    };

    const interval = setInterval(pollLogs, 2000); // Poll every 2s
    return () => clearInterval(interval);
  }, [settings.useLiveAgent, settings.agentEndpoint]);

  const addLog = (logData: Omit<AuditLog, 'id' | 'timestamp'>) => {
    const newLog: AuditLog = {
      id: Date.now().toString(),
      timestamp: new Date(),
      ...logData
    };
    setLogs(prev => [...prev.slice(-49), newLog]);
  };

  const handleSaveSettings = (newSettings: AppSettings) => {
      setSettings(newSettings);
      setCurrentView(AppView.DASHBOARD);
  };

  const handleKillSession = async () => {
      if (settings.useLiveAgent && settings.agentEndpoint) {
          await stopAgent(settings.agentEndpoint);
          addLog({ action: 'SESSION_KILL', status: 'WARNING', details: 'Manual Override: Terminated active browser sessions.' });
      } else {
          addLog({ action: 'SESSION_KILL', status: 'SUCCESS', details: 'Simulated session termination.' });
      }
  };

  const renderContent = () => {
    switch (currentView) {
      case AppView.DASHBOARD:
        return <DashboardView logs={logs} settings={settings} />;
      case AppView.QUERY:
        return (
          <div className="h-screen p-6 max-w-6xl mx-auto flex flex-col">
            <div className="mb-6">
               <h2 className="text-2xl font-bold text-white">Agent Query Interface</h2>
               <p className="text-slate-400 text-sm">Natural language bridge to legacy ERP data.</p>
            </div>
            <div className="flex-1 min-h-0">
               <ChatInterface settings={settings} addLog={addLog} />
            </div>
          </div>
        );
      case AppView.MAP:
        return (
          <div className="h-screen flex flex-col">
            <div className="px-8 py-6 border-b border-slate-800 bg-slate-950/50 z-10">
              <h2 className="text-2xl font-bold text-white">Knowledge Graph</h2>
              <p className="text-slate-400 text-sm">Real-time topology of the mapped ERP interface.</p>
            </div>
            <div className="flex-1 bg-slate-950 relative overflow-hidden">
                {/* Grid Background Pattern */}
                <div className="absolute inset-0" style={{ backgroundImage: 'radial-gradient(#1e293b 1px, transparent 1px)', backgroundSize: '40px 40px', opacity: 0.2 }}></div>
                <KnowledgeGraph nodes={INITIAL_NODES} className="z-10" />
            </div>
          </div>
        );
      case AppView.AUDIT:
        return (
            <div className="p-8 max-w-7xl mx-auto">
                <div className="mb-6 flex justify-between items-end">
                    <div>
                        <h2 className="text-2xl font-bold text-white">Security Audit Logs</h2>
                        <p className="text-slate-400 text-sm">Immutable record of all agent actions.</p>
                    </div>
                    <div className="flex space-x-2">
                        <button className="px-3 py-1.5 bg-slate-800 text-slate-300 text-xs rounded border border-slate-700 hover:bg-slate-700">Export CSV</button>
                    </div>
                </div>
                <TerminalLog logs={logs} maxHeight="h-[calc(100vh-200px)]" />
            </div>
        );
      case AppView.SETTINGS:
        return <SettingsView settings={settings} onSave={handleSaveSettings} onLog={addLog} />;
      default:
        return <div className="p-10 text-slate-500">View not implemented yet.</div>;
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-200 font-sans selection:bg-blue-500/30">
      <Sidebar currentView={currentView} onChangeView={setCurrentView} onKillSession={handleKillSession} />
      <main className="flex-1 overflow-auto bg-slate-950 relative">
        {renderContent()}
      </main>
    </div>
  );
};

export default App;