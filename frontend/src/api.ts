// O modo n8n nunca retorna silenciosamente à API Python quando um workflow falha.
export type BackendMode = 'n8n' | 'python';

export function backendMode(): BackendMode {
  return localStorage.getItem('pbi-backend') === 'python' ? 'python' : 'n8n';
}

export function selectBackend(mode: BackendMode) {
  localStorage.setItem('pbi-backend', mode);
  location.reload();
}

export async function api<T>(path:string, init?:RequestInit):Promise<T> {
  const url = backendMode() === 'n8n' ? path.replace(/^\/api\//, '/workflow-api/') : path;
  const headers = new Headers(init?.headers);
  if (init?.method === 'POST' && !headers.has('Idempotency-Key')) headers.set('Idempotency-Key',crypto.randomUUID());
  const response = await fetch(url,{...init,headers});
  if (!response.ok) {
    const body = await response.json().catch(()=>({detail:response.statusText}));
    throw new Error(typeof body.detail==='string' ? body.detail : 'Falha no contrato da API');
  }
  return response.json();
}
