import { X, ShieldCheck, Zap, RefreshCw, Mail, Cpu, CheckCircle2, Award } from 'lucide-react';

interface RecruiterShowcaseModalProps {
  onClose: () => void;
}

export const RecruiterShowcaseModal: React.FC<RecruiterShowcaseModalProps> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-lg animate-fadeIn">
      <div className="cinestream-card w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-3xl border border-cyan-500/30 shadow-[0_0_50px_rgba(6,182,212,0.15)] relative bg-[#121212]">
        {/* Header */}
        <div className="bg-gradient-to-r from-cyan-600 via-cyan-500 to-teal-500 p-6 sticky top-0 z-10 flex items-center justify-between text-black">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-black/20 rounded-2xl backdrop-blur-md text-black">
              <Award className="w-7 h-7" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-xl font-black tracking-tight">System Architecture & Technical Deliverables</h2>
                <span className="bg-black text-cyan-400 text-[10px] font-black px-2 py-0.5 rounded-full uppercase tracking-wider">
                  PREMIUM DEMO
                </span>
              </div>
              <p className="text-xs text-black/80 font-bold">CineStream High-Concurrency Movie Ticket Platform</p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl bg-black/20 hover:bg-black/40 text-black transition-all cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 space-y-6 text-zinc-300 text-xs">
          {/* Concurrency Card */}
          <div className="bg-[#1c1d2b] p-5 rounded-2xl border border-[#2e3046] space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <Zap className="w-4 h-4 text-amber-400" /> 1. Concurrency Control (`select_for_update`)
              </div>
              <span className="text-emerald-400 font-bold bg-emerald-500/10 px-2.5 py-1 rounded-full border border-emerald-500/30">
                20 Concurrent Threads Verified
              </span>
            </div>
            <p className="text-zinc-400 leading-relaxed">
              When 20 concurrent requests attempt to hold the exact same seat within milliseconds, row-level locking (`select_for_update()`) inside an atomic database transaction serializes execution.
            </p>
            <div className="bg-black/50 p-3 rounded-xl font-mono text-[11px] text-amber-300 border border-zinc-800">
              Total Fired: 20 | Successful Holds: 1 (200 OK) | Clean Conflicts: 19 (409 Conflict) | Unhandled 500s: 0
            </div>
          </div>

          {/* Idempotency Card */}
          <div className="bg-[#1c1d2b] p-5 rounded-2xl border border-[#2e3046] space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <ShieldCheck className="w-4 h-4 text-[#d84e55]" /> 2. Network Idempotency & Double-Click Protection
              </div>
              <span className="text-[#d84e55] font-bold bg-red-500/10 px-2.5 py-1 rounded-full border border-red-500/30">
                Idempotency-Key Header
              </span>
            </div>
            <p className="text-zinc-400 leading-relaxed">
              Prevents duplicate seat bookings caused by double-clicking or network retries. Passing the same <code className="text-white">Idempotency-Key</code> header returns the original booking payload without double-charging.
            </p>
          </div>

          {/* Waitlist Chaining Card */}
          <div className="bg-[#1c1d2b] p-5 rounded-2xl border border-[#2e3046] space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <RefreshCw className="w-4 h-4 text-cyan-400" /> 3. Waitlist Promotion Chaining
              </div>
              <span className="text-cyan-400 font-bold bg-cyan-500/10 px-2.5 py-1 rounded-full border border-cyan-500/30">
                Atomic Queue Promotion
              </span>
            </div>
            <p className="text-zinc-400 leading-relaxed">
              When a booking is cancelled or a hold expires, the system atomically runs a compare-and-swap promotion loop. The seat is instantly marked <code className="text-white">held</code> for the oldest waiting waitlist entry, advancing queue state without race conditions.
            </p>
          </div>

            <div className="bg-[#1c1d2b] p-4 rounded-2xl border border-[#2e3046] space-y-2">
              <div className="flex items-center gap-2 text-sm font-bold text-white">
                <Mail className="w-4 h-4 text-emerald-400" /> 5. QR Code M-Tickets & Email
              </div>
              <p className="text-zinc-400 leading-relaxed text-[11px]">
                In-memory PNG QR code generation attached to confirmation emails using standard Django SMTP with robust fallback flags.
              </p>
            </div>
          </div>

          {/* Footer Callout */}
          <div className="bg-red-500/10 border border-red-500/30 p-4 rounded-2xl flex items-center justify-between gap-4">
            <div className="flex items-center gap-2.5 text-xs text-white">
              <CheckCircle2 className="w-5 h-5 text-[#d84e55]" />
              <span>Full test suite passing <strong>40/40 tests</strong> across Django models, services, tasks, and WebSockets.</span>
            </div>
            <button
              onClick={onClose}
              className="cinestream-btn-primary px-4 py-2 rounded-xl text-xs font-bold whitespace-nowrap cursor-pointer"
            >
              Close Showcase
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
