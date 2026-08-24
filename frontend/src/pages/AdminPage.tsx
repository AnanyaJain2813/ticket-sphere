import React, { useState, useEffect } from 'react';
import { getSeatCategoriesApi, createVenueApi } from '../api';
import { ShieldCheck, Save } from 'lucide-react';

export const AdminPage: React.FC = () => {
  const [categories, setCategories] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [location, setLocation] = useState('');
  const [capacity, setCapacity] = useState<number>(100);
  
  const [rows, setRows] = useState<number>(5);
  const [cols, setCols] = useState<number>(10);
  
  // activeCategory to "paint" seats with
  const [activeCategoryId, setActiveCategoryId] = useState<string | null>(null);
  
  // 2D grid storing categoryIds (null means unassigned / aisle)
  const [grid, setGrid] = useState<(string | null)[][]>([]);
  
  const [msgBanner, setMsgBanner] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchCats = async () => {
      try {
        const data = await getSeatCategoriesApi();
        setCategories(data);
        if (data.length > 0) {
          setActiveCategoryId(data[0].id);
        }
      } catch (err) {
        console.error('Failed to load categories', err);
      }
    };
    fetchCats();
  }, []);

  // Initialize or resize grid
  useEffect(() => {
    setGrid((prevGrid) => {
      const newGrid: (string | null)[][] = [];
      for (let r = 0; r < rows; r++) {
        const newRow: (string | null)[] = [];
        for (let c = 0; c < cols; c++) {
          // Preserve existing if within bounds, else null
          if (prevGrid[r] && prevGrid[r][c] !== undefined) {
            newRow.push(prevGrid[r][c]);
          } else {
            newRow.push(null);
          }
        }
        newGrid.push(newRow);
      }
      return newGrid;
    });
  }, [rows, cols]);

  const handleCellClick = (rIndex: number, cIndex: number) => {
    setGrid((prevGrid) => {
      const newGrid = [...prevGrid];
      newGrid[rIndex] = [...newGrid[rIndex]];
      // Toggle off if clicking with same category, else paint
      if (newGrid[rIndex][cIndex] === activeCategoryId) {
        newGrid[rIndex][cIndex] = null;
      } else {
        newGrid[rIndex][cIndex] = activeCategoryId;
      }
      return newGrid;
    });
  };

  const getRowLetter = (index: number) => {
    return String.fromCharCode(65 + index); // 0 -> A, 1 -> B
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !location) {
      setMsgBanner({ text: 'Name and location are required.', type: 'error' });
      return;
    }

    setLoading(true);
    setMsgBanner(null);
    try {
      // Build layout JSON
      const seats = [];
      for (let r = 0; r < rows; r++) {
        const rowName = getRowLetter(r);
        let colCounter = 1; // logical seat number skipping blanks
        for (let c = 0; c < cols; c++) {
          const catId = grid[r][c];
          if (catId) {
            seats.push({
              category_id: catId,
              row_name: rowName,
              col_number: colCounter++,
              coord_x: c * 10,
              coord_y: r * 10
            });
          }
        }
      }

      if (seats.length === 0) {
        setMsgBanner({ text: 'Layout must contain at least one assigned seat.', type: 'error' });
        setLoading(false);
        return;
      }

      const payload = {
        name,
        location,
        total_capacity: capacity,
        layout: {
          name: 'Main Layout',
          total_rows: rows,
          total_columns: cols,
          seats: seats
        }
      };

      await createVenueApi(payload);
      setMsgBanner({ text: `Venue "${name}" created successfully!`, type: 'success' });
      setName('');
      setLocation('');
      setGrid(Array(rows).fill(Array(cols).fill(null)));
    } catch (err: any) {
      setMsgBanner({ text: err.response?.data?.message || 'Error creating venue.', type: 'error' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12 animate-fadeIn">
      <div>
        <h2 className="text-2xl font-black text-white flex items-center gap-2">
          <ShieldCheck className="w-6 h-6 text-purple-400" /> Platform Admin Portal
        </h2>
        <p className="text-xs text-zinc-400">Configure global venues and physical seat layouts</p>
      </div>

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

      <form onSubmit={handleSubmit} className="cinestream-card p-6 sm:p-8 rounded-3xl border border-[#262626] bg-[#171717] space-y-8">
        
        {/* Basic Venue Details */}
        <div className="space-y-4">
          <h3 className="text-sm font-black text-white border-b border-[#262626] pb-2 uppercase tracking-wider">
            1. Venue Details
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-zinc-400 uppercase">Venue Name</label>
              <input
                required
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                className="w-full bg-black/50 border border-[#262626] rounded-xl px-4 py-2.5 text-sm text-white focus:border-cyan-500 outline-none"
                placeholder="e.g. PVR Director's Cut"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-zinc-400 uppercase">Location / City</label>
              <input
                required
                type="text"
                value={location}
                onChange={e => setLocation(e.target.value)}
                className="w-full bg-black/50 border border-[#262626] rounded-xl px-4 py-2.5 text-sm text-white focus:border-cyan-500 outline-none"
                placeholder="e.g. New Delhi"
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-bold text-zinc-400 uppercase">Listed Capacity</label>
              <input
                required
                type="number"
                min="1"
                value={capacity}
                onChange={e => setCapacity(parseInt(e.target.value))}
                className="w-full bg-black/50 border border-[#262626] rounded-xl px-4 py-2.5 text-sm text-white focus:border-cyan-500 outline-none"
              />
            </div>
          </div>
        </div>

        {/* Seat Layout Builder */}
        <div className="space-y-6">
          <h3 className="text-sm font-black text-white border-b border-[#262626] pb-2 uppercase tracking-wider">
            2. Interactive Seat Layout Builder
          </h3>

          <div className="flex flex-wrap gap-6 items-center">
            <div className="flex items-center gap-4 bg-black/40 p-3 rounded-2xl border border-white/5">
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase">Rows</label>
                <input
                  type="number"
                  min="1" max="26"
                  value={rows}
                  onChange={e => setRows(Math.min(26, Math.max(1, parseInt(e.target.value) || 1)))}
                  className="w-20 bg-[#171717] border border-[#262626] rounded-lg px-2 py-1 text-sm text-white focus:border-cyan-500 outline-none"
                />
              </div>
              <div className="space-y-1">
                <label className="text-[10px] font-bold text-zinc-500 uppercase">Columns</label>
                <input
                  type="number"
                  min="1" max="50"
                  value={cols}
                  onChange={e => setCols(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-20 bg-[#171717] border border-[#262626] rounded-lg px-2 py-1 text-sm text-white focus:border-cyan-500 outline-none"
                />
              </div>
            </div>

            <div className="flex-1">
              <label className="text-[10px] font-bold text-zinc-500 uppercase mb-2 block">
                Active Paintbrush Category
              </label>
              <div className="flex flex-wrap gap-2">
                {categories.map(c => (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setActiveCategoryId(c.id)}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all border ${
                      activeCategoryId === c.id
                        ? 'bg-purple-500/20 text-purple-400 border-purple-500/50 shadow-[0_0_10px_rgba(168,85,247,0.2)]'
                        : 'bg-black/40 text-zinc-500 border-[#262626] hover:text-white'
                    }`}
                  >
                    {c.name}
                  </button>
                ))}
                <button
                  type="button"
                  onClick={() => setActiveCategoryId(null)}
                  className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all border ${
                    activeCategoryId === null
                      ? 'bg-zinc-500/20 text-zinc-300 border-zinc-500/50'
                      : 'bg-black/40 text-zinc-500 border-[#262626] hover:text-white'
                  }`}
                >
                  Eraser (Aisle)
                </button>
              </div>
            </div>
          </div>

          <div className="bg-black/50 p-6 rounded-2xl border border-[#262626] overflow-x-auto">
            <div className="flex flex-col items-center gap-2 min-w-max">
              {/* Screen Indicator */}
              <div className="w-full max-w-md h-2 bg-gradient-to-r from-transparent via-cyan-500/30 to-transparent mb-8 flex justify-center relative">
                <span className="absolute -bottom-6 text-[9px] font-bold text-cyan-500/50 uppercase tracking-[0.3em]">Screen</span>
              </div>

              {grid.map((row, rIndex) => (
                <div key={rIndex} className="flex items-center gap-3">
                  <div className="w-6 text-center text-xs font-black text-zinc-500 select-none">
                    {getRowLetter(rIndex)}
                  </div>
                  <div className="flex gap-1.5">
                    {row.map((catId, cIndex) => {
                      const category = categories.find(c => c.id === catId);
                      return (
                        <div
                          key={`${rIndex}-${cIndex}`}
                          onClick={() => handleCellClick(rIndex, cIndex)}
                          className={`w-6 h-6 rounded-md cursor-crosshair flex items-center justify-center transition-colors border ${
                            catId
                              ? 'bg-purple-500/20 border-purple-500/50 hover:bg-purple-500/40 text-purple-400 text-[9px] font-black'
                              : 'bg-[#171717] border-[#262626] hover:border-zinc-500 border-dashed'
                          }`}
                          title={category ? category.name : 'Aisle (Blank)'}
                        >
                          {catId && category ? category.name.substring(0, 1) : ''}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-purple-500 hover:bg-purple-400 text-purple-950 font-black py-4 rounded-xl flex items-center justify-center gap-2 transition-colors shadow-[0_0_20px_rgba(168,85,247,0.3)] disabled:opacity-50"
        >
          {loading ? 'Building Venue...' : (
            <><Save className="w-5 h-5" /> Publish Venue Configuration</>
          )}
        </button>
      </form>
    </div>
  );
};
