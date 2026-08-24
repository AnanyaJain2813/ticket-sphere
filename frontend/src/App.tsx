import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { AuthScreen } from './components/AuthScreen';
import { BookingPage } from './pages/BookingPage';
import { HistoryPage } from './pages/HistoryPage';
import { OrganiserPage } from './pages/OrganiserPage';
import { AdminPage } from './pages/AdminPage';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import type { ActiveHold } from './types';

const MainApp: React.FC = () => {
  const { isAuthenticated, user } = useAuth();
  
  const [mouseOffset, setMouseOffset] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [mousePosPx, setMousePosPx] = useState<{ x: number; y: number }>({ x: 500, y: 300 });
  const [currentWallpaper, setCurrentWallpaper] = useState<string>('/dune_wallpaper.png');

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      const x = e.clientX / window.innerWidth - 0.5;
      const y = e.clientY / window.innerHeight - 0.5;
      setMouseOffset({ x, y });
      setMousePosPx({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const [activeHolds, setActiveHoldsState] = useState<ActiveHold[]>(() => {
    const saved = localStorage.getItem('apex_active_holds');
    if (!saved) return [];
    try {
      const parsed: ActiveHold[] = JSON.parse(saved);
      const valid = parsed.filter(h => new Date(h.expiresAt).getTime() > Date.now());
      if (valid.length !== parsed.length) {
        localStorage.setItem('apex_active_holds', JSON.stringify(valid));
      }
      return valid;
    } catch {
      return [];
    }
  });

  const setActiveHolds = (holdsOrFn: ActiveHold[] | ((prev: ActiveHold[]) => ActiveHold[])) => {
    setActiveHoldsState((prev) => {
      const newHolds = typeof holdsOrFn === 'function' ? holdsOrFn(prev) : holdsOrFn;
      if (newHolds.length > 0) {
        localStorage.setItem('apex_active_holds', JSON.stringify(newHolds));
      } else {
        localStorage.removeItem('apex_active_holds');
      }
      return newHolds;
    });
  };

  const activeWallpaper = !isAuthenticated ? '/interstellar_wallpaper.jpg' : currentWallpaper;

  return (
    <BrowserRouter>
      <div className="relative min-h-screen bg-[#050507] text-zinc-100 flex flex-col font-sans overflow-x-hidden">
        {/* Dynamic Movie Wallpaper Background with Parallax Movement */}
        <div
          className="fixed inset-0 pointer-events-none z-0 transition-all duration-700 ease-out scale-110"
          style={{
            backgroundImage: `radial-gradient(circle at ${mousePosPx.x}px ${mousePosPx.y}px, rgba(6, 182, 212, 0.25) 0%, rgba(5, 5, 7, 0.92) 50%, rgba(0, 0, 0, 0.98) 100%), url('${activeWallpaper}')`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
            opacity: 0.45,
            transform: window.matchMedia('(prefers-reduced-motion: reduce)').matches 
              ? 'none' 
              : `translate3d(${mouseOffset.x * -25}px, ${mouseOffset.y * -25}px, 0) scale(1.08)`,
          }}
        />

        {/* Dynamic Cursor Spotlight Ambient Overlay */}
        <div
          className="fixed inset-0 pointer-events-none z-0 transition-opacity duration-300 opacity-60"
          style={{
            background: `radial-gradient(600px circle at ${mousePosPx.x}px ${mousePosPx.y}px, rgba(6, 182, 212, 0.08), transparent 80%)`,
          }}
        />

        {/* Content Layer */}
        <div className="relative z-10 flex flex-col min-h-screen">
          {!isAuthenticated ? (
            <AuthScreen />
          ) : (
            <>
              <Header
                activeHolds={activeHolds}
              />

              <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
                <Routes>
                  {user?.role === 'customer' ? (
                    <>
                      <Route
                        path="/"
                        element={
                          <BookingPage
                            activeHolds={activeHolds}
                            setActiveHolds={setActiveHolds}
                            onMovieSelect={setCurrentWallpaper}
                          />
                        }
                      />
                      <Route
                        path="/history"
                        element={<HistoryPage />}
                      />
                      <Route path="*" element={<Navigate to="/" replace />} />
                    </>
                  ) : user?.role === 'admin' ? (
                    <>
                      <Route path="/admin" element={<AdminPage />} />
                      <Route path="*" element={<Navigate to="/admin" replace />} />
                    </>
                  ) : (
                    <>
                      <Route path="/organiser" element={<OrganiserPage />} />
                      <Route path="*" element={<Navigate to="/organiser" replace />} />
                    </>
                  )}
                </Routes>
              </main>
            </>
          )}
        </div>
      </div>
    </BrowserRouter>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  );
};

export default App;
