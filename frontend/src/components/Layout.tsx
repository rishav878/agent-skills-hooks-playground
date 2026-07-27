import { NavLink, Outlet } from 'react-router-dom'
import { useHealth } from '../hooks/useApi'

const links = [
  { to: '/', label: 'Dashboard' },
  { to: '/playground', label: 'Playground' },
  { to: '/skills', label: 'Skills' },
  { to: '/hooks', label: 'Hooks' },
  { to: '/tools', label: 'Tools' },
  { to: '/runs', label: 'Run History' },
]

export default function Layout() {
  const { data: health } = useHealth()

  return (
    <div className="flex h-screen">
      <aside className="w-56 bg-gray-900 text-white flex flex-col shrink-0">
        <div className="p-4 border-b border-gray-700">
          <h1 className="text-lg font-bold">Agent Playground</h1>
          <p className="text-xs text-gray-400 mt-1">
            {health?.status === 'ok'
              ? 'Backend Connected'
              : 'Backend Offline'}
          </p>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === '/'}
              className={({ isActive }) =>
                `block px-3 py-2 rounded text-sm transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-gray-800'
                }`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 border-t border-gray-700 text-xs text-gray-500">
          v0.1.0
        </div>
      </aside>
      <main className="flex-1 overflow-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
