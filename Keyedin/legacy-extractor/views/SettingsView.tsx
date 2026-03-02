import React, { useState } from 'react';
import { Save, Server, Globe, Shield, Activity, Sparkles, Cpu, Key, CreditCard, Lock, RefreshCw, ChevronDown, ChevronRight, ChevronsUpDown, Terminal } from 'lucide-react';
import { AppSettings, AuditLog, AIProvider } from '../types';
import clsx from 'clsx';

interface SettingsViewProps {
  settings: AppSettings;
  onSave: (settings: AppSettings) => void;
  onLog?: (log: Omit<AuditLog, 'id' | 'timestamp'>) => void;
}

export const SettingsView: React.FC<SettingsViewProps> = ({ settings, onSave, onLog }) => {
  const [formData, setFormData] = useState<AppSettings>(settings);
  const [isDirty, setIsDirty] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [showAdvancedLocal, setShowAdvancedLocal] = useState(false);

  const handleChange = (field: keyof AppSettings, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setIsDirty(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    
    if (onLog) {
        if (formData.erpUsername !== settings.erpUsername) {
            onLog({
                action: 'SECURE_UPDATE',
                status: 'SUCCESS',
                details: `Credentials updated for user ${formData.erpUsername}. Stored in System Keyring.`
            });
        }
        if (formData.apiKey !== settings.apiKey) {
             onLog({
                action: 'KEY_ROTATION',
                status: 'SUCCESS',
                details: `AI Provider API Key updated securely.`
            });
        }
    }
    
    setIsDirty(false);
  };

  const handleAutoDetectLocal = () => {
      setIsScanning(true);
      // Simulate network scan
      setTimeout(() => {
          setIsScanning(false);
          const detectedEndpoint = 'http://localhost:11434/v1/chat/completions';
          handleChange('localModelEndpoint', detectedEndpoint);
          if (onLog) {
              onLog({
                  action: 'NET_SCAN',
                  status: 'SUCCESS',
                  details: 'Detected Ollama service on port 11434.'
              });
          }
      }, 1500);
  };

  const providers: { id: AIProvider, label: string, icon: React.ElementType }[] = [
      { id: 'google', label: 'Google Gemini', icon: Sparkles },
      { id: 'anthropic', label: 'Anthropic', icon: Activity },
      { id: 'openai', label: 'OpenAI', icon: Globe },
      { id: 'local', label: 'Local LLM', icon: Cpu },
  ];

  return (
    <div className="p-8 max-w-4xl mx-auto">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white">System Configuration</h2>
        <p className="text-slate-400 text-sm mt-1">Configure the connection bridge to the Legacy ERP Target.</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        
        {/* Intelligence Engine Configuration */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-sm">
             <div className="flex items-center space-x-3 mb-6">
                <div className="p-2 bg-purple-500/10 rounded-lg border border-purple-500/20">
                    <Cpu className="text-purple-400" size={20} />
                </div>
                <h3 className="font-medium text-slate-200">Intelligence Engine</h3>
            </div>

            {/* Provider Selection */}
            <div className="grid grid-cols-4 gap-4 mb-6">
                {providers.map(p => (
                    <button
                        key={p.id}
                        type="button"
                        onClick={() => handleChange('aiProvider', p.id)}
                        className={clsx(
                            "flex flex-col items-center justify-center p-4 rounded-xl border transition-all",
                            formData.aiProvider === p.id
                                ? "bg-slate-800 border-blue-500 text-blue-400 shadow-lg shadow-blue-900/20"
                                : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700 hover:bg-slate-900"
                        )}
                    >
                        <p.icon size={24} className="mb-2" />
                        <span className="text-xs font-medium">{p.label}</span>
                    </button>
                ))}
            </div>

            {/* Auth Method & Details */}
            {formData.aiProvider !== 'local' ? (
                <div className="space-y-4 p-4 bg-slate-950/50 rounded-lg border border-slate-800">
                    <div className="flex space-x-4 mb-4 border-b border-slate-800 pb-4">
                         <button
                            type="button"
                            onClick={() => handleChange('authMethod', 'apikey')}
                            className={clsx(
                                "flex items-center px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                                formData.authMethod === 'apikey' ? "bg-blue-500/10 text-blue-400" : "text-slate-500 hover:text-slate-300"
                            )}
                         >
                            <Key size={12} className="mr-2" /> API Key
                         </button>
                         <button
                            type="button"
                            onClick={() => handleChange('authMethod', 'subscription')}
                            className={clsx(
                                "flex items-center px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                                formData.authMethod === 'subscription' ? "bg-purple-500/10 text-purple-400" : "text-slate-500 hover:text-slate-300"
                            )}
                         >
                            <CreditCard size={12} className="mr-2" /> Subscription (OAuth)
                         </button>
                    </div>

                    {formData.authMethod === 'apikey' ? (
                        <div>
                            <label className="block text-xs font-mono text-slate-500 mb-1">API SECRET KEY</label>
                            <div className="relative">
                                <input 
                                    type="password" 
                                    value={formData.apiKey || ''}
                                    onChange={(e) => handleChange('apiKey', e.target.value)}
                                    placeholder={`Enter your ${formData.aiProvider} API Key...`}
                                    className="w-full bg-slate-900 border border-slate-700 rounded p-2 text-sm text-slate-200 font-mono focus:border-blue-500 focus:outline-none pr-10"
                                />
                                <Lock size={14} className="absolute right-3 top-3 text-slate-600" />
                            </div>
                            <p className="text-[10px] text-amber-500/80 mt-1 flex items-center">
                                <Shield size={10} className="mr-1" />
                                Keys are stored locally in browser memory only.
                            </p>
                        </div>
                    ) : (
                        <div className="flex items-center justify-center py-4 bg-slate-900 rounded border border-slate-800 border-dashed">
                            <button type="button" className="px-4 py-2 bg-slate-800 text-white text-xs rounded hover:bg-slate-700 transition-colors">
                                Connect {formData.aiProvider.charAt(0).toUpperCase() + formData.aiProvider.slice(1)} Account
                            </button>
                        </div>
                    )}
                </div>
            ) : (
                <div className="space-y-4 p-5 bg-slate-950/50 rounded-lg border border-slate-800">
                     <div className="flex items-center justify-between mb-2">
                         <label className="block text-xs font-mono text-slate-500 uppercase tracking-wider">Connection Preset</label>
                         {isScanning && <span className="text-xs text-blue-400 animate-pulse">Scanning localhost...</span>}
                         {!isScanning && formData.localModelEndpoint?.includes('11434') && (
                             <span className="text-[10px] text-emerald-400 flex items-center">
                                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5"></div>
                                Ollama Detected
                             </span>
                         )}
                     </div>
                     
                     <div className="flex gap-3">
                        <div className="relative flex-1">
                            <select 
                                className="w-full appearance-none bg-slate-900 border border-slate-700 hover:border-slate-600 rounded-lg py-3 pl-4 pr-10 text-sm text-slate-200 focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all shadow-sm"
                                onChange={(e) => {
                                    const val = e.target.value;
                                    if (val === 'custom') {
                                        setShowAdvancedLocal(true);
                                    } else {
                                        handleChange('localModelEndpoint', val);
                                        setShowAdvancedLocal(false);
                                    }
                                }}
                                value={
                                    formData.localModelEndpoint?.includes('11434') ? 'http://localhost:11434/v1/chat/completions' :
                                    formData.localModelEndpoint?.includes('1234') ? 'http://localhost:1234/v1/chat/completions' :
                                    formData.localModelEndpoint?.includes('8080') ? 'http://localhost:8080/v1/chat/completions' :
                                    'custom'
                                }
                            >
                                <option value="http://localhost:11434/v1/chat/completions">Ollama (Llama 3, Mistral)</option>
                                <option value="http://localhost:1234/v1/chat/completions">LM Studio (Port 1234)</option>
                                <option value="http://localhost:8080/v1/chat/completions">LocalAI (Port 8080)</option>
                                <option value="custom">Custom / Advanced</option>
                            </select>
                            <div className="absolute inset-y-0 right-0 flex items-center px-3 pointer-events-none text-slate-500">
                                <ChevronsUpDown size={16} />
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={handleAutoDetectLocal}
                            disabled={isScanning}
                            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 text-xs font-medium flex items-center gap-2 transition-colors min-w-[140px] justify-center"
                        >
                            {isScanning ? (
                                <RefreshCw size={14} className="animate-spin text-blue-400" />
                            ) : (
                                <Sparkles size={14} className="text-amber-400" />
                            )}
                            {isScanning ? 'Scanning...' : 'Auto-Detect'}
                        </button>
                     </div>

                     <div className="pt-2">
                        <button 
                            type="button"
                            onClick={() => setShowAdvancedLocal(!showAdvancedLocal)}
                            className="flex items-center text-[10px] text-slate-500 hover:text-slate-400 transition-colors group"
                        >
                            {showAdvancedLocal ? <ChevronDown size={12} className="mr-1" /> : <ChevronRight size={12} className="mr-1" />}
                            ADVANCED CONFIGURATION
                        </button>

                        {showAdvancedLocal && (
                            <div className="mt-3 animate-in slide-in-from-top-2 duration-200">
                                <label className="block text-[10px] font-mono text-slate-600 mb-1">ENDPOINT URL</label>
                                <div className="relative">
                                    <input 
                                        type="text" 
                                        value={formData.localModelEndpoint || ''}
                                        onChange={(e) => handleChange('localModelEndpoint', e.target.value)}
                                        placeholder="http://localhost:..."
                                        className="w-full bg-slate-950 border border-slate-800 rounded p-2.5 pl-9 text-xs text-slate-400 font-mono focus:border-blue-500 focus:text-slate-200 transition-colors"
                                    />
                                    <Terminal size={14} className="absolute left-3 top-3 text-slate-600" />
                                </div>
                                <p className="text-[10px] text-slate-600 mt-2">
                                    Must be an OpenAI-compatible API endpoint (e.g., <code className="bg-slate-900 px-1 rounded text-slate-400">/v1/chat/completions</code>).
                                </p>
                            </div>
                        )}
                     </div>
                </div>
            )}
        </div>

        {/* Connection Mode */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 backdrop-blur-sm">
          <div className="flex items-start space-x-4">
            <div className="p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
              <Activity className="text-blue-400" size={24} />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-medium text-white mb-2">Backend Mode</h3>
              <p className="text-sm text-slate-400 mb-4">
                Toggle between frontend simulation and the live Python/Playwright backend.
              </p>
              
              <div className="flex space-x-4">
                <button
                  type="button"
                  onClick={() => handleChange('useLiveAgent', false)}
                  className={clsx(
                    "flex-1 py-3 px-4 rounded-lg border text-sm font-medium transition-all",
                    !formData.useLiveAgent 
                      ? "bg-blue-600 border-blue-500 text-white shadow-lg shadow-blue-900/20" 
                      : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                  )}
                >
                  Simulation (Mock)
                </button>
                <button
                  type="button"
                  onClick={() => handleChange('useLiveAgent', true)}
                  className={clsx(
                    "flex-1 py-3 px-4 rounded-lg border text-sm font-medium transition-all",
                    formData.useLiveAgent 
                      ? "bg-emerald-600 border-emerald-500 text-white shadow-lg shadow-emerald-900/20" 
                      : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                  )}
                >
                  Live Agent Connection
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Target Config */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Globe className="text-slate-400" size={20} />
                    <h3 className="font-medium text-slate-200">Target ERP</h3>
                </div>
                <div className="space-y-4">
                    <div>
                        <label className="block text-xs font-mono text-slate-500 mb-1">BASE URL</label>
                        <input 
                            type="text" 
                            value={formData.targetUrl}
                            onChange={(e) => handleChange('targetUrl', e.target.value)}
                            className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-sm text-slate-200 font-mono focus:border-blue-500 focus:outline-none"
                        />
                    </div>
                </div>
            </div>

            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Server className="text-slate-400" size={20} />
                    <h3 className="font-medium text-slate-200">Backend Bridge</h3>
                </div>
                <div className="space-y-4">
                    <div>
                        <label className="block text-xs font-mono text-slate-500 mb-1">API ENDPOINT</label>
                        <input 
                            type="text" 
                            value={formData.agentEndpoint}
                            onChange={(e) => handleChange('agentEndpoint', e.target.value)}
                            placeholder="http://localhost:8000"
                            className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-sm text-slate-200 font-mono focus:border-blue-500 focus:outline-none"
                        />
                    </div>
                </div>
            </div>
        </div>

        {/* Credentials Stubs */}
        <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6 opacity-75">
             <div className="flex items-center space-x-3 mb-4">
                <Shield className="text-slate-400" size={20} />
                <h3 className="font-medium text-slate-200">Secure Credentials</h3>
            </div>
            <div className="grid grid-cols-2 gap-4">
                <div>
                    <label className="block text-xs font-mono text-slate-500 mb-1">USERNAME</label>
                    <input 
                        type="text" 
                        value={formData.erpUsername || ''}
                        onChange={(e) => handleChange('erpUsername', e.target.value)}
                        className="w-full bg-slate-950 border border-slate-700 rounded p-2 text-sm text-slate-200 font-mono focus:border-blue-500 focus:outline-none"
                    />
                </div>
                <div>
                    <label className="block text-xs font-mono text-slate-500 mb-1">PASSWORD</label>
                    <input 
                        type="password" 
                        value={formData.erpPassword || '********'}
                        disabled
                        className="w-full bg-slate-950 border border-slate-800 rounded p-2 text-sm text-slate-600 font-mono cursor-not-allowed"
                    />
                    <p className="text-[10px] text-slate-500 mt-1">Passwords managed via Backend Vault/Keyring only.</p>
                </div>
            </div>
        </div>

        {/* Action Bar */}
        <div className="flex items-center justify-end pt-4 border-t border-slate-800">
            {isDirty && <span className="text-xs text-amber-400 mr-4 animate-pulse">Unsaved changes</span>}
            <button
                type="submit"
                className="flex items-center px-6 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-900/20"
            >
                <Save size={16} className="mr-2" />
                Save Configuration
            </button>
        </div>
      </form>
    </div>
  );
};