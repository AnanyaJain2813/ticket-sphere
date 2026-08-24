import React, { useState } from 'react';
import { Film, BarChart3, Ticket, ArrowRight, Key, Mail, User as UserIcon } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { loginApi, registerApi } from '../api';

export const AuthScreen: React.FC = () => {
  const { login } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [role, setRole] = useState<'customer' | 'organiser'>('organiser');
  const [username, setUsername] = useState('organizer');
  const [password, setPassword] = useState('12345678');
  const [email, setEmail] = useState('organizer@gmail.com');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      if (mode === 'register') {
        const regData = await registerApi({ username, email, password, role });
        login(regData.tokens.access, regData.user);
      } else {
        const data = await loginApi({ username, password });
        login(data.access || data.token, data.user);
      }
    } catch (err: any) {
      const data = err.response?.data;
      let msg = 'Authentication failed. Please check your credentials.';
      if (!err.response) {
        msg = 'Network connection failed. Please ensure the backend is running and the Vercel API URL is configured correctly.';
      } else if (typeof data === 'string') {
        msg = data;
      } else if (data?.error) {
        msg = data.error;
      } else if (data?.message) {
        msg = data.message;
      } else if (data?.detail) {
        msg = data.detail;
      } else if (data && typeof data === 'object') {
        const key = Object.keys(data)[0];
        const val = data[key];
        if (Array.isArray(val)) {
          msg = `${key.toUpperCase()}: ${val[0]}`;
        } else if (typeof val === 'string') {
          msg = `${key.toUpperCase()}: ${val}`;
        }
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center p-4 max-w-md mx-auto space-y-8 animate-fadeIn w-full">
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 bg-cyan-950/40 border border-cyan-500/30 px-4 py-1.5 rounded-full text-cyan-400 text-xs font-black tracking-widest uppercase shadow-[0_0_15px_rgba(6,182,212,0.15)]">
          <Ticket className="w-4 h-4" /> TicketSphere Platform
        </div>
        <h1 className="text-3xl sm:text-4xl font-black text-white tracking-tight">
          {mode === 'login' ? 'Welcome Back' : 'Create Account'}
        </h1>
      </div>

      <div className="cinestream-card w-full p-8 rounded-3xl border border-[#262626] bg-[#171717] shadow-2xl relative overflow-hidden">
        <div className="flex gap-4 mb-8 bg-black/40 p-1.5 rounded-2xl border border-white/5">
          <button
            onClick={() => setMode('login')}
            className={`flex-1 py-2 text-sm font-bold rounded-xl transition-all ${
              mode === 'login' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'text-zinc-500 hover:text-white'
            }`}
          >
            Login
          </button>
          <button
            onClick={() => setMode('register')}
            className={`flex-1 py-2 text-sm font-bold rounded-xl transition-all ${
              mode === 'register' ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'text-zinc-500 hover:text-white'
            }`}
          >
            Register
          </button>
        </div>

        {error && (
          <div className="mb-6 p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-sm font-medium text-center">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === 'register' && (
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-zinc-400 ml-1 uppercase tracking-wider">Account Role</label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setRole('customer')}
                  className={`flex items-center justify-center gap-2 py-3 rounded-xl border transition-all ${
                    role === 'customer' 
                      ? 'border-cyan-500 bg-cyan-500/10 text-cyan-400' 
                      : 'border-[#262626] bg-black/50 text-zinc-500 hover:border-zinc-700'
                  }`}
                >
                  <Film className="w-4 h-4" /> Customer
                </button>
                <button
                  type="button"
                  onClick={() => setRole('organiser')}
                  className={`flex items-center justify-center gap-2 py-3 rounded-xl border transition-all ${
                    role === 'organiser' 
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400' 
                      : 'border-[#262626] bg-black/50 text-zinc-500 hover:border-zinc-700'
                  }`}
                >
                  <BarChart3 className="w-4 h-4" /> Organiser
                </button>
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-zinc-400 ml-1 uppercase tracking-wider">Username</label>
            <div className="relative">
              <UserIcon className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                required
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-black/50 border border-[#262626] focus:border-cyan-500 rounded-xl py-3 pl-12 pr-4 text-white placeholder-zinc-600 transition-colors outline-none"
                placeholder="Enter username"
              />
            </div>
          </div>

          {mode === 'register' && (
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-zinc-400 ml-1 uppercase tracking-wider">Email</label>
              <div className="relative">
                <Mail className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" />
                <input
                  required
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-black/50 border border-[#262626] focus:border-cyan-500 rounded-xl py-3 pl-12 pr-4 text-white placeholder-zinc-600 transition-colors outline-none"
                  placeholder="Enter email address"
                />
              </div>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-zinc-400 ml-1 uppercase tracking-wider">Password</label>
            <div className="relative">
              <Key className="w-5 h-5 absolute left-4 top-1/2 -translate-y-1/2 text-zinc-500" />
              <input
                required
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-black/50 border border-[#262626] focus:border-cyan-500 rounded-xl py-3 pl-12 pr-4 text-white placeholder-zinc-600 transition-colors outline-none"
                placeholder="Enter password"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-cyan-500 hover:bg-cyan-400 text-cyan-950 font-black py-4 rounded-xl mt-6 flex items-center justify-center gap-2 transition-colors shadow-[0_0_20px_rgba(6,182,212,0.3)] hover:shadow-[0_0_30px_rgba(6,182,212,0.5)] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <span className="animate-pulse">Processing...</span>
            ) : (
              <>
                {mode === 'login' ? 'Secure Login' : 'Create Account'}
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
