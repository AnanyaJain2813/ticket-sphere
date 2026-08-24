import React, { useState, useRef, useEffect } from 'react';
import type { SeatItem, ActiveHold } from '../types';
import { Lock, Check, Circle, Filter, Monitor } from 'lucide-react';

interface SeatMapProps {
  seats: SeatItem[];
  activeHolds: ActiveHold[];
  onSeatSelect: (seat: SeatItem, e?: React.MouseEvent) => void;
  loadingSeatId?: string | null;
}

export const SeatMap: React.FC<SeatMapProps> = ({
  seats,
  activeHolds,
  onSeatSelect,
  loadingSeatId,
}) => {
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [mousePos, setMousePos] = useState<{ x: number; y: number }>({ x: 50, y: 50 });
  const [isTouchDevice, setIsTouchDevice] = useState<boolean>(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setIsTouchDevice('ontouchstart' in window || navigator.maxTouchPoints > 0);
  }, []);

  const handleMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    if (isTouchDevice || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    setMousePos({ x, y });
  };

  const categories = Array.from(new Set(seats.map((s) => s.category_name)));

  const filteredSeats = selectedCategory === 'all'
    ? seats
    : seats.filter((s) => s.category_name === selectedCategory);

  const rows = Array.from(new Set(filteredSeats.map((s) => s.row_name))).sort();

  const getSeatStyle = (seat: SeatItem) => {
    if (seat.status === 'booked') {
      return 'cinestream-seat-booked';
    }
    if (seat.status === 'held') {
      const isHeldByMe = activeHolds.some((h) => h.showSeatId === seat.id);
      return isHeldByMe ? 'cinestream-seat-held' : 'cinestream-seat-booked';
    }
    return 'cinestream-seat-available';
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Category Filter & Status Legend */}
      <div className="flex flex-wrap items-center justify-between gap-4 cinestream-card p-4">
        {/* Tier Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-cyan-500" />
          <span className="text-xs font-bold text-zinc-500 uppercase tracking-wider">Seat Class:</span>
          <button
            onClick={() => setSelectedCategory('all')}
            className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all ${
              selectedCategory === 'all'
                ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                : 'bg-[#171717] text-zinc-400 hover:text-white border border-[#262626]'
            }`}
          >
            All Classes
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all ${
                selectedCategory === cat
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'bg-[#171717] text-zinc-400 hover:text-white border border-[#262626]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-4 text-xs font-medium">
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded border border-[#404040] bg-[#171717]" />
            <span className="text-zinc-400">Available</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.6)]" />
            <span className="text-cyan-400 font-bold">Selected</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-3.5 rounded bg-[#262626] border border-[#171717]" />
            <span className="text-zinc-600">Booked</span>
          </div>
        </div>
      </div>

      {/* CineStream Seat Map Grid */}
      <div className="relative cinestream-card overflow-hidden">
        <div
          ref={containerRef}
          onMouseMove={handleMouseMove}
          style={{
            '--mouse-x': `${mousePos.x}%`,
            '--mouse-y': `${mousePos.y}%`,
          } as React.CSSProperties}
          className="p-6 sm:p-10 min-h-[500px] overflow-x-auto webkit-scrollbar-hide"
        >
        {/* Cinema Screen */}
        <div className="cinema-screen flex items-center justify-center">
          <span className="text-xs font-bold text-cyan-500/50 uppercase tracking-[0.3em] flex items-center gap-2">
            <Monitor className="w-4 h-4" /> SCREEN THIS WAY
          </span>
        </div>

        {/* Rows Layout */}
        <div className="space-y-4 sm:space-y-6 flex flex-col items-center min-w-max pb-8 mx-auto px-4">
          {rows.map((rowName) => {
            const rowSeats = filteredSeats
              .filter((s) => s.row_name === rowName)
              .sort((a, b) => a.col_number - b.col_number);
            // Splitting logic to create a central aisle if col_number is divided by 5
            const leftSeats = rowSeats.filter((s) => s.col_number <= 5);
            const rightSeats = rowSeats.filter((s) => s.col_number > 5);

            return (
              <div key={rowName} className="flex items-center justify-center gap-4 sm:gap-8 w-full max-w-3xl">
                {/* Row Label (Left) */}
                <div className="w-6 text-center text-xs font-black text-zinc-500">
                  {rowName}
                </div>

                {/* Left Side */}
                <div className="flex items-center justify-end gap-1.5 sm:gap-3 flex-1">
                  {leftSeats.map((seat) => {
                    const isHeldByMe = activeHolds.some((h) => h.showSeatId === seat.id);
                    const isBookedOrHeldByOther = seat.status === 'booked' || (seat.status === 'held' && !isHeldByMe);
                    const isLoading = loadingSeatId === seat.id;

                    return (
                      <button
                        key={seat.id}
                        tabIndex={isBookedOrHeldByOther ? -1 : 0}
                        role="button"
                        aria-label={`Row ${seat.row_name} Seat ${seat.col_number} - ${seat.category_name} - ₹${seat.price}`}
                        disabled={isBookedOrHeldByOther || isLoading}
                        onClick={(e) => onSeatSelect(seat, e)}
                        className={`cinestream-seat relative group shrink-0 ${getSeatStyle(seat)}`}
                      >
                        <span className="text-[10px] sm:text-[11px] font-black leading-none">
                          {seat.col_number}
                        </span>
                        <div className="mt-0.5">
                          {isLoading ? (
                            <div className="w-3 h-3 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                          ) : isBookedOrHeldByOther ? (
                            <Lock className="w-3 h-3 text-zinc-600" />
                          ) : isHeldByMe ? (
                            <Check className="w-3.5 h-3.5 text-black font-black" />
                          ) : (
                            <Circle className="w-2 h-2 sm:w-2.5 sm:h-2.5 opacity-20" />
                          )}
                        </div>

                        {/* Hover Tooltip */}
                        <div className="absolute bottom-full mb-2 hidden group-hover:flex flex-col items-center bg-black border border-[#262626] text-white text-[10px] py-1 px-3 rounded-lg shadow-xl whitespace-nowrap pointer-events-none z-30">
                          <span className="font-bold text-cyan-400">₹{seat.price}</span>
                          <span className="text-zinc-400">{seat.category_name}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Central Aisle */}
                <div className="w-8 sm:w-16 flex-shrink-0"></div>

                {/* Right Side */}
                <div className="flex items-center justify-start gap-1.5 sm:gap-3 flex-1">
                  {rightSeats.map((seat) => {
                    const isHeldByMe = activeHolds.some((h) => h.showSeatId === seat.id);
                    const isBookedOrHeldByOther = seat.status === 'booked' || (seat.status === 'held' && !isHeldByMe);
                    const isLoading = loadingSeatId === seat.id;

                    return (
                      <button
                        key={seat.id}
                        tabIndex={isBookedOrHeldByOther ? -1 : 0}
                        role="button"
                        aria-label={`Row ${seat.row_name} Seat ${seat.col_number} - ${seat.category_name} - ₹${seat.price}`}
                        disabled={isBookedOrHeldByOther || isLoading}
                        onClick={(e) => onSeatSelect(seat, e)}
                        className={`cinestream-seat relative group shrink-0 ${getSeatStyle(seat)}`}
                      >
                        <span className="text-[10px] sm:text-[11px] font-black leading-none">
                          {seat.col_number}
                        </span>
                        <div className="mt-0.5">
                          {isLoading ? (
                            <div className="w-3 h-3 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
                          ) : isBookedOrHeldByOther ? (
                            <Lock className="w-3 h-3 text-zinc-600" />
                          ) : isHeldByMe ? (
                            <Check className="w-3.5 h-3.5 text-black font-black" />
                          ) : (
                            <Circle className="w-2 h-2 sm:w-2.5 sm:h-2.5 opacity-20" />
                          )}
                        </div>

                        {/* Hover Tooltip */}
                        <div className="absolute bottom-full mb-2 hidden group-hover:flex flex-col items-center bg-black border border-[#262626] text-white text-[10px] py-1 px-3 rounded-lg shadow-xl whitespace-nowrap pointer-events-none z-30">
                          <span className="font-bold text-cyan-400">₹{seat.price}</span>
                          <span className="text-zinc-400">{seat.category_name}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>

                {/* Row Label (Right) */}
                <div className="w-6 text-center text-xs font-black text-zinc-500">
                  {rowName}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  </div>
);
};
