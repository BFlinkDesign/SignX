import { AppView, GraphNode, AuditLog, AppSettings } from './types';

export const INITIAL_NODES: GraphNode[] = [
  { id: 'login', label: 'Login Gate', type: 'root', status: 'mapped', connections: ['dashboard'] },
  { id: 'dashboard', label: 'Main Dashboard', type: 'dashboard', status: 'mapped', connections: ['inv_list', 'po_list', 'vendor_master'] },
  { id: 'inv_list', label: 'Invoice List', type: 'list', status: 'mapped', connections: ['inv_detail', 'dashboard'], interactiveMap: [{ selector: '#btn_export', coordinates: {x: 800, y: 50}, description: 'Export CSV' }] },
  { id: 'inv_detail', label: 'Invoice Detail', type: 'form', status: 'mapped', connections: ['inv_list'] },
  { id: 'po_list', label: 'Purchase Orders', type: 'list', status: 'mapped', connections: ['po_detail', 'dashboard'] },
  { id: 'po_detail', label: 'PO Detail', type: 'form', status: 'scanning', connections: ['po_list'] },
  { id: 'vendor_master', label: 'Vendor Master', type: 'form', status: 'mapped', connections: ['dashboard', 'vendor_popup'] },
  { id: 'vendor_popup', label: 'Contact Popup', type: 'popup', status: 'unknown', connections: ['vendor_master'] },
];

export const SAMPLE_LOGS: AuditLog[] = [
  { id: '1', timestamp: new Date(Date.now() - 1000 * 60 * 5), action: 'SESSION_INIT', status: 'SUCCESS', details: 'Secure handshake with MVI.exe established.' },
  { id: '2', timestamp: new Date(Date.now() - 1000 * 60 * 4), action: 'NAVIGATE', status: 'SUCCESS', details: 'Navigated to /LOGIN.START' },
  { id: '3', timestamp: new Date(Date.now() - 1000 * 60 * 3), action: 'AUTH_CHALLENGE', status: 'SUCCESS', details: 'Credentials injected via Secure Enclave.' },
  { id: '4', timestamp: new Date(Date.now() - 1000 * 60 * 2), action: 'UI_VERIFY', status: 'WARNING', details: 'UI Cache stale for frame[2]. Triggering re-scan.' },
  { id: '5', timestamp: new Date(Date.now() - 1000 * 30), action: 'POPUP_CAPTURE', status: 'SUCCESS', details: 'Captured report popup state.', screenshot: 'https://placehold.co/320x240/1e293b/e2e8f0?text=Legacy+Report', contentHash: 'sha256:99d...a21' },
];

export const DEFAULT_SETTINGS: AppSettings = {
  targetUrl: 'https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START',
  agentEndpoint: 'http://localhost:8000/api/query',
  useLiveAgent: false,
  erpUsername: 'ADMIN',
  
  aiProvider: 'google',
  authMethod: 'apikey',
  apiKey: '', // Empty by default for security
  localModelEndpoint: 'http://localhost:11434/v1/chat/completions'
};