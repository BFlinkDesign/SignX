import React, { useState, useEffect } from 'react';
import { StatusBadge } from '../components/StatusBadge';
import { TerminalLog } from '../components/TerminalLog';
import { Activity, ShieldCheck, Database, Zap, MonitorPlay, Square, RefreshCw, Maximize2, Minimize2 } from 'lucide-react';
import { AuditLog, AppSettings } from '../types';
import { fetchLiveScreenshot, stopAgent } from '../services/geminiService';
import clsx from 'clsx';

interface DashboardViewProps {
  logs: AuditLog[];
  settings?: AppSettings;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ logs, settings }) => {
  const [liveImage, setLiveImage] = useState<string | null>(null);
  const [isStopping, setIsStopping] = useState(false);
  const [isFullScreen, setIsFullScreen] = useState(false);

  // Poll for live screenshot if agent is active
  useEffect(() => {
    if (!settings?.useLiveAgent || !settings?.agentEndpoint) return;

    const interval = setInterval(async () => {
       const img = await fetchLiveScreenshot(settings.agentEndpoint, 'global_session'); 
       if (img) setLiveImage(img);
    }, 1000);

    return () => clearInterval(interval);
  }, [settings?.useLiveAgent, settings?.agentEndpoint]);

  // Handle Escape key to exit full screen
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setIsFullScreen(false);
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, []);

  const handleStop = async () => {
      if (!settings?.agentEndpoint) return;
      setIsStopping(true);
      await stopAgent(settings.agentEndpoint);
      setTimeout(() => setIsStopping(false), 1000);
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Command Center</h2>
          <p className="text-slate-400 text-sm mt-1">System Status: <span className="text-emerald-400 font-mono">OPERATIONAL</span></p>
        </div>
        <div className="flex items-center space-x-4">
             <StatusBadge label="Secure Enclave Active" status="success" />
             <StatusBadge label="MVI.exe Connected" status="success" pulse />
        </div>
      </div>

      {/* Live Operator Deck (Visual Monitor) */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className={clsx(
            "bg-slate-950 border border-slate-800 rounded-xl overflow-hidden relative group transition-all duration-300",
            isFullScreen ? "fixed inset-0 z-50 rounded-none border-0" : "lg:col-span-2"
        )}>
            <div className="absolute top-0 left-0 right-0 p-3 bg-gradient-to-b from-slate-900/90 to-transparent flex justify-between items-start z-10">
                <div className="flex items-center gap-2">
                    <MonitorPlay size={16} className="text-emerald-400 animate-pulse" />
                    <span className="text-xs font-mono text-emerald-400">LIVE_FEED :: {settings?.useLiveAgent ? 'ACTIVE' : 'STANDBY'}</span>
                </div>
                <div className="flex items-center gap-2">
                    <button 
                        onClick={() => setIsFullScreen(!isFullScreen)}
                        className="p-1.5 bg-slate-800/50 text-slate-400 rounded hover:bg-slate-700 hover:text-white transition-colors backdrop-blur-sm"
                        title={isFullScreen ? "Exit Full Screen (Esc)" : "Full Screen"}
                    >
                        {isFullScreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
                    </button>
                    <button 
                        onClick={handleStop}
                        disabled={isStopping}
                        className="flex items-center gap-2 px-3 py-1.5 bg-red-500/20 border border-red-500/50 text-red-400 text-xs font-bold rounded hover:bg-red-500 hover:text-white transition-all backdrop-blur-sm"
                    >
                        {isStopping ? <RefreshCw size={12} className="animate-spin" /> : <Square size={12} fill="currentColor" />}
                        MANUAL OVERRIDE
                    </button>
                </div>
            </div>
            
            <div className={clsx(
                "bg-black flex items-center justify-center relative",
                isFullScreen ? "h-screen w-screen" : "aspect-video"
            )}>
                {liveImage ? (
                    <img src={liveImage} alt="Live Browser Feed" className="w-full h-full object-contain" />
                ) : (
                    <div className="text-slate-600 flex flex-col items-center">
                        <Activity size={48} className="mb-2 opacity-20" />
                        <span className="text-xs font-mono">NO SIGNAL / AWAITING COMMAND</span>
                    </div>
                )}
                
                {/* CRT Scanline Effect */}
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-white/5 to-transparent opacity-10 pointer-events-none" style={{ backgroundSize: '100% 4px' }}></div>
            </div>
        </div>

        <div className="space-y-4">
             <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl backdrop-blur-sm">
                <div className="flex items-center justify-between mb-4">
                    <div className="p-2 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
                        <ShieldCheck className="text-emerald-400" size={20} />
                    </div>
                    <span className="text-xs text-slate-500 font-mono">SECURE_AUTH</span>
                </div>
                <div className="text-2xl font-bold text-white">Active</div>
                <div className="text-xs text-slate-400 mt-1">Last handshake: 2s ago</div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl backdrop-blur-sm">
                <div className="flex items-center justify-between mb-4">
                    <div className="p-2 bg-blue-500/10 rounded-lg border border-blue-500/20">
                        <Database className="text-blue-400" size={20} />
                    </div>
                    <span className="text-xs text-slate-500 font-mono">GRAPH_NODES</span>
                </div>
                <div className="text-2xl font-bold text-white">142</div>
                <div className="text-xs text-slate-400 mt-1">Pages mapped</div>
            </div>
             
             <div className="bg-slate-900/50 border border-slate-800 p-4 rounded-xl backdrop-blur-sm">
                <div className="flex items-center justify-between mb-4">
                    <div className="p-2 bg-amber-500/10 rounded-lg border border-amber-500/20">
                        <Activity className="text-amber-400" size={20} />
                    </div>
                    <span className="text-xs text-slate-500 font-mono">LATENCY</span>
                </div>
                <div className="text-2xl font-bold text-white">240ms</div>
            </div>
        </div>
      </div>

      {/* Logs */}
      <div>
        <div className="mb-4 flex items-center justify-between">
            <h3 className="text-lg font-semibold text-white">Live Kernel Stream</h3>
            <button className="text-xs text-blue-400 hover:text-blue-300">Download Logs</button>
        </div>
        <TerminalLog logs={logs} maxHeight="h-64" />
      </div>

    </div>
  );
};