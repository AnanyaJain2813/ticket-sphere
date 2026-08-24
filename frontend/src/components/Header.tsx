import React from 'react';
import { NavLink } from 'react-router-dom';
import { MapPin, UserCheck, LogOut, Film } from 'lucide-react';
import { HoldCountdownRing } from './HoldCountdownRing';
import { useAuth } from '../contexts/AuthContext';
import type { ActiveHold } from '../types';

interface HeaderProps {
  activeHolds: ActiveHold[];
}

export const Header: React.FC<HeaderProps> = ({
  activeHolds,
}) => {
  const { user, logout } = useAuth();
  
  // Safety check, though the router should prevent this
  if (!user) return null;

  return (
    <header className="bg-[#0a0a0a] border-b border-[#262626] sticky top-0 z-40 shadow-sm backdrop-blur-md bg-opacity-90">
      {/* Top CineStream Cyan Accent Stripe */}
      <div className="h-1 bg-gradient-to-r from-cyan-600 via-cyan-400 to-teal-400" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* CineStream Brand */}
        <div className="flex items-center gap-6">
          <NavLink to="/" className="flex items-center gap-3 group">
            <div className="p-2 bg-[#171717] rounded-xl border border-[#262626] shadow-[0_0_15px_rgba(6,182,212,0.15)] group-hover:border-cyan-500/50 transition-colors">
              <Film className="w-6 h-6 text-cyan-400" />
            </div>
            <div className="text-2xl font-black text-white tracking-tight leading-none">
              TicketSphere
              <span className="text-[9px] font-bold text-cyan-500 uppercase tracking-widest block font-sans text-left mt-0.5">
                TICKET BOOKING PLATFORM
              </span>
            </div>
          </NavLink>

          {/* Location Selector */}
          <div className="hidden sm:flex items-center gap-2 text-xs font-semibold text-zinc-300 bg-[#171717] px-4 py-2 rounded-full border border-[#262626] hover:bg-[#262626] hover:border-cyan-500/30 transition-all cursor-pointer">
            <MapPin className="w-4 h-4 text-cyan-500" />
            <div>
              <span className="font-bold text-white block leading-tight">India (All Cities)</span>
              <span className="text-[10px] text-zinc-500 block leading-tight">Delhi NCR • Mumbai • Bangalore</span>
            </div>
          </div>
        </div>

        {/* Navigation Category Pills */}
        <nav className="flex items-center gap-2">
          {user.role === 'customer' ? (
            <>
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `px-5 py-2 rounded-full text-xs font-bold transition-all ${
                    isActive
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                      : 'text-zinc-400 border border-transparent hover:text-white hover:bg-[#171717] hover:border-[#262626]'
                  }`
                }
              >
                Now Showing
              </NavLink>

              <NavLink
                to="/history"
                className={({ isActive }) =>
                  `px-5 py-2 rounded-full text-xs font-bold transition-all ${
                    isActive
                      ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 shadow-[0_0_10px_rgba(6,182,212,0.2)]'
                      : 'text-zinc-400 border border-transparent hover:text-white hover:bg-[#171717] hover:border-[#262626]'
                  }`
                }
              >
                My Tickets
              </NavLink>
            </>
          ) : (
            <NavLink
              to="/organiser"
              className={({ isActive }) =>
                `px-5 py-2 rounded-full text-xs font-bold transition-all ${
                  isActive
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.2)]'
                    : 'text-zinc-400 border border-transparent hover:text-white hover:bg-[#171717] hover:border-[#262626]'
                }`
              }
            >
              Box Office Analytics
            </NavLink>
          )}
        </nav>

        {/* Search & Profile Widget */}
        <div className="flex items-center gap-4">
          {user.role === 'customer' && activeHolds.length > 0 && (
            <div className="flex items-center gap-2 bg-cyan-900/30 border border-cyan-700/50 px-3 py-1.5 rounded-full shadow-[0_0_15px_rgba(6,182,212,0.1)]">
              <HoldCountdownRing 
                expiresAt={activeHolds.reduce((min, hold) => (new Date(hold.expiresAt) < new Date(min) ? hold.expiresAt : min), activeHolds[0].expiresAt)} 
                size={30} strokeWidth={2.5} 
              />
              <div className="flex flex-col">
                <span className="text-[9px] font-black uppercase text-cyan-400 leading-none">{activeHolds.length} Seat{activeHolds.length > 1 ? 's' : ''}</span>
                <span className="text-[10px] text-zinc-300 leading-tight font-medium">Reserved</span>
              </div>
            </div>
          )}

          {/* User Display */}
          <div className="flex items-center gap-2 bg-[#171717] px-4 py-2 rounded-full border border-[#262626]">
            <UserCheck className="w-4 h-4 text-cyan-500" />
            <span className="text-xs font-bold text-white capitalize">{user.username} ({user.role})</span>
          </div>

          <button
            onClick={logout}
            className="flex items-center gap-1.5 text-xs bg-[#171717] hover:bg-red-500/10 border border-[#262626] hover:border-red-500/50 hover:text-red-400 text-white px-4 py-2 rounded-full transition-all cursor-pointer font-bold shadow-lg"
          >
            <LogOut className="w-3.5 h-3.5" /> Logout
          </button>
        </div>
      </div>
    </header>
  );
};
