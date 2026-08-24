import React, { useState, useMemo } from 'react';
import { Film, MapPin, Clock } from 'lucide-react';
import type { ShowItem } from '../types';

interface SearchWizardProps {
  shows: ShowItem[];
  selectedShowId: string | null;
  onSelectShow: (showId: string) => void;
  onMovieSelect?: (bannerUrl: string) => void;
  activeCategoryType?: 'bus' | 'concert';
  setActiveCategoryType?: (type: 'bus' | 'concert') => void;
}

export const SearchWizard: React.FC<SearchWizardProps> = ({
  shows,
  selectedShowId,
  onSelectShow,
  onMovieSelect,
}) => {
  const [selectedMovieTitle, setSelectedMovieTitle] = useState<string | null>(null);

  // Group shows by Movie with title-matched authentic posters
  const uniqueMovies = useMemo(() => {
    const moviesMap = new Map();
    shows.forEach(show => {
      if (!moviesMap.has(show.event_title)) {
        let poster = show.banner_url;
        const lower = show.event_title.toLowerCase();

        // Ensure each movie has its correct distinct poster
        if (!poster || poster.trim() === '' || (poster.includes('dune_wallpaper.png') && !lower.includes('dune'))) {
          if (lower.includes('interstellar')) {
            poster = '/interstellar_wallpaper.jpg';
          } else if (lower.includes('dune')) {
            poster = '/dune_wallpaper.png';
          } else if (lower.includes('coldplay')) {
            poster = 'https://images.unsplash.com/photo-1470225620780-dba8ba36b745?auto=format&fit=crop&w=800&q=80';
          } else {
            poster = 'https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?auto=format&fit=crop&w=800&q=80';
          }
        }

        moviesMap.set(show.event_title, {
          title: show.event_title,
          banner: poster
        });
      }
    });
    return Array.from(moviesMap.values());
  }, [shows]);

  // Set first movie as default if none selected
  React.useEffect(() => {
    if (!selectedMovieTitle && uniqueMovies.length > 0) {
      setSelectedMovieTitle(uniqueMovies[0].title);
      if (onMovieSelect) {
        onMovieSelect(uniqueMovies[0].banner);
      }
    }
  }, [uniqueMovies, selectedMovieTitle, onMovieSelect]);

  const handleMovieClick = (movie: { title: string; banner: string }) => {
    setSelectedMovieTitle(movie.title);
    if (onMovieSelect) {
      onMovieSelect(movie.banner);
    }
  };

  const availableShows = shows.filter(s => s.event_title === selectedMovieTitle);

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Movies Carousel */}
      <div className="space-y-4">
        <h3 className="text-xl font-black text-white tracking-tight flex items-center gap-2">
          <Film className="w-5 h-5 text-cyan-500" /> Now Showing
        </h3>
        <div className="flex items-center gap-6 overflow-x-auto pb-4 scrollbar-none snap-x">
          {uniqueMovies.map((movie) => (
            <div 
              key={movie.title} 
              onClick={() => handleMovieClick(movie)}
              className={`flex flex-col gap-3 cursor-pointer flex-shrink-0 snap-start transition-all duration-300 ${
                selectedMovieTitle === movie.title ? 'scale-105 opacity-100' : 'scale-95 opacity-50 hover:opacity-80'
              }`}
            >
              <div className={`w-48 h-72 sm:w-56 sm:h-80 rounded-2xl overflow-hidden border-2 shadow-2xl relative group ${
                selectedMovieTitle === movie.title ? 'border-cyan-500 shadow-cyan-500/20' : 'border-transparent'
              }`}>
                <img src={movie.banner} alt={movie.title} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent"></div>
                <div className="absolute bottom-4 left-4 right-4">
                  <h4 className="text-lg font-black text-white leading-tight line-clamp-2">{movie.title}</h4>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Showtimes Picker */}
      {selectedMovieTitle && (
        <div className="cinestream-card p-6 sm:p-8 space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl font-black text-white">Select Cinema & Showtime</h3>
            <span className="text-xs font-bold bg-cyan-900/40 text-cyan-400 px-3 py-1 rounded-full border border-cyan-800/50">
              {availableShows.length} Shows Available
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {availableShows.map((show) => {
              const isSelected = show.id === selectedShowId;
              const startTime = new Date(show.start_time);
              const dateStr = startTime.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
              const timeStr = startTime.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
              
              return (
                <button
                  key={show.id}
                  onClick={() => onSelectShow(show.id)}
                  className={`text-left p-5 rounded-2xl border transition-all cursor-pointer relative overflow-hidden group ${
                    isSelected
                      ? 'bg-cyan-900/20 border-cyan-500 shadow-[0_0_20px_rgba(6,182,212,0.15)]'
                      : 'bg-[#171717] border-[#262626] hover:border-[#404040]'
                  }`}
                >
                  {isSelected && (
                    <div className="absolute top-0 left-0 w-1 h-full bg-cyan-500"></div>
                  )}
                  <div className="flex items-center justify-between mb-4">
                    <span className="text-sm font-black text-white flex items-center gap-2">
                      <Clock className="w-4 h-4 text-cyan-500" /> {timeStr}
                    </span>
                    <span className="text-[10px] bg-[#262626] text-zinc-300 px-2 py-1 rounded-md font-bold">
                      {dateStr}
                    </span>
                  </div>
                  
                  <div className="space-y-2">
                    <div className="flex items-start gap-2">
                      <MapPin className="w-4 h-4 text-cyan-600 mt-0.5 shrink-0" />
                      <div>
                        <div className="text-sm font-bold text-white">{show.venue_name}</div>
                        <div className="text-xs text-zinc-500 mt-0.5">{show.venue_location}</div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="mt-4 pt-4 border-t border-[#262626] flex items-center justify-between">
                     <span className="text-xs font-bold text-zinc-400">
                        Filling Fast
                     </span>
                     <span className={`text-xs font-bold px-2 py-1 rounded-md ${
                       (show.available_seats / show.total_seats) < 0.2 ? 'bg-red-900/30 text-red-400' : 'bg-emerald-900/30 text-emerald-400'
                     }`}>
                        {show.available_seats} / {show.total_seats} Seats
                     </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
