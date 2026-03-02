import React from 'react';

export interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

export enum AppView {
  DASHBOARD = 'DASHBOARD',
  MAP = 'MAP',
  QUERY = 'QUERY',
  AUDIT = 'AUDIT',
  SETTINGS = 'SETTINGS'
}

export interface AuditLog {
  id: string;
  timestamp: Date;
  action: string;
  status: 'SUCCESS' | 'WARNING' | 'ERROR' | 'PENDING';
  details: string;
  screenshot?: string;
  contentHash?: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: 'root' | 'dashboard' | 'form' | 'list' | 'popup';
  status: 'mapped' | 'scanning' | 'unknown';
  connections: string[];
  interactiveMap?: {
      selector?: string;
      coordinates?: { x: number, y: number };
      description?: string;
  }[];
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'system' | 'assistant';
  content: string;
  timestamp: Date;
  isThinking?: boolean;
}

export enum ConnectionStatus {
  DISCONNECTED = 'DISCONNECTED',
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  SECURE = 'SECURE'
}

export type AIProvider = 'google' | 'anthropic' | 'openai' | 'local';
export type AuthMethod = 'apikey' | 'subscription';

export interface AppSettings {
  targetUrl: string;
  agentEndpoint: string;
  useLiveAgent: boolean;
  erpUsername?: string;
  erpPassword?: string; // In real app, handle this securely or rely on backend vault

  // Intelligence Configuration
  aiProvider: AIProvider;
  authMethod: AuthMethod;
  apiKey?: string;
  localModelEndpoint?: string;
}

export interface ChatInterfaceProps {
  settings: AppSettings;
  addLog: (log: Omit<AuditLog, 'id' | 'timestamp'>) => void;
}