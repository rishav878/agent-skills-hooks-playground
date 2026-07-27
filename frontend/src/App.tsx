import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Playground from './pages/Playground'
import Skills from './pages/Skills'
import Hooks from './pages/Hooks'
import Tools from './pages/Tools'
import RunHistory from './pages/RunHistory'
import RunDetails from './pages/RunDetails'
import Settings from './pages/Settings'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      staleTime: 10_000,
      refetchOnWindowFocus: false,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/playground" element={<Playground />} />
            <Route path="/skills" element={<Skills />} />
            <Route path="/hooks" element={<Hooks />} />
            <Route path="/tools" element={<Tools />} />
            <Route path="/runs" element={<RunHistory />} />
            <Route path="/runs/:id" element={<RunDetails />} />
            <Route path="/settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
