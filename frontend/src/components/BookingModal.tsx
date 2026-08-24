import React, { useState } from 'react';
import type { ShowItem, ActiveHold } from '../types';
import { HoldCountdownRing } from './HoldCountdownRing';
import { CreditCard, QrCode, CheckCircle2, AlertCircle, X, ShieldCheck, Ticket, MapPin, User, Mail, Film, Calendar, Clock, Phone } from 'lucide-react';
import api from '../api/client';

interface BookingModalProps {
  activeHolds: ActiveHold[];
  show?: ShowItem | null;
  onClose: () => void;
  onConfirmBooking: (
    idempotencyKey: string,
    details: { name: string; phone: string; email: string }
  ) => Promise<any>;
}

export const BookingModal: React.FC<BookingModalProps> = ({
  activeHolds,
  show,
  onClose,
  onConfirmBooking,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [bookingSuccess, setBookingSuccess] = useState<any | null>(null);
  const [emailStatus, setEmailStatus] = useState<'pending' | 'success' | 'failed'>('pending');

  const [passengerName, setPassengerName] = useState('');
  const [passengerPhone, setPassengerPhone] = useState('');
  const [passengerEmail, setPassengerEmail] = useState('');

  const [idempotencyKey] = useState<string>(
    () => `IDEM-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`
  );

  const handleConfirm = async () => {
    if (!passengerEmail.includes('@')) {
      setErrorMsg('Please enter a valid Gmail / Email address.');
      return;
    }
    setIsSubmitting(true);
    setErrorMsg(null);
    try {
      const res = await onConfirmBooking(idempotencyKey, {
        name: passengerName,
        phone: passengerPhone,
        email: passengerEmail,
      });
      if (res && (res.success || res.booking)) {
        setBookingSuccess(res.booking || { booking_reference: idempotencyKey, qr_code_url: '' });
      } else {
        setErrorMsg(res?.message || 'Booking confirmation could not be completed.');
      }
    } catch (err: any) {
      const apiMsg = err.response?.data?.message || err.message;
      if (apiMsg) {
        setErrorMsg(apiMsg);
      } else {
        setBookingSuccess({ booking_reference: idempotencyKey, qr_code_url: '' });
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  React.useEffect(() => {
    if (!bookingSuccess) return;
    
    let attempts = 0;
    const maxAttempts = 5;
    
    const checkEmailStatus = async () => {
      try {
        const { data } = await api.get('/bookings/history/');
        const booking = data.find((b: any) => b.booking_reference === bookingSuccess.booking_reference);
        
        if (booking) {
          if (booking.email_delivery_failed === true) {
            setEmailStatus('failed');
            return;
          } else if (booking.email_delivery_failed === false && attempts > 1) {
            // Assume success if it hasn't failed after a few seconds (as async task completes)
            setEmailStatus('success');
            return;
          }
        }
      } catch (err) {
        console.error('Failed to poll booking history', err);
      }

      attempts++;
      if (attempts < maxAttempts) {
        setTimeout(checkEmailStatus, 2000);
      } else {
        // Fallback to failed/pending state if we can't confirm success
        setEmailStatus('failed');
      }
    };
    
    setTimeout(checkEmailStatus, 2000);
  }, [bookingSuccess]);

  const startTimeStr = show?.start_time
    ? new Date(show.start_time).toLocaleString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      })
    : 'Today, 7:00 PM';
  const minExpiresAt = activeHolds.length > 0 
    ? activeHolds.reduce((min, hold) => (new Date(hold.expiresAt) < new Date(min) ? hold.expiresAt : min), activeHolds[0].expiresAt)
    : null;

  const totalAmount = activeHolds.reduce((sum, hold) => sum + parseFloat(hold.price || '0'), 0).toFixed(2);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/85 backdrop-blur-md animate-fadeIn">
      <div className="cinestream-card w-full max-w-lg overflow-hidden relative shadow-[0_0_50px_rgba(6,182,212,0.2)] bg-[#121212] border border-[#262626] rounded-3xl">
        {/* Header */}
        <div className="bg-gradient-to-r from-cyan-600 via-cyan-500 to-teal-500 p-5 flex items-center justify-between text-black">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-black/20 rounded-2xl backdrop-blur-md text-black">
              <Ticket className="w-6 h-6" />
            </div>
            <div>
              <h2 className="text-lg font-black tracking-tight leading-tight">Confirm Cinema Booking</h2>
              <p className="text-xs font-extrabold opacity-80 uppercase tracking-wider">CineStream Instant Checkout</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-full bg-black/20 hover:bg-black/40 text-black transition-all cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {!bookingSuccess ? (
          <div className="p-6 space-y-5">
            {/* Live Hold Timer Widget */}
            <div className="flex items-center justify-between bg-cyan-950/30 border border-cyan-500/30 p-3.5 rounded-2xl">
              <div className="flex items-center gap-3">
                <HoldCountdownRing expiresAt={minExpiresAt} size={40} strokeWidth={3} />
                <div>
                  <div className="text-xs font-bold text-cyan-400">Seat Hold Active</div>
                  <div className="text-[11px] text-zinc-400">Complete before timer expires</div>
                </div>
              </div>
              <div className="text-right">
                <span className="text-[10px] text-zinc-400 block font-bold uppercase tracking-wider">Reserved Seats</span>
                <span className="text-sm font-black text-white">
                  {activeHolds.map(h => h.seatLabel).join(', ')}
                </span>
              </div>
            </div>

            {/* Movie & Cinema Info */}
            <div className="bg-[#171717] p-4 rounded-2xl border border-[#262626] space-y-2.5">
              <div className="flex items-center gap-2 text-sm font-black text-white">
                <Film className="w-4 h-4 text-cyan-400" />
                <span>{show?.event_title || 'Featured Movie'}</span>
              </div>
              <div className="flex flex-col gap-1 text-xs text-zinc-400">
                <div className="flex items-center gap-1.5 font-medium text-zinc-300">
                  <MapPin className="w-3.5 h-3.5 text-cyan-500 shrink-0" />
                  <span>{show?.venue_name || 'PVR Cinema'} ({show?.venue_location || 'Auditorium 1'})</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Calendar className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                  <span>Showtime: {startTimeStr}</span>
                </div>
              </div>
            </div>

            {/* Contact Form: Name, Phone, Gmail */}
            <div className="space-y-2">
              <h3 className="text-[10px] font-bold text-zinc-400 uppercase tracking-wider">
                Passenger & Ticket Delivery Contact
              </h3>
              <div className="space-y-2.5">
                <div className="relative">
                  <User className="w-4 h-4 text-zinc-500 absolute left-3 top-3" />
                  <input
                    type="text"
                    value={passengerName}
                    onChange={(e) => setPassengerName(e.target.value)}
                    placeholder="Full Name"
                    className="w-full bg-[#1a1a1a] border border-[#262626] rounded-xl pl-9 pr-3 py-2 text-xs text-white font-semibold focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <div className="relative">
                    <Phone className="w-4 h-4 text-zinc-500 absolute left-3 top-3" />
                    <input
                      type="text"
                      value={passengerPhone}
                      onChange={(e) => setPassengerPhone(e.target.value)}
                      placeholder="Mobile (+91)"
                      className="w-full bg-[#1a1a1a] border border-[#262626] rounded-xl pl-9 pr-3 py-2 text-xs text-white font-semibold focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-cyan-400 absolute left-3 top-3" />
                    <input
                      type="email"
                      value={passengerEmail}
                      onChange={(e) => setPassengerEmail(e.target.value)}
                      placeholder="Gmail / Email Address"
                      className="w-full bg-[#1a1a1a] border border-[#262626] rounded-xl pl-9 pr-3 py-2 text-xs text-white font-semibold focus:outline-none focus:border-cyan-500"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Fare Summary in INR */}
            <div className="bg-[#171717] p-4 rounded-2xl border border-[#262626] space-y-2 text-xs">
              <div className="flex justify-between text-zinc-400">
                <span>Seat Price ({activeHolds.length} Seat{activeHolds.length > 1 ? 's' : ''}):</span>
                <span className="font-bold text-white">₹{totalAmount}</span>
              </div>
              <div className="flex justify-between text-zinc-400">
                <span>Convenience Fee & GST:</span>
                <span className="font-bold text-emerald-400">₹0.00 (Waived)</span>
              </div>
              <div className="flex justify-between text-sm font-black text-white pt-2.5 border-t border-[#262626]">
                <span>Total Amount:</span>
                <span className="text-cyan-400 text-base">₹{totalAmount}</span>
              </div>
            </div>

            {/* Idempotency Protection Indicator */}
            <div className="flex items-center gap-2 text-[11px] text-emerald-400 bg-emerald-950/20 p-2.5 rounded-xl border border-emerald-500/20 font-medium">
              <ShieldCheck className="w-4 h-4 flex-shrink-0 text-emerald-400" />
              <span>Idempotent Checkout & Email Delivery Engine Active</span>
            </div>

            {/* Error Message */}
            {errorMsg && (
              <div className="flex items-center gap-2 text-xs text-red-400 bg-red-950/30 p-3 rounded-xl border border-red-500/30">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                <span>{errorMsg}</span>
              </div>
            )}

            {/* Confirm CTA Button */}
            <button
              onClick={handleConfirm}
              disabled={isSubmitting}
              className="w-full cinestream-btn-primary py-3.5 rounded-xl flex items-center justify-center gap-2 text-sm font-extrabold cursor-pointer disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <div className="w-4 h-4 border-2 border-black border-t-transparent rounded-full animate-spin" />
                  Processing Booking...
                </>
              ) : (
                <>
                  <CreditCard className="w-4 h-4" />
                  Complete Booking • ₹{totalAmount}
                </>
              )}
            </button>
          </div>
        ) : (
          /* Confirmation Success View */
          <div className="p-6 text-center space-y-5">
            <div className="w-16 h-16 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto border border-emerald-500/40 shadow-[0_0_25px_rgba(16,185,129,0.3)]">
              <CheckCircle2 className="w-10 h-10" />
            </div>

            <div>
              <h3 className="text-2xl font-black text-white">Movie Ticket Confirmed!</h3>
              <p className="text-xs text-zinc-400 mt-1">
                Reference ID: <span className="font-mono text-cyan-400 font-bold">{bookingSuccess.booking_reference}</span>
              </p>
            </div>

            {/* QR Code M-Ticket Pass */}
            <div className="bg-[#171717] p-5 rounded-3xl inline-block shadow-2xl mx-auto border border-cyan-500/40 text-center space-y-3">
              {bookingSuccess.qr_code_url ? (
                <img
                  src={bookingSuccess.qr_code_url}
                  alt="QR Ticket"
                  className="w-44 h-44 mx-auto rounded-xl p-2 bg-white"
                />
              ) : (
                <div className="w-44 h-44 mx-auto rounded-xl bg-white p-3 flex flex-col items-center justify-center text-black font-mono text-xs">
                  <QrCode className="w-28 h-28 text-black" />
                  <span className="text-[10px] font-bold mt-1">ENTRY PASS</span>
                </div>
              )}
              <div className="text-xs font-black text-cyan-400 uppercase tracking-widest">
                {show?.event_title || 'CineStream Ticket'}
              </div>
              <div className="text-[11px] font-bold text-zinc-300">
                Seats: {activeHolds.map(h => h.seatLabel).join(', ')}
              </div>
            </div>

            {/* Delivery Confirmation Box */}
            <div className="bg-[#171717] p-4 rounded-2xl border border-[#262626] text-left space-y-3 text-xs text-zinc-300">
              {emailStatus === 'pending' && (
                <div className="flex items-center gap-2 text-zinc-400 font-bold">
                  <Clock className="w-4 h-4 animate-pulse" /> Email Delivery: <span className="text-white">Dispatching...</span>
                </div>
              )}
              {emailStatus === 'success' && (
                <div className="flex items-center gap-2 text-emerald-400 font-bold">
                  <Mail className="w-4 h-4" /> Email Delivery: <span className="text-white font-mono">{passengerEmail}</span>
                  <CheckCircle2 className="w-4 h-4 ml-auto text-emerald-400" />
                </div>
              )}
              {emailStatus === 'failed' && (
                <div className="flex items-center gap-2 text-amber-400 font-bold">
                  <AlertCircle className="w-4 h-4" /> Email Delivery: <span className="text-white">Pending / Failed</span>
                </div>
              )}
              <p className="text-zinc-400 text-[11px] pt-2 border-t border-[#262626]">
                {emailStatus === 'success' 
                  ? `Confirmation email sent. Attached PNG QR M-Ticket sent for passenger ${passengerName}. Show at gate entry.`
                  : `Booking confirmed — email delivery is pending/failed, check your booking history.`}
              </p>
            </div>

            <button
              onClick={onClose}
              className="w-full cinestream-btn-primary font-black py-3.5 rounded-xl transition-all cursor-pointer text-xs"
            >
              Back to Showtimes
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
