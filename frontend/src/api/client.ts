const API_BASE = '/api/v1'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body.slice(0, 200)}`)
  }
  return res.json()
}

export const api = {
  health: () => request<{ status: string; version: string }>('/health'),

  listSkills: () =>
    request<{ skills: import('./types').Skill[]; total: number }>('/skills'),
  getSkill: (id: string) => request<import('./types').Skill>(`/skills/${id}`),

  listHooks: () =>
    request<{ hooks: import('./types').Hook[]; total: number }>('/hooks'),
  getHook: (id: string) => request<import('./types').Hook>(`/hooks/${id}`),

  listTools: () =>
    request<{ tools: import('./types').Tool[]; total: number }>('/tools'),
  getTool: (id: string) => request<import('./types').Tool>(`/tools/${id}`),

  runAgent: (task: string, params?: Record<string, unknown>) =>
    request<import('./types').AgentRunResponse>('/agents/run', {
      method: 'POST',
      body: JSON.stringify({ task, parameters: params ?? {} }),
    }),

  listRuns: (limit = 50, offset = 0) =>
    request<{ runs: import('./types').RunSummary[]; total: number }>(
      `/runs?limit=${limit}&offset=${offset}`,
    ),
  getRun: (id: string) =>
    request<import('./types').RunDetail>(`/runs/${id}`),
  getRunEvents: (id: string, limit = 500, offset = 0) =>
    request<{ events: import('./types').AgentEvent[]; total: number }>(
      `/runs/${id}/events?limit=${limit}&offset=${offset}`,
    ),

  approveRun: (runId: string) =>
    request<import('./types').ApproveResponse>(`/runs/${runId}/approve`, {
      method: 'POST',
    }),

  cancelRun: (runId: string) =>
    request<import('./types').CancelResponse>(`/runs/${runId}/cancel`, {
      method: 'POST',
    }),
}
