/**
 * OutfitAR - Layout Premium dengan Fluid Island Nav & Bottom Tab Bar (Mobile)
 */
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { TShirt, Scan, Sparkle, Package, House, SignOut } from '@phosphor-icons/react'
import useStore from '../../store/useStore'

const NAV_ITEMS = [
  { to: '/',       label: 'Beranda',    icon: House },
  { to: '/skin-tone',      label: 'Skin Tone',  icon: Scan },
  { to: '/recommendations',label: 'Rekomendasi',icon: Sparkle },
  { to: '/products',       label: 'Produk',     icon: Package },
]

export default function Layout() {
  const { user, clearAuth } = useStore()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col relative overflow-hidden">
      {/* Subtle Ethereal Glass Background Effect */}
      <div className="fixed inset-0 pointer-events-none z-[-1] overflow-hidden">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-violet-600/10 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[60%] h-[60%] rounded-full bg-pink-600/10 blur-[120px]" />
      </div>

      {/* ── Fluid Island Nav Desktop ── */}
      <header className="hidden md:flex justify-center sticky top-6 z-50 px-4 w-full">
        <div className="flex items-center justify-between w-full max-w-4xl px-4 py-2.5 rounded-full bg-black/40 backdrop-blur-2xl border border-white/10 shadow-[0_8px_32px_rgba(0,0,0,0.4)] transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)]">
          {/* Logo */}
          <NavLink to="/" className="flex items-center gap-2.5 pl-2 group">
            <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center border border-white/10 group-hover:bg-white/10 transition-colors">
              <TShirt size={18} weight="light" className="text-white" />
            </div>
            <span className="font-display font-semibold text-base text-white tracking-wide">
              OutfitAR
            </span>
          </NavLink>

          {/* Nav Links */}
          <nav className="flex items-center gap-1 absolute left-1/2 -translate-x-1/2">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-2 px-4 py-2 rounded-full text-sm transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] ${
                    isActive
                      ? 'bg-white/10 text-white shadow-[inset_0_1px_1px_rgba(255,255,255,0.15)]'
                      : 'text-white/50 hover:text-white hover:bg-white/5'
                  }`
                }
              >
                <Icon size={18} weight="light" />
                <span className="font-medium">{label}</span>
              </NavLink>
            ))}
          </nav>

          {/* User Button */}
          <div className="flex items-center gap-2 pr-2">
            {user ? (
              <>
                <span className="text-sm text-white/50 font-medium px-2">{user.name}</span>
                <button
                  onClick={() => { clearAuth(); navigate('/') }}
                  className="w-8 h-8 flex items-center justify-center rounded-full text-white/50 hover:text-white hover:bg-white/10 transition-colors"
                >
                  <SignOut size={18} weight="light" />
                </button>
              </>
            ) : (
              <button 
                onClick={() => navigate('/login')} 
                className="btn-premium text-white font-medium text-sm px-5 py-2 flex items-center bg-white/5 border border-white/10"
              >
                Masuk
              </button>
            )}
          </div>
        </div>
      </header>

      {/* ── Content ── */}
      <main className="flex-1 pb-24 md:pb-0 pt-6 md:pt-12">
        <Outlet />
      </main>

      {/* ── Floating Bottom Tab Bar (Mobile Only) ── */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 md:hidden">
        <div className="mx-4 mb-6 rounded-[2rem] bg-black/60 backdrop-blur-2xl border border-white/10 shadow-[0_-8px_32px_rgba(0,0,0,0.5),inset_0_1px_1px_rgba(255,255,255,0.1)] p-2">
          <div className="flex justify-between items-center">
            {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex-1 flex flex-col items-center justify-center py-2 rounded-[1.5rem] relative transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] ${
                    isActive ? 'bg-white/10 text-white' : 'text-white/40 active:text-white/60'
                  }`
                }
              >
                <Icon size={24} weight="light" />
                <span className="text-[10px] font-medium tracking-wide mt-1">
                  {label}
                </span>
              </NavLink>
            ))}
          </div>
        </div>
      </nav>
    </div>
  )
}