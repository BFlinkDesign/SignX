import * as Y from 'yjs';
import { WebsocketProvider } from 'y-websocket';

export function createYDoc(room = 'betterbeam-dev', url = 'ws://localhost:1234') {
  const doc = new Y.Doc();
  const provider = new WebsocketProvider(url, room, doc, { connect: true });
  const text = doc.getText('shared');
  provider.on('status', (e: any) => {
    // eslint-disable-next-line no-console
    console.log('[yjs] status', e);
  });
  return { doc, provider, text };
}


