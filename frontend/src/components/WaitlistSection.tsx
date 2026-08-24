import React, { useState, useEffect } from 'react';
import { getUserWaitlistApi, joinWaitlistApi, cancelWaitlistApi } from '../api';
import type { WaitlistEntryItem, SeatItem } from '../types';
import { HoldCountdownRing } from './HoldCountdownRing';
import { Users, PlusCircle, RefreshCw, XCircle } from 'lucide-react';

interface WaitlistSectionProps {
  showId: string | null;
  seats: SeatItem[];
}

export const WaitlistSection: React.FC<WaitlistSectionProps> = ({
  showId,
  seats,
}) => {
  const [waitlistEntries, setWaitlistEntries] = useState<WaitlistEntryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [joiningCategory, setJoiningCategory] = useState<string | null>(null);
  const [msgBanner, setMsgBanner] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchWaitlist = async () => {
    try {
      setLoading(true);
      const data = await getUserWaitlistApi();
      setWaitlistEntries(data);
    } catch (err) {
      console.error('Failed to fetch waitlist:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWaitlist();
  }, [showId]);

  // Extract unique seat categories for this show
  const categoryMap = Array.from(
    new Map(seats.map((s) => [s.category_name, s])).values()
  );

  const handleJoin = async (categoryId: string, categoryName: string) => {
    if (!showId) return;
    try {
      setMsgBanner(null);
      setJoiningCategory(categoryId);
      const res = await joinWaitlistApi(showId, categoryId);
      if (res.success) {
        setMsgBanner({ text: `Joined waitlist for ${categoryName}!`, type: 'success' });
        fetchWaitlist();
      } else {
        setMsgBanner({ text: res.message || 'Could not join waitlist.', type: 'error' });
      }
    } catch (err: any) {
      setMsgBanner({ text: err.response?.data?.message || 'Error joining waitlist.', type: 'error' });
    } finally {
      setJoiningCategory(null);
    }
  };

  const handleCancelWaitlist = async (entryId: string) => {
    try {
      const res = await cancelWaitlistApi(entryId);
      if (res.success) {
        setMsgBanner({ text: 'Waitlist entry cancelled. Next person promoted!', type: 'success' });
        fetchWaitlist();
      } else {
        setMsgBanner({ text: res.message || 'Could not cancel waitlist.', type: 'error' });
      }
    } catch (err: any) {
      setMsgBanner({ text: err.response?.data?.message || 'Error cancelling waitlist.', type: 'error' });
    }
  };

  return (
    <div className="cinestream-card p-6 rounded-3xl space-y-5 border border-[#262626] bg-[#171717]">
      {/* Section Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#262626] pb-4">
        <div>
          <h3 className="text-lg font-black text-white flex items-center gap-2">
            <Users className="w-5 h-5 text-cyan-400" /> Queue & Waitlist Management
          </h3>
          <p className="text-xs text-zinc-400">Join waitlists when seats sell out — auto-promoted when holds expire or cancel</p>
        </div>

        <button
          onClick={fetchWaitlist}
          className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white bg-[#171717] px-3.5 py-1.5 rounded-xl border border-[#262626] hover:border-cyan-500/30 transition-all cursor-pointer font-bold"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh Queue
        </button>
      </div>

      {/* Message Banner */}
      {msgBanner && (
        <div
          className={`p-3 rounded-2xl text-xs flex items-center justify-between border ${
            msgBanner.type === 'success'
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-red-500/10 text-red-400 border-red-500/30'
          }`}
        >
          <span>{msgBanner.text}</span>
          <button onClick={() => setMsgBanner(null)} className="text-zinc-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Join Waitlist Actions */}
      <div className="space-y-3">
        <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Join Waitlist Queue by Class</h4>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {categoryMap.map((catSeat) => {
            const availableCount = seats.filter(
              (s) =>
                (s.category_id === catSeat.category_id || s.category_name === catSeat.category_name) &&
                s.status === 'available'
            ).length;
            const isSoldOut = availableCount === 0;

            return (
              <button
                key={catSeat.category_id || catSeat.category_name}
                onClick={() => {
                  if (!isSoldOut) {
                    setMsgBanner({
                      text: `Seats are still available for ${catSeat.category_name}! Select an available seat on the map above to book directly.`,
                      type: 'error',
                    });
                    return;
                  }
                  if (!catSeat.category_id) {
                    setMsgBanner({
                      text: 'Backend is still deploying... Please wait a minute and refresh the page.',
                      type: 'error',
                    });
                    return;
                  }
                  handleJoin(catSeat.category_id, catSeat.category_name);
                }}
                disabled={joiningCategory === catSeat.category_id || !isSoldOut}
                className={`flex items-center justify-between p-3 rounded-xl transition-all border text-left group ${
                  isSoldOut
                    ? 'bg-[#1c1d2b] hover:bg-[#25273a] border-[#2e3046] cursor-pointer'
                    : 'bg-[#141522]/50 border-zinc-800/40 opacity-70 cursor-not-allowed'
                }`}
              >
                <div>
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="text-xs font-bold text-white block">{catSeat.category_name}</span>
                    {isSoldOut ? (
                      <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase bg-red-500/20 text-red-400 border border-red-500/30">
                        Sold Out
                      </span>
                    ) : (
                      <span className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                        {availableCount} Available
                      </span>
                    )}
                  </div>
                  <span className="text-[10px] text-[#d84e55] font-bold">₹{catSeat.price}</span>
                </div>
                {isSoldOut ? (
                  <PlusCircle className="w-4 h-4 text-[#d84e55] group-hover:scale-110 transition-transform shrink-0" />
                ) : (
                  <span className="text-[10px] text-emerald-400 font-semibold bg-emerald-500/10 px-2 py-1 rounded-lg border border-emerald-500/20 shrink-0">
                    Book Above
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* User's Active Waitlist Entries */}
      <div className="space-y-3 pt-2">
        <h4 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">My Active Queue Entries</h4>
        {loading ? (
          <div className="text-xs text-zinc-500 py-4 text-center">Loading queue entries...</div>
        ) : waitlistEntries.length === 0 ? (
          <div className="text-xs text-zinc-500 bg-[#1c1d2b] p-4 rounded-2xl text-center border border-[#2e3046]">
            You have no active waitlist queue entries for this show.
          </div>
        ) : (
          <div className="space-y-2">
            {waitlistEntries.map((entry, idx) => {
              const isOffered = entry.status === 'offered';
              const isWaiting = entry.status === 'waiting';

              return (
                <div
                  key={entry.id}
                  className="flex items-center justify-between bg-[#1c1d2b] p-3.5 rounded-2xl border border-[#2e3046] text-xs"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-xl bg-zinc-800 text-amber-400 font-bold flex items-center justify-center text-xs">
                      #{idx + 1}
                    </div>
                    <div>
                      <div className="font-bold text-white">{entry.event_title} ({entry.category_name})</div>
                      <div className="text-[10px] text-zinc-400">Joined: {new Date(entry.created_at).toLocaleTimeString()}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    {isOffered && entry.offer_expires_at ? (
                      <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 rounded-xl">
                        <HoldCountdownRing expiresAt={entry.offer_expires_at} size={28} strokeWidth={2} />
                        <span className="text-emerald-400 font-bold text-[11px]">SEAT OFFERED!</span>
                      </div>
                    ) : isWaiting ? (
                      <span className="bg-amber-500/10 text-amber-400 px-2.5 py-1 rounded-full border border-amber-500/30 font-bold text-[10px]">
                        Waiting in Queue
                      </span>
                    ) : (
                      <span className="bg-zinc-800 text-zinc-500 px-2.5 py-1 rounded-full text-[10px]">
                        {entry.status}
                      </span>
                    )}

                    <button
                      onClick={() => handleCancelWaitlist(entry.id)}
                      className="text-zinc-500 hover:text-red-400 p-1 transition-colors cursor-pointer"
                      title="Cancel Waitlist Entry"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
