import React, { useState, useEffect, useCallback } from 'react';
import { getShows, getShowSeats, holdSeatApi, releaseSeatApi, confirmBookingApi } from '../api';
import type { ShowItem, SeatItem, ActiveHold } from '../types';
import { SeatMap } from '../components/SeatMap';
import { BookingModal } from '../components/BookingModal';
import { WaitlistSection } from '../components/WaitlistSection';
import { RecruiterShowcaseModal } from '../components/RecruiterShowcaseModal';
import { SearchWizard } from '../components/SearchWizard';
import { useWebSocket } from '../hooks/useWebSocket';
import { RefreshCw } from 'lucide-react';

interface BookingPageProps {
  activeHolds: ActiveHold[];
  setActiveHolds: (holds: ActiveHold[] | ((prev: ActiveHold[]) => ActiveHold[])) => void;
  onMovieSelect?: (bannerUrl: string) => void;
}

export const BookingPage: React.FC<BookingPageProps> = ({
  activeHolds,
  setActiveHolds,
  onMovieSelect,
}) => {
  const [shows, setShows] = useState<ShowItem[]>([]);
  const [selectedShowId, setSelectedShowId] = useState<string | null>(null);
  const [seats, setSeats] = useState<SeatItem[]>([]);
  const [holdingSeatId, setHoldingSeatId] = useState<string | null>(null);
  const [showCheckoutModal, setShowCheckoutModal] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [errorToast, setErrorToast] = useState<{ message: string; x: number; y: number } | null>(null);
  const [showRecruiterModal, setShowRecruiterModal] = useState<boolean>(false);

  useEffect(() => {
    const fetchShows = async () => {
      try {
        const data = await getShows();
        setShows(data);
        if (data.length > 0) {
          setSelectedShowId(data[0].id);
        }
      } catch (err) {
        console.error('Failed to load shows:', err);
        setErrorBanner('Failed to load shows from backend API.');
      }
    };
    fetchShows();
  }, []);

  const fetchSeatMap = useCallback(async (showId: string) => {
    try {
      const seatData = await getShowSeats(showId);
      setSeats(seatData);
      
      // Sync activeHolds from backend: replace holds for current show with exact holds returned
      const currentShowSeatIds = new Set(seatData.map((s) => s.id));
      const myHolds = seatData
        .filter((s) => s.status === 'held' && s.is_held_by_me && s.hold_expires_at)
        .map((s) => ({
          showSeatId: s.id,
          expiresAt: s.hold_expires_at as string,
          seatLabel: `${s.row_name}${s.col_number}`,
          price: s.price,
        }));
  
      setActiveHolds((prev: ActiveHold[]) => {
        const otherShowHolds = prev.filter((h) => !currentShowSeatIds.has(h.showSeatId));
        return [...otherShowHolds, ...myHolds];
      });
    } catch (err) {
      console.error('Failed to load seat map:', err);
    }
  }, [setActiveHolds]);

  useEffect(() => {
    if (selectedShowId) {
      fetchSeatMap(selectedShowId);
    }
  }, [selectedShowId, fetchSeatMap]);

  // Monitor seat state and real-time timer to auto-expire held seats locally
  useEffect(() => {
    const interval = setInterval(() => {
      const now = Date.now();

      // Check if current user's active holds expired
      if (activeHolds.length > 0) {
        const validHolds = activeHolds.filter((h) => new Date(h.expiresAt).getTime() > now);
        if (validHolds.length !== activeHolds.length) {
          setActiveHolds(validHolds);
          if (validHolds.length === 0) {
            setShowCheckoutModal(false);
          }
          setErrorBanner("Some of your seat holds have expired and were removed from your cart.");
          setTimeout(() => setErrorBanner(null), 5000);
        }
      }

      // Automatically release any held seats whose TTL has passed
      setSeats((prevSeats) => {
        let hasChanges = false;
        const updated = prevSeats.map((seat) => {
          if (
            seat.status === 'held' &&
            seat.hold_expires_at &&
            new Date(seat.hold_expires_at).getTime() <= now
          ) {
            hasChanges = true;
            return {
              ...seat,
              status: 'available' as const,
              hold_expires_at: null,
            };
          }
          return seat;
        });
        return hasChanges ? updated : prevSeats;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [activeHolds, setActiveHolds]);

  const handleFullState = useCallback((fullSeats: SeatItem[]) => {
    setSeats(fullSeats);
    
    // Sync activeHolds from backend
    const myHolds = fullSeats
      .filter((s) => s.status === 'held' && s.is_held_by_me && s.hold_expires_at)
      .map((s) => ({
        showSeatId: s.id,
        expiresAt: s.hold_expires_at as string,
        seatLabel: `${s.row_name}${s.col_number}`,
        price: s.price,
      }));

    if (myHolds.length > 0) {
      setActiveHolds((prev: ActiveHold[]) => {
        const newHolds = [...prev];
        for (const hold of myHolds) {
          if (!newHolds.some((h) => h.showSeatId === hold.showSeatId)) {
            newHolds.push(hold);
          }
        }
        return newHolds;
      });
    }
  }, [setActiveHolds]);

  const handleUpdates = useCallback((updates: any[]) => {
    setSeats((prevSeats) =>
      prevSeats.map((seat) => {
        const update = updates.find((u) => u.id === seat.id || u.seat_id === seat.id);
        if (update) {
          return {
            ...seat,
            status: update.status,
            hold_expires_at: update.hold_expires_at !== undefined ? update.hold_expires_at : seat.hold_expires_at,
          };
        }
        return seat;
      })
    );
  }, []);

  const handleReconnect = useCallback(() => {
    if (selectedShowId) {
      fetchSeatMap(selectedShowId);
    }
  }, [selectedShowId, fetchSeatMap]);

  useWebSocket({
    showId: selectedShowId,
    onFullState: handleFullState,
    onUpdates: handleUpdates,
    onReconnect: handleReconnect,
  });

  const selectedShow = shows.find((s) => s.id === selectedShowId);

  const handleSeatSelect = async (seat: SeatItem, e?: React.MouseEvent) => {
    if (!selectedShowId) return;

    const existingHoldIndex = activeHolds.findIndex((h) => h.showSeatId === seat.id);
    if (existingHoldIndex !== -1) {
      try {
        await releaseSeatApi(selectedShowId, seat.id);
      } catch (err) {
        console.error('Failed to release seat:', err);
      } finally {
        // Always remove from frontend state even if backend fails 
        // (e.g. if backend says we don't hold it, we shouldn't hold it here either)
        setActiveHolds((prevHolds: ActiveHold[]) => prevHolds.filter(h => h.showSeatId !== seat.id));
        
        // Optimistically update local seat state
        setSeats((prev) =>
          prev.map((s) => (s.id === seat.id ? { ...s, status: 'available', hold_expires_at: null } : s))
        );

        if (e) {
          setErrorToast({ message: `Removed seat ${seat.row_name}${seat.col_number} from selection.`, x: e.clientX, y: e.clientY });
          setTimeout(() => setErrorToast(null), 2000);
        }
      }
      return;
    }

    if (seat.status !== 'available') {
      const msg = `Seat ${seat.row_name}${seat.col_number} is currently ${seat.status}.`;
      if (e) {
        setErrorToast({ message: msg, x: e.clientX, y: e.clientY });
        setTimeout(() => setErrorToast(null), 3000);
      } else {
        setErrorBanner(msg);
        setTimeout(() => setErrorBanner(null), 3000);
      }
      return;
    }

    if (activeHolds.length >= 10) {
      const msg = `Maximum 10 seats allowed per transaction.`;
      if (e) {
        setErrorToast({ message: msg, x: e.clientX, y: e.clientY });
        setTimeout(() => setErrorToast(null), 3000);
      } else {
        setErrorBanner(msg);
        setTimeout(() => setErrorBanner(null), 3000);
      }
      return;
    }

    try {
      setHoldingSeatId(seat.id);
      setErrorBanner(null);

      const res = await holdSeatApi(selectedShowId, seat.id);

      if (res.success && res.hold) {
        const holdData: ActiveHold = {
          showSeatId: seat.id,
          expiresAt: res.hold.hold_expires_at,
          seatLabel: `${seat.row_name}${seat.col_number}`,
          price: res.hold.price,
        };
        setActiveHolds((prevHolds: ActiveHold[]) => [...prevHolds, holdData]);
        
        setSeats((prev) =>
          prev.map((s) => (s.id === seat.id ? { ...s, status: 'held', hold_expires_at: res.hold.hold_expires_at } : s))
        );
      } else {
        setErrorBanner(res.message || 'Could not hold seat.');
        setTimeout(() => setErrorBanner(null), 4000);
      }
    } catch (err: any) {
      setErrorBanner(err.response?.data?.message || 'Error holding seat.');
      setTimeout(() => setErrorBanner(null), 4000);
    } finally {
      setHoldingSeatId(null);
    }
  };

  const handleConfirmBooking = async (
    idempotencyKey: string,
    details: { name: string; phone: string; email: string }
  ) => {
    if (!selectedShowId || activeHolds.length === 0) return { success: false, message: 'No seats selected.' };
    
    let lastSuccess = null;
    let firstError = null;
    let successfulSeatIds = [];

    for (let i = 0; i < activeHolds.length; i++) {
      const hold = activeHolds[i];
      try {
        const res = await confirmBookingApi(
          selectedShowId,
          hold.showSeatId,
          `${idempotencyKey}-${i}`, // unique idem key per seat
          details
        );
        if (res && res.success) {
          lastSuccess = res;
          successfulSeatIds.push(hold.showSeatId);
        } else {
          firstError = res?.message || 'Booking failed for a seat.';
          break; // Stop on first failure for safety
        }
      } catch (err: any) {
        firstError = err.response?.data?.message || 'Booking failed for a seat.';
        break;
      }
    }

    if (successfulSeatIds.length > 0) {
      // Remove booked seats from activeHolds
      setActiveHolds((prevHolds: ActiveHold[]) => prevHolds.filter((h) => !successfulSeatIds.includes(h.showSeatId)));
      // Update seat map
      setSeats((prev) =>
        prev.map((s) => (successfulSeatIds.includes(s.id) ? { ...s, status: 'booked', hold_expires_at: null } : s))
      );
    }

    if (firstError) {
      return { success: false, message: firstError };
    }
    
    return lastSuccess; // Return the last successful booking response to show QR code etc.
  };

  return (
    <div className="space-y-8 pb-12">
      {/* Error Banner */}
      {errorBanner && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-2xl text-xs flex items-center justify-between animate-fadeIn">
          <span>{errorBanner}</span>
          <button onClick={() => setErrorBanner(null)} className="text-zinc-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Error Toast near pointer */}
      {errorToast && (
        <div 
          className="fixed z-50 pointer-events-none bg-red-950/90 border border-red-500 text-red-400 px-3 py-2 rounded-xl text-xs font-bold shadow-2xl animate-fadeIn"
          style={{ 
            left: Math.min(errorToast.x + 15, window.innerWidth - 200), 
            top: errorToast.y - 15 
          }}
        >
          {errorToast.message}
        </div>
      )}

      {/* Step 1 Search Wizard: Movie & Showtime Selection */}
      <SearchWizard
        shows={shows}
        selectedShowId={selectedShowId}
        onSelectShow={setSelectedShowId}
        onMovieSelect={onMovieSelect}
      />

      {/* Step 2 Seat Map View */}
      {selectedShow && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-black text-white flex items-center gap-2">
                Step 2: Select Seat for <span className="text-cyan-400">{selectedShow.event_title}</span>
              </h2>
              <p className="text-xs text-zinc-400">Click any available seat to hold it atomically for 10 minutes</p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => selectedShowId && fetchSeatMap(selectedShowId)}
                className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white bg-[#171717] px-4 py-2 rounded-xl border border-[#262626] hover:border-cyan-500/30 transition-all cursor-pointer font-bold"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Refresh Seat Map
              </button>
            </div>
          </div>

          <SeatMap
            seats={seats}
            activeHolds={activeHolds}
            onSeatSelect={handleSeatSelect}
            loadingSeatId={holdingSeatId}
          />
        </div>
      )}

      {/* Floating Checkout Button */}
      {activeHolds.length > 0 && selectedShow && !showCheckoutModal && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 animate-fadeIn">
          <button
            onClick={() => setShowCheckoutModal(true)}
            className="cinestream-button bg-cyan-500 hover:bg-cyan-400 text-black px-8 py-3 rounded-2xl font-black text-sm flex items-center gap-3 shadow-[0_0_30px_rgba(6,182,212,0.3)] hover:shadow-[0_0_40px_rgba(6,182,212,0.5)] transition-all"
          >
            Checkout ({activeHolds.length} Seats)
            <span className="opacity-50">|</span>
            ₹{activeHolds.reduce((sum, h) => sum + parseFloat(h.price || '0'), 0).toFixed(2)}
          </button>
        </div>
      )}

      {/* Step 3 Queue & Waitlist Section */}
      <WaitlistSection
        showId={selectedShowId}
        seats={seats}
      />

      {/* Booking Checkout Modal */}
      {showCheckoutModal && selectedShow && (
        <BookingModal
          activeHolds={activeHolds}
          show={selectedShow}
          onClose={() => setShowCheckoutModal(false)}
          onConfirmBooking={handleConfirmBooking}
        />
      )}

      {/* Recruiter Deliverables Modal */}
      {showRecruiterModal && (
        <RecruiterShowcaseModal onClose={() => setShowRecruiterModal(false)} />
      )}
    </div>
  );
};
