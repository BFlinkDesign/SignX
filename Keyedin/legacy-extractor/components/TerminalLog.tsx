import React, { useEffect, useRef } from 'react';
import { AuditLog } from '../types';
import clsx from 'clsx';
import { Image, Hash } from 'lucide-react';

interface TerminalLogProps {
  logs: AuditLog[];
  maxHeight?: string;
}

export const TerminalLog: React.FC<TerminalLogProps> = ({ logs, maxHeight = 'h-64' }) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="bg-slate-950 border border-slate-800 rounded-lg overflow-hidden font-mono text-sm shadow-inner">
      <div className="bg-slate-900 px-4 py-2 border-b border-slate-800 flex items-center justify-between">
        <span className="text-slate-400 text-xs uppercase tracking-wider font-semibold">System Kernel Log</span>
        <div className="flex space-x-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-slate-700"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-slate-700"></div>
          <div className="w-2.5 h-2.5 rounded-full bg-slate-700"></div>
        </div>
      </div>
      <div 
        ref={scrollRef}
        className={clsx("p-4 overflow-y-auto space-y-2 scroll-smooth", maxHeight)}
      >
        {logs.map((log) => (
          <div key={log.id} className="flex items-start space-x-3 hover:bg-slate-900/50 p-1 rounded group">
            <span className="text-slate-500 text-xs whitespace-nowrap pt-0.5">
              {log.timestamp.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
            <div className="flex-1 break-all">
              <div className="flex items-center flex-wrap gap-2 mb-0.5">
                  <span className={clsx(
                    "font-bold text-xs px-1.5 py-0.5 rounded",
                    log.status === 'SUCCESS' && "bg-emerald-950 text-emerald-400",
                    log.status === 'WARNING' && "bg-amber-950 text-amber-400",
                    log.status === 'ERROR' && "bg-rose-950 text-rose-400",
                    log.status === 'PENDING' && "bg-blue-950 text-blue-400",
                  )}>
                    {log.action}
                  </span>
                  {log.contentHash && (
                      <span className="flex items-center text-[10px] text-slate-600 bg-slate-900 border border-slate-800 px-1 rounded">
                          <Hash size={8} className="mr-1" />
                          {log.contentHash}
                      </span>
                  )}
              </div>
              <span className="text-slate-300 block">{log.details}</span>
              
              {/* Screenshot Attachment */}
              {log.screenshot && (
                  <div className="mt-2 mb-1">
                      <div className="inline-flex flex-col bg-slate-900 border border-slate-800 rounded-lg overflow-hidden group-hover:border-slate-700 transition-colors">
                          <div className="px-2 py-1 bg-slate-800/50 border-b border-slate-800 flex items-center gap-1">
                              <Image size={10} className="text-slate-400" />
                              <span className="text-[10px] text-slate-400">POPUP_CAPTURE.JPG</span>
                          </div>
                          <img 
                              src={log.screenshot} 
                              alt="Audit Capture" 
                              className="max-h-24 w-auto object-cover opacity-80 hover:opacity-100 transition-opacity cursor-pointer" 
                          />
                      </div>
                  </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};