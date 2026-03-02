import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, Cpu, Sparkles, AlertTriangle, ShieldAlert } from 'lucide-react';
import { ChatMessage, AppSettings, AuditLog } from '../types';
import { generateERPResponse } from '../services/geminiService';
import clsx from 'clsx';

interface ChatInterfaceProps {
  settings: AppSettings;
  addLog: (log: Omit<AuditLog, 'id' | 'timestamp'>) => void;
}

export const ChatInterface: React.FC<ChatInterfaceProps> = ({ settings, addLog }) => {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'init',
      role: 'system',
      content: `ERP Agent initialized.\nMode: **${settings.useLiveAgent ? 'LIVE LINK' : 'SIMULATION'}**\nTarget: \`${settings.targetUrl}\`\nReady for natural language queries.`,
      timestamp: new Date(),
    }
  ]);
  const [isThinking, setIsThinking] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Update system message if settings change
  useEffect(() => {
     setMessages(prev => {
        if (prev.length === 1 && prev[0].id === 'init') {
            return [{
                id: 'init',
                role: 'system',
                content: `ERP Agent initialized.\nMode: **${settings.useLiveAgent ? 'LIVE LINK' : 'SIMULATION'}**\nTarget: \`${settings.targetUrl}\`\nReady for natural language queries.`,
                timestamp: new Date(),
            }];
        }
        return prev;
     })
  }, [settings.useLiveAgent, settings.targetUrl]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isThinking]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isThinking) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsThinking(true);

    // Log query initiation
    addLog({
      action: 'QUERY_INIT',
      status: 'PENDING',
      details: `Processing user query: "${userMsg.content.substring(0, 30)}..."`
    });

    try {
      const responseText = await generateERPResponse(
        userMsg.content, 
        settings,
        // Logging callback for retries/errors
        (msg, type, metadata) => {
            const status = type === 'error' ? 'ERROR' : type === 'warning' ? 'WARNING' : 'SUCCESS';
            addLog({
                action: type === 'warning' ? 'RETRY_ATTEMPT' : 'SYSTEM_EVENT',
                status,
                details: msg,
                screenshot: metadata?.screenshot,
                contentHash: metadata?.contentHash
            });
        }
      );
      
      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: responseText,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, aiMsg]);
      
      addLog({
        action: 'QUERY_COMPLETE',
        status: 'SUCCESS',
        details: 'Response generated successfully.'
      });

    } catch (error: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'system',
        content: `Error: ${error.message || 'Agent communication failure.'}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);

      addLog({
        action: 'QUERY_FAILED',
        status: 'ERROR',
        details: error.message || 'Unknown error during query processing.'
      });
    } finally {
      setIsThinking(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden backdrop-blur-sm">
      {/* Header */}
      <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/80 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className={clsx(
            "p-2 rounded-lg border",
            settings.useLiveAgent ? "bg-emerald-500/10 border-emerald-500/20" : "bg-blue-500/10 border-blue-500/20"
          )}>
            <Sparkles className={clsx("w-5 h-5", settings.useLiveAgent ? "text-emerald-400" : "text-blue-400")} />
          </div>
          <div>
            <h2 className="text-sm font-semibold text-slate-100">Natural Language Query</h2>
            <div className="flex items-center space-x-2">
                <span className="text-xs text-slate-400">Gemini 2.5 Flash</span>
                <span className="text-slate-600">•</span>
                <span className={clsx("text-xs", settings.useLiveAgent ? "text-emerald-400" : "text-blue-400")}>
                    {settings.useLiveAgent ? 'Live Agent Connected' : 'Simulation Mode'}
                </span>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-6 space-y-6"
      >
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={clsx(
              "flex space-x-4 max-w-3xl",
              msg.role === 'user' ? "ml-auto flex-row-reverse space-x-reverse" : ""
            )}
          >
            <div className={clsx(
              "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 border",
              msg.role === 'assistant' ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400" :
              msg.role === 'user' ? "bg-blue-600 border-blue-400 text-white" :
              "bg-slate-800 border-slate-700 text-slate-400"
            )}>
              {msg.role === 'assistant' ? <Bot size={16} /> : 
               msg.role === 'user' ? <User size={16} /> : <Cpu size={16} />}
            </div>
            
            <div className={clsx(
              "flex flex-col",
              msg.role === 'user' ? "items-end" : "items-start"
            )}>
              <div className={clsx(
                "px-4 py-3 rounded-2xl text-sm shadow-sm",
                msg.role === 'user' 
                  ? "bg-blue-600 text-white rounded-tr-none" 
                  : msg.role === 'assistant'
                  ? "bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-none"
                  : "bg-slate-900/50 border border-slate-800 text-slate-400 font-mono text-xs w-full"
              )}>
                {msg.role === 'assistant' ? (
                  <div className="prose prose-invert prose-sm max-w-none whitespace-pre-line">
                    {msg.content}
                  </div>
                ) : (
                  msg.content
                )}
              </div>
              <span className="text-[10px] text-slate-500 mt-1 px-1">
                {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
          </div>
        ))}

        {isThinking && (
          <div className="flex space-x-4">
             <div className="w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center flex-shrink-0 animate-pulse">
               <Bot size={16} />
             </div>
             <div className="bg-slate-800/50 border border-slate-700/50 px-4 py-3 rounded-2xl rounded-tl-none flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                <span className="text-xs text-slate-400 ml-2 font-mono">
                    {settings.useLiveAgent ? 'Negotiating session...' : 'Processing...'}
                </span>
             </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 bg-slate-900 border-t border-slate-800">
        <form onSubmit={handleSubmit} className="relative flex items-center">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the ERP (e.g., 'Find unpaid invoices for Vendor X')..."
            className="w-full bg-slate-950 border border-slate-700 text-slate-200 rounded-lg pl-4 pr-12 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all text-sm shadow-inner"
          />
          <button 
            type="submit"
            disabled={!input.trim() || isThinking}
            className="absolute right-2 p-2 bg-blue-600 text-white rounded-md hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={16} />
          </button>
        </form>
        <div className="mt-2 text-center">
          <p className="text-[10px] text-slate-500 flex items-center justify-center gap-1">
            <ShieldAlert size={10} />
             Audit Active. Retries enabled for unstable connections.
          </p>
        </div>
      </div>
    </div>
  );
};