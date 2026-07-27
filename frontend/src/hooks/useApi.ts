import { useQuery, useMutation } from '@tanstack/react-query'
import { api } from '../api/client'

export function useHealth() {
  return useQuery({ queryKey: ['health'], queryFn: api.health })
}

export function useSkills() {
  return useQuery({ queryKey: ['skills'], queryFn: api.listSkills })
}

export function useSkill(id: string) {
  return useQuery({
    queryKey: ['skill', id],
    queryFn: () => api.getSkill(id),
    enabled: !!id,
  })
}

export function useHooks() {
  return useQuery({ queryKey: ['hooks'], queryFn: api.listHooks })
}

export function useHook(id: string) {
  return useQuery({
    queryKey: ['hook', id],
    queryFn: () => api.getHook(id),
    enabled: !!id,
  })
}

export function useTools() {
  return useQuery({ queryKey: ['tools'], queryFn: api.listTools })
}

export function useTool(id: string) {
  return useQuery({
    queryKey: ['tool', id],
    queryFn: () => api.getTool(id),
    enabled: !!id,
  })
}

export function useRunAgent() {
  return useMutation({
    mutationFn: ({ task, params }: { task: string; params?: Record<string, unknown> }) =>
      api.runAgent(task, params),
  })
}

export function useRuns(limit = 50, offset = 0) {
  return useQuery({
    queryKey: ['runs', limit, offset],
    queryFn: () => api.listRuns(limit, offset),
  })
}

export function useRun(id: string) {
  return useQuery({
    queryKey: ['run', id],
    queryFn: () => api.getRun(id),
    enabled: !!id,
  })
}

export function useRunEvents(id: string, limit = 500) {
  return useQuery({
    queryKey: ['runEvents', id],
    queryFn: () => api.getRunEvents(id, limit),
    enabled: !!id,
  })
}
