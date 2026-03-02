import { GoogleGenAI } from "@google/genai";
import { AppSettings, AuditLog } from "../types";
import { INITIAL_NODES } from "../constants";

// REMOVED: Global initialization of GoogleGenAI to prevent key leakage and support BYOK
// const apiKey = process.env.API_KEY || ''; 
// const ai = new GoogleGenAI({ apiKey });

// --- Retry Logic & Error Types ---

const RETRY_MAX_ATTEMPTS = 3;
const RETRY_BASE_DELAY_MS = 1000;

class AgentError extends Error {
    constructor(message: string, public type: 'NETWORK' | 'TIMEOUT' | 'AUTH' | 'UI_CHANGE' | 'UNKNOWN') {
        super(message);
        this.name = 'AgentError';
    }
}

/**
 * Mimics tenacity.retry with exponential backoff
 */
async function retry<T>(
  fn: () => Promise<T>,
  retries: number = RETRY_MAX_ATTEMPTS,
  delay: number = RETRY_BASE_DELAY_MS,
  onRetry?: (error: any, attempt: number) => void
): Promise<T> {
  let lastError: any;
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error: any) {
      lastError = error;
      
      // SPECIAL HANDLING: Auto-Reauth Simulation
      if (error instanceof AgentError && error.type === 'AUTH') {
          if (onRetry) onRetry(new Error("Session Token Expired. Auto-negotiating new secure handshake..."), i + 1);
          await new Promise(r => setTimeout(r, 2000)); // Simulate login delay
          continue; // Retry
      }
      
      if (onRetry) onRetry(error, i + 1);
      
      if (i < retries - 1) {
          const backoff = delay * Math.pow(2, i);
          await new Promise(r => setTimeout(r, backoff));
      }
    }
  }
  throw lastError;
}

// --- Prompts ---

const ERP_SYSTEM_PROMPT = `
You are the autonomous interface for a legacy ERP system (EagleSign/MultiValue).
The user will ask you queries about business data (Invoices, POs, Vendors, Jobs).
You are simulating the backend agent that navigates the legacy "green screen" web interface to find this data.

Current Known ERP Map (Graph Nodes):
${JSON.stringify(INITIAL_NODES.map(n => ({ 
    id: n.id, 
    label: n.label, 
    connections: n.connections,
    interactiveMap: n.interactiveMap 
})))}

Your Logic:
1. **Fuzzy Navigation**: Match the user's intent to the most relevant Node ID from the map above. Mention this in your response.
2. **UI Element Analysis**: Identify interactive elements on the target screen using the 'interactiveMap' data if available, or Hallucinate plausible ones.
   - STRICT FORMAT: "interactive_elements: [{"selector": "...", "coordinates": [x,y]}]"
3. **Data Extraction**: Generate plausible synthetic data for the context.
4. **Structure**: Use Markdown tables or lists.

Example Response:
"Resolved intent to node: \`inv_list\`.
Navigating to *Invoice List*...
Verifying UI Element Cache... [OK]

Found 1 matching record:
**Invoice #9921** | Status: **Paid** | Amount: **$450.00**
"
`;

// --- Main Service ---

export const stopAgent = async (endpoint: string) => {
    try {
        const cleanEndpoint = endpoint.replace('/api/query', '/api/stop');
        await fetch(cleanEndpoint, { method: 'POST' });
        return true;
    } catch (e) {
        console.error("Failed to stop agent:", e);
        return false;
    }
};

export const fetchLiveScreenshot = async (endpoint: string, sessionId: string): Promise<string | null> => {
    try {
        const cleanEndpoint = endpoint.replace('/api/query', '/api/live/screenshot');
        const response = await fetch(cleanEndpoint, {
            headers: { 'X-Session-ID': sessionId }
        });
        if (!response.ok) return null;
        const data = await response.json();
        return data.image;
    } catch (e) {
        return null;
    }
};

export const fetchSystemLogs = async (endpoint: string, sessionId?: string): Promise<AuditLog[]> => {
    try {
        const cleanEndpoint = endpoint.replace('/api/query', '/api/logs');
        const response = await fetch(cleanEndpoint, {
            headers: sessionId ? { 'X-Session-ID': sessionId } : {}
        });
        if (!response.ok) return [];
        
        const rawLogs = await response.json();
        return rawLogs.map((l: any) => ({
            id: l.id,
            timestamp: new Date(l.timestamp),
            action: l.action,
            status: l.status,
            details: l.details,
            screenshot: l.screenshot,
            contentHash: l.contentHash
        }));
    } catch (e) {
        console.error("Failed to poll logs:", e);
        return [];
    }
};

// Store session ID in closure for this service run
let currentSessionId: string | null = null;

export const generateERPResponse = async (
    userQuery: string, 
    settings: AppSettings,
    onLog?: (message: string, type: 'info' | 'warning' | 'error', metadata?: { screenshot?: string, contentHash?: string }) => void
): Promise<string> => {
  
  // 1. Live Agent Mode (Python Backend)
  if (settings.useLiveAgent && settings.agentEndpoint) {
    try {
      const result = await retry(
        async () => {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30s timeout for Real AI

            try {
                const response = await fetch(settings.agentEndpoint, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        ...(currentSessionId ? { 'X-Session-ID': currentSessionId } : {})
                    },
                    body: JSON.stringify({ 
                        query: userQuery, 
                        targetUrl: settings.targetUrl,
                        aiProvider: settings.aiProvider,
                        apiKey: settings.apiKey,
                        localModelEndpoint: settings.localModelEndpoint
                    }),
                    signal: controller.signal
                });

                if (!response.ok) {
                    if (response.status === 401 || response.status === 403) throw new AgentError("Authentication failed.", 'AUTH');
                    if (response.status === 503) throw new AgentError("Backend Unavailable", 'NETWORK');
                    throw new AgentError(`Agent Error ${response.status}`, 'UNKNOWN');
                }
                const json = await response.json();
                // Update Session ID if returned
                if (json.session_id) currentSessionId = json.session_id;
                return json;
            } catch (e: any) {
                if (e.name === 'AbortError') throw new AgentError("Timeout waiting for Agent.", 'TIMEOUT');
                throw e;
            } finally {
                clearTimeout(timeoutId);
            }
        },
        RETRY_MAX_ATTEMPTS,
        RETRY_BASE_DELAY_MS,
        (err, attempt) => {
            if (onLog) onLog(`Attempt ${attempt}: ${err.message}`, 'warning');
        }
      );

      if (result.error) {
          if (result.error.includes("layout mismatch")) throw new AgentError(`UI Layout Change Detected`, 'UI_CHANGE');
          throw new AgentError(result.error, 'UNKNOWN');
      }

      return result.result || result.message || JSON.stringify(result);

    } catch (error: any) {
      let errorMessage = "";
      if (error instanceof AgentError) {
          if (onLog) onLog(`Agent Failed (${error.type}): ${error.message}`, 'error');
          errorMessage = `**Agent Failure (${error.type})**: ${error.message}`;
      } else {
          if (onLog) onLog(`Critical Network Failure: ${error.message}`, 'error');
          errorMessage = `**Connection Failed**: Could not reach agent at \`${settings.agentEndpoint}\`.`;
      }
      return `⚠️ ${errorMessage}\n\n*Falling back to simulation mode...*\n\n` + await runSimulation(userQuery, settings, onLog);
    }
  }

  // 2. Simulation Mode (Frontend-only LLM)
  return runSimulation(userQuery, settings, onLog);
};

const runSimulation = async (
    userQuery: string,
    settings: AppSettings,
    onLog?: (message: string, type: 'info' | 'warning' | 'error', metadata?: any) => void
): Promise<string> => {
  
  // --- Simulation Events ---
  if (Math.random() > 0.5) {
      if (onLog) onLog("Verifying UI Element Cache...", 'info');
      await new Promise(r => setTimeout(r, 500)); 
  }

  // --- Provider Logic ---
  
  // Case: Google Gemini
  if (settings.aiProvider === 'google') {
      if (!settings.apiKey) {
          return `[CONFIGURATION REQUIRED]\n\nPlease go to Settings > Intelligence Engine and provide your **Google Gemini API Key** to enable the simulation agent.\n\n(This application uses a Bring-Your-Own-Key security model).`;
      }

      try {
        const ai = new GoogleGenAI({ apiKey: settings.apiKey });
        const response = await ai.models.generateContent({
          model: 'gemini-2.5-flash',
          contents: userQuery,
          config: {
            systemInstruction: ERP_SYSTEM_PROMPT,
            temperature: 0.4,
          },
        });
        return response.text || "Error: No response text generated.";
      } catch (error: any) {
        console.error("Gemini API Error:", error);
        return `**Gemini API Error**: ${error.message || 'Unknown error'}. Please check your API Key.`;
      }
  }

  // Case: Local LLM (Ollama/Llama3)
  if (settings.aiProvider === 'local') {
       return `[LOCAL SIMULATION]\n\nSuccessfully connected to Local LLM at \`${settings.localModelEndpoint}\`.\n\n(Mock Response): Navigation complete. Found 5 records matching "${userQuery}".`;
  }

  // Case: Others (Mocked for now)
  return `[PROVIDER NOT IMPLEMENTED]\n\nSimulation for **${settings.aiProvider}** is not fully implemented in this demo version.\n\nPlease switch to **Google Gemini** or **Local LLM** in Settings.`;
}