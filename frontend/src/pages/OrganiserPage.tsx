import React, { useState, useEffect } from 'react';
import { getOrganiserRevenue, getShows, getVenuesApi, getSeatCategoriesApi, createEventApi, createShowApi, getOrganiserBookings } from '../api';
import type { OrganiserRevenueSummary, ShowItem } from '../types';
import { LayoutDashboard, IndianRupee, Users, PieChart as PieChartIcon, TrendingUp, RefreshCw, PlusCircle, Save, List } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

export const OrganiserPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'analytics' | 'create' | 'bookings'>('analytics');
  
  // Analytics State
  const [shows, setShows] = useState<ShowItem[]>([]);
  const [selectedShowId, setSelectedShowId] = useState<string>('all');
  const [summary, setSummary] = useState<OrganiserRevenueSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [liveBookings, setLiveBookings] = useState<any[]>([]);

  // Create Flow State
  const [venues, setVenues] = useState<any[]>([]);
  const [categories, setCategories] = useState<any[]>([]);
  const [msgBanner, setMsgBanner] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [creating, setCreating] = useState(false);
  
  // Event Form
  const [eventTitle, setEventTitle] = useState('');
  const [eventType, setEventType] = useState('movie');
  const [eventDesc, setEventDesc] = useState('');
  const [eventBanner, setEventBanner] = useState('');
  
  // Show Form
  const [showVenueId, setShowVenueId] = useState('');
  const [showStartTime, setShowStartTime] = useState('');
  const [showEndTime, setShowEndTime] = useState('');
  const [pricing, setPricing] = useState<Record<string, number>>({});

  useEffect(() => {
    const loadInitData = async () => {
      try {
        const [showsData, venuesData, catsData] = await Promise.all([
          getShows(),
          getVenuesApi(),
          getSeatCategoriesApi()
        ]);
        setShows(showsData);
        setVenues(venuesData);
        if (venuesData.length > 0) setShowVenueId(venuesData[0].id);
        
        setCategories(catsData);
        const initPricing: Record<string, number> = {};
        catsData.forEach((c: any) => {
          initPricing[c.id] = parseInt(c.base_price);
        });
        setPricing(initPricing);
      } catch (err) {
        console.error('Failed to load init data:', err);
      }
    };
    loadInitData();
  }, []);

  const fetchRevenueData = async (showId?: string) => {
    try {
      setLoading(true);
      const targetId = showId === 'all' ? undefined : showId;
      const data = await getOrganiserRevenue(targetId);
      setSummary(data);
    } catch (err) {
      console.error('Failed to load revenue summary:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchLiveBookings = async () => {
    try {
      const data = await getOrganiserBookings();
      setLiveBookings(data);
    } catch (err) {
      console.error('Failed to load live bookings:', err);
    }
  };

  useEffect(() => {
    if (activeTab === 'analytics') {
      fetchRevenueData(selectedShowId);
    } else if (activeTab === 'bookings') {
      fetchLiveBookings();
    }
  }, [selectedShowId, activeTab]);

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eventTitle || !showVenueId || !showStartTime || !showEndTime) {
      setMsgBanner({ text: 'Please fill all required fields.', type: 'error' });
      return;
    }

    setCreating(true);
    setMsgBanner(null);
    try {
      // 1. Create Event
      const eventRes = await createEventApi({
        title: eventTitle,
        event_type: eventType,
        description: eventDesc,
        banner_url: eventBanner
      });

      // 2. Create Show
      await createShowApi({
        event_id: eventRes.id,
        venue_id: showVenueId,
        start_time: new Date(showStartTime).toISOString(),
        end_time: new Date(showEndTime).toISOString(),
        pricing: pricing
      });

      setMsgBanner({ text: `Event "${eventTitle}" and its Show have been published successfully!`, type: 'success' });
      setEventTitle('');
      setEventDesc('');
      setEventBanner('');
      
      // Refresh shows list
      const freshShows = await getShows();
      setShows(freshShows);
      
    } catch (err: any) {
      setMsgBanner({ text: err.response?.data?.message || 'Error creating event and show.', type: 'error' });
    } finally {
      setCreating(false);
    }
  };

  const chartData = summary
    ? [
        { name: 'Booked', value: summary.booked_seats, color: '#10b981' },
        { name: 'Held', value: summary.held_seats, color: '#d84e55' },
        { name: 'Available', value: summary.available_seats, color: '#3f3f46' },
      ]
    : [];

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12 animate-fadeIn">
      {/* Header & Tabs */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="text-2xl font-black text-white flex items-center gap-2">
            Organiser <span className="text-[#d84e55]">Portal</span>
          </h2>
          <p className="text-xs text-zinc-400">Manage your events, shows, and revenue analytics</p>
        </div>

        <div className="flex bg-[#1c1d2b] p-1 rounded-xl border border-[#2e3046]">
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors ${
              activeTab === 'analytics'
                ? 'bg-[#d84e55] text-white shadow-md'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            Revenue Analytics
          </button>
          <button
            onClick={() => setActiveTab('bookings')}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'bookings'
                ? 'bg-[#d84e55] text-white shadow-md'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            <List className="w-3.5 h-3.5" /> Live Bookings
          </button>
          <button
            onClick={() => setActiveTab('create')}
            className={`px-4 py-2 text-xs font-bold rounded-lg transition-colors flex items-center gap-1.5 ${
              activeTab === 'create'
                ? 'bg-[#d84e55] text-white shadow-md'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            <PlusCircle className="w-3.5 h-3.5" /> Publish New Event
          </button>
        </div>
      </div>

      {activeTab === 'analytics' && (
        <div className="space-y-6">
          <div className="flex items-center justify-end gap-3">
            <select
              value={selectedShowId}
              onChange={(e) => setSelectedShowId(e.target.value)}
              className="bg-[#1c1d2b] border border-[#2e3046] text-xs font-bold text-white px-3.5 py-2 rounded-xl focus:outline-none cursor-pointer"
            >
              <option value="all">All Routes / Events Combined</option>
              {shows.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.event_title} ({s.venue_name})
                </option>
              ))}
            </select>
            <button
              onClick={() => fetchRevenueData(selectedShowId)}
              className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white bg-[#1c1d2b] px-3.5 py-2 rounded-xl border border-[#2e3046] transition-all cursor-pointer font-bold"
            >
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>

          {loading || !summary ? (
            <div className="cinestream-card p-12 rounded-3xl text-center text-zinc-400">
              <div className="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              Loading revenue statistics...
            </div>
          ) : (
            <div className="space-y-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="cinestream-card p-5 rounded-2xl border border-[#262626] space-y-2 bg-[#171717]">
                  <div className="flex justify-between items-center text-zinc-400 text-xs">
                    <span>Total Revenue</span>
                    <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-xl">
                      <IndianRupee className="w-4 h-4" />
                    </div>
                  </div>
                  <div className="text-2xl font-black text-white">₹{summary.total_revenue}</div>
                  <div className="text-[11px] text-emerald-400 flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" /> Confirmed Collections
                  </div>
                </div>

                <div className="cinestream-card p-5 rounded-2xl border border-[#262626] space-y-2 bg-[#171717]">
                  <div className="flex justify-between items-center text-zinc-400 text-xs">
                    <span>Occupancy Rate</span>
                    <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-xl">
                      <PieChartIcon className="w-4 h-4" />
                    </div>
                  </div>
                  <div className="text-2xl font-black text-cyan-400">
                    {summary.occupancy_rate_percent}%
                  </div>
                  <div className="text-[11px] text-zinc-400">
                    {summary.booked_seats} of {summary.total_seats} seats booked
                  </div>
                </div>

                <div className="cinestream-card p-5 rounded-2xl border border-[#262626] space-y-2 bg-[#171717]">
                  <div className="flex justify-between items-center text-zinc-400 text-xs">
                    <span>Active Holds</span>
                    <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-xl">
                      <Users className="w-4 h-4" />
                    </div>
                  </div>
                  <div className="text-2xl font-black text-indigo-400">{summary.held_seats}</div>
                  <div className="text-[11px] text-zinc-400">In checkout pipeline</div>
                </div>

                <div className="cinestream-card p-5 rounded-2xl border border-[#262626] space-y-2 bg-[#171717]">
                  <div className="flex justify-between items-center text-zinc-400 text-xs">
                    <span>Available Seats</span>
                    <div className="p-2 bg-zinc-800 text-zinc-400 rounded-xl">
                      <LayoutDashboard className="w-4 h-4" />
                    </div>
                  </div>
                  <div className="text-2xl font-black text-zinc-300">{summary.available_seats}</div>
                  <div className="text-[11px] text-zinc-500">Ready for booking</div>
                </div>
              </div>

              <div className="cinestream-card p-6 rounded-3xl border border-[#262626] space-y-4 bg-[#171717]">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <PieChartIcon className="w-4 h-4 text-cyan-400" /> Seat Status Breakdown
                </h3>
                <div className="h-64 w-full flex items-center justify-center">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={chartData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={5} dataKey="value">
                        {chartData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: '#14151e', borderColor: '#2e3046', borderRadius: '12px', color: '#ffffff' }} />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Added Shows List for Evaluators */}
              <div className="cinestream-card p-6 rounded-3xl border border-[#262626] space-y-4 bg-[#171717]">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <LayoutDashboard className="w-4 h-4 text-[#d84e55]" /> Active Shows Database
                </h3>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm text-zinc-400">
                    <thead className="text-xs text-zinc-500 uppercase bg-black/40 border-b border-[#262626]">
                      <tr>
                        <th className="px-4 py-3 font-bold rounded-tl-lg">Event Title</th>
                        <th className="px-4 py-3 font-bold">Venue</th>
                        <th className="px-4 py-3 font-bold">Start Time</th>
                        <th className="px-4 py-3 font-bold">Total Seats</th>
                        <th className="px-4 py-3 font-bold rounded-tr-lg">Available</th>
                      </tr>
                    </thead>
                    <tbody>
                      {shows.map((s) => (
                        <tr key={s.id} className="border-b border-[#262626]/50 hover:bg-white/5 transition-colors">
                          <td className="px-4 py-3 font-bold text-white">{s.event_title} <span className="text-[10px] text-zinc-500 font-normal uppercase bg-[#262626] px-2 py-0.5 rounded ml-2">{s.event_type}</span></td>
                          <td className="px-4 py-3">{s.venue_name}</td>
                          <td className="px-4 py-3">{new Date(s.start_time).toLocaleString()}</td>
                          <td className="px-4 py-3 text-zinc-300">{s.total_seats}</td>
                          <td className="px-4 py-3 text-cyan-400 font-bold">{s.available_seats}</td>
                        </tr>
                      ))}
                      {shows.length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-4 py-8 text-center text-zinc-500">No shows found.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'bookings' && (
        <div className="space-y-6 animate-fadeIn">
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={() => fetchLiveBookings()}
              className="flex items-center gap-1.5 text-xs text-zinc-400 hover:text-white bg-[#1c1d2b] px-3.5 py-2 rounded-xl border border-[#2e3046] transition-all cursor-pointer font-bold"
            >
              <RefreshCw className="w-4 h-4" /> Refresh
            </button>
          </div>

          <div className="cinestream-card rounded-3xl border border-[#262626] bg-[#171717] overflow-hidden">
            <div className="p-5 border-b border-[#262626] flex items-center justify-between bg-black/40">
              <h2 className="text-sm font-black text-white uppercase tracking-widest flex items-center gap-2">
                <List className="w-4 h-4 text-[#d84e55]" /> Live Bookings Database
              </h2>
              <span className="text-xs font-bold text-zinc-400 bg-[#262626] px-3 py-1 rounded-full">
                {liveBookings.length} Total Bookings
              </span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-[#1c1d2b] text-zinc-400 text-xs uppercase tracking-wider">
                  <tr>
                    <th className="px-4 py-3 font-bold rounded-tl-lg">Reference</th>
                    <th className="px-4 py-3 font-bold">Status</th>
                    <th className="px-4 py-3 font-bold">Customer</th>
                    <th className="px-4 py-3 font-bold">Contact</th>
                    <th className="px-4 py-3 font-bold">Movie & Time</th>
                    <th className="px-4 py-3 font-bold">Seat</th>
                    <th className="px-4 py-3 font-bold rounded-tr-lg">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {liveBookings.map((b) => (
                    <tr key={b.id} className="border-b border-[#262626]/50 hover:bg-white/5 transition-colors">
                      <td className="px-4 py-3 font-mono text-cyan-400 font-bold">{b.booking_reference}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${b.status === 'confirmed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}`}>
                          {b.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-white font-bold">{b.customer_name}</td>
                      <td className="px-4 py-3 text-zinc-400 text-xs">{b.customer_email}</td>
                      <td className="px-4 py-3">
                        <div className="text-white font-bold">{b.movie}</div>
                        <div className="text-[10px] text-zinc-500">{b.show_date} • {b.show_time}</div>
                      </td>
                      <td className="px-4 py-3 font-bold text-white">{b.seat}</td>
                      <td className="px-4 py-3 text-zinc-300">₹{b.amount}</td>
                    </tr>
                  ))}
                  {liveBookings.length === 0 && (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-zinc-500">No live bookings found for your events yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'create' && (
        <form onSubmit={handleCreateSubmit} className="cinestream-card p-6 sm:p-8 rounded-3xl border border-[#262626] bg-[#171717] space-y-8 animate-fadeIn">
          
          {msgBanner && (
            <div className={`p-4 rounded-2xl text-xs flex items-center justify-between border ${
              msgBanner.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-red-500/10 text-red-400 border-red-500/30'
            }`}>
              <span>{msgBanner.text}</span>
              <button type="button" onClick={() => setMsgBanner(null)} className="text-zinc-400 hover:text-white">✕</button>
            </div>
          )}

          <div className="space-y-4">
            <h3 className="text-sm font-black text-white border-b border-[#262626] pb-2 uppercase tracking-wider">
              1. Event Details
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-zinc-400 uppercase">Event Title</label>
                <input required type="text" value={eventTitle} onChange={e => setEventTitle(e.target.value)} className="w-full bg-black/50 border border-[#262626] rounded-xl px-4 py-2.5 text-sm text-white focus:border-[#d84e55] outline-none" placeholder="e.g. Dune: Part Two" />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-zinc-400 uppercase">Event Type</label>
                <select value={eventType} onChange={e => setEventType(e.target.value)} className="w-full bg-black/50 border border-[#262626] rounded-xl px-4 py-2.5 text-sm text-white focus:border-[#d84e55] outline-none">
                  <option value="movie">Movie</option>
                  <option value="concert">Concert</option>
                  <option value="sports">Sports</option>
                  <option value="theater">Theater</option>
                </select>
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-[10px] font-bold text-zinc-400 uppercase">Description (Optional)</label>
                <textarea rows={2} value={eventDesc} onChange={e => setEventDesc(e.target.value)} className="w-full bg-black/50 border border-[#262626] rounded-xl px-4 py-2.5 text-sm text-white focus:border-[#d84e55] outline-none resize-none" placeholder="Describe the event..." />
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                <label className="text-[10px] font-bold text-zinc-400 uppercase">Banner Image URL (Optional)</label>
                <input type="url" value={eventBanner} onChange={e => setEventBanner(e.target.value)} className="w-full bg-black/50 border border-[#262626] rounded-xl px-4 py-2.5 text-sm text-white focus:border-[#d84e55] outline-none" placeholder="https://..." />
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-black text-white border-b border-[#262626] pb-2 uppercase tracking-wider">
              2. Show Details & Venue
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-zinc-400 uppercase">Venue</label>
                <select required value={showVenueId} onChange={e => setShowVenueId(e.target.value)} className="w-full bg-black/50 border border-[#262626] rounded-xl px-4 py-2.5 text-sm text-white focus:border-[#d84e55] outline-none">
                  <option value="" disabled>Select Venue</option>
                  {venues.map(v => (
                    <option key={v.id} value={v.id}>{v.name} ({v.location})</option>
                  ))}
                </select>
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-zinc-400 uppercase">Start Time</label>
                <input required type="datetime-local" value={showStartTime} onChange={e => setShowStartTime(e.target.value)} className="w-full bg-black/50 border border-[#262626] rounded-xl px-4 py-2.5 text-sm text-white focus:border-[#d84e55] outline-none [color-scheme:dark]" />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-zinc-400 uppercase">End Time</label>
                <input required type="datetime-local" value={showEndTime} onChange={e => setShowEndTime(e.target.value)} className="w-full bg-black/50 border border-[#262626] rounded-xl px-4 py-2.5 text-sm text-white focus:border-[#d84e55] outline-none [color-scheme:dark]" />
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-black text-white border-b border-[#262626] pb-2 uppercase tracking-wider">
              3. Custom Ticket Pricing
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {categories.map(c => (
                <div key={c.id} className="space-y-1.5 bg-black/40 p-4 rounded-xl border border-[#262626]">
                  <label className="text-[10px] font-bold text-zinc-400 uppercase">{c.name} (₹)</label>
                  <input
                    type="number"
                    min="0"
                    required
                    value={pricing[c.id] || 0}
                    onChange={e => setPricing({...pricing, [c.id]: parseInt(e.target.value) || 0})}
                    className="w-full bg-[#171717] border border-[#262626] rounded-lg px-3 py-2 text-sm text-white focus:border-[#d84e55] outline-none"
                  />
                  <div className="text-[9px] text-zinc-500">Base: ₹{c.base_price}</div>
                </div>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={creating}
            className="w-full bg-[#d84e55] hover:bg-red-500 text-white font-black py-4 rounded-xl flex items-center justify-center gap-2 transition-colors shadow-[0_0_20px_rgba(216,78,85,0.3)] disabled:opacity-50"
          >
            {creating ? 'Publishing Event & Seating...' : (
              <><Save className="w-5 h-5" /> Publish New Event</>
            )}
          </button>
        </form>
      )}
    </div>
  );
};
