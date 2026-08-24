import React, { useState, useEffect } from 'react';
import { getUserBookingHistory, cancelBookingApi, resendBookingEmailApi } from '../api';
import type { BookingItem } from '../types';
import { History, Mail, XCircle, AlertTriangle, RefreshCw, CheckCircle2, Ticket } from 'lucide-react';

export const HistoryPage: React.FC = () => {
  const [bookings, setBookings] = useState<BookingItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [msgBanner, setMsgBanner] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const data = await getUserBookingHistory();
      setBookings(data);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleCancel = async (bookingId: string) => {
    try {
      setActionLoadingId(bookingId);
      const res = await cancelBookingApi(bookingId);
      if (res.success) {
        setMsgBanner({ text: 'Booking cancelled. Seat returned / offered to waitlist.', type: 'success' });
        fetchHistory();
      } else {
        setMsgBanner({ text: res.message || 'Could not cancel booking.', type: 'error' });
      }
    } catch (err: any) {
      setMsgBanner({ text: err.response?.data?.message || 'Error cancelling booking.', type: 'error' });
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleResendEmail = async (bookingId: string) => {
    try {
      setActionLoadingId(bookingId);
      const res = await resendBookingEmailApi(bookingId);
      if (res.success) {
        setMsgBanner({ text: 'Confirmation QR M-Ticket email resend queued!', type: 'success' });
        fetchHistory();
      } else {
        setMsgBanner({ text: res.message || 'Resend email failed.', type: 'error' });
      }
    } catch (err: any) {
      setMsgBanner({ text: err.response?.data?.message || 'Error resending email.', type: 'error' });
    } finally {
      setActionLoadingId(null);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-black text-white flex items-center gap-2">
            My Booking <span className="text-[#d84e55]">History</span>
          </h2>
          <p className="text-xs text-zinc-400">View confirmed M-Tickets, QR codes, or cancel bookings</p>
        </div>
        <button
          onClick={fetchHistory}
          className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white bg-[#1c1d2b] px-3.5 py-2 rounded-xl border border-[#2e3046] transition-all cursor-pointer"
        >
          <RefreshCw className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* Message Banner */}
      {msgBanner && (
        <div
          className={`p-4 rounded-2xl text-xs flex items-center justify-between border ${
            msgBanner.type === 'success'
              ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
              : 'bg-red-500/10 text-red-400 border-red-500/30'
          }`}
        >
          <span>{msgBanner.text}</span>
          <button onClick={() => setMsgBanner(null)} className="text-zinc-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Loading state */}
      {loading ? (
        <div className="cinestream-card p-12 rounded-3xl text-center text-zinc-400">
          <div className="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
          Loading your M-Tickets...
        </div>
      ) : bookings.length === 0 ? (
        <div className="cinestream-card p-12 rounded-3xl text-center text-zinc-400 space-y-3">
          <History className="w-10 h-10 mx-auto text-zinc-600" />
          <p className="text-sm font-bold">No bookings found</p>
          <p className="text-xs text-zinc-500">Hold and confirm a seat on the Now Showing page to see your ticket here.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {bookings.map((booking) => {
            const isCancelled = booking.status === 'cancelled';
            const isActionBusy = actionLoadingId === booking.id;

            return (
              <div
                key={booking.id}
                className="cinestream-card p-6 rounded-3xl space-y-4 border border-[#262626] relative overflow-hidden bg-[#171717]"
              >
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[#262626] pb-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
                      <Ticket className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-base font-bold text-white">{booking.event_title}</h3>
                        <span
                          className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase ${
                            isCancelled
                              ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                              : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          }`}
                        >
                          {booking.status}
                        </span>
                      </div>
                      <p className="text-xs text-zinc-400">Ref: <span className="font-mono text-cyan-400 font-bold">{booking.booking_reference}</span></p>
                    </div>
                  </div>

                  <div className="text-right">
                    <div className="text-lg font-black text-[#d84e55]">₹{booking.amount}</div>
                    <div className="text-[11px] text-zinc-500">{new Date(booking.created_at).toLocaleDateString()}</div>
                  </div>
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 text-xs">
                  <div>
                    <span className="text-zinc-500 block">Boarding Terminal</span>
                    <span className="text-white font-medium">{booking.venue_name}</span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block">Seat Reserved</span>
                    <span className="text-[#d84e55] font-bold">
                      Row {booking.seat.row_name}, Seat {booking.seat.col_number} ({booking.seat.category_name})
                    </span>
                  </div>
                  <div>
                    <span className="text-zinc-500 block">Departure Time</span>
                    <span className="text-white font-medium">{new Date(booking.start_time).toLocaleString()}</span>
                  </div>
                </div>

                {/* Email Delivery Warning & Resend Button */}
                {!isCancelled && (
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-zinc-800/60">
                    {booking.email_delivery_failed ? (
                      <div className="flex items-center gap-2 text-xs text-amber-400 bg-amber-500/10 px-3 py-1.5 rounded-xl border border-amber-500/20">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                        <span>Email notice delayed. Your M-Ticket is saved safely here.</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 text-xs text-emerald-400">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>QR M-Ticket issued & emailed</span>
                      </div>
                    )}

                    <div className="flex items-center gap-2 ml-auto">
                      <button
                        onClick={() => handleResendEmail(booking.id)}
                        disabled={isActionBusy}
                        className="flex items-center gap-1.5 text-xs bg-[#1c1d2b] hover:bg-zinc-800 text-zinc-300 px-3 py-1.5 rounded-xl border border-[#2e3046] transition-all cursor-pointer disabled:opacity-50 font-bold"
                      >
                        <Mail className="w-3.5 h-3.5" />
                        Resend QR Ticket
                      </button>

                      <button
                        onClick={() => handleCancel(booking.id)}
                        disabled={isActionBusy}
                        className="flex items-center gap-1.5 text-xs bg-red-500/10 hover:bg-red-500/20 text-red-400 px-3 py-1.5 rounded-xl border border-red-500/30 transition-all cursor-pointer disabled:opacity-50 font-bold"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        Cancel Booking
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
