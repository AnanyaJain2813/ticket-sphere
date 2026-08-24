import React, { useEffect, useState } from 'react';
import { checkHealth } from '../api/client';
import { Activity, CheckCircle, XCircle, RefreshCw, Server, Database, Layers, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';

interface HealthData {
  status: string;
  timestamp: string;
  database: string;
  service: string;
  apps?: string[];
}

export const HomePage: React.FC = () => {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await checkHealth();
      setHealth(data);
    } catch (err: any) {
      setError(err.message || 'Failed to connect to backend service.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '40px 20px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1e293b' }}>
      <header style={{ marginBottom: '40px', textAlign: 'center' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', background: '#eff6ff', color: '#2563eb', padding: '6px 16px', borderRadius: '20px', fontSize: '14px', fontWeight: 600, marginBottom: '16px' }}>
          <Layers size={18} /> Full-Stack Architecture Scaffold
        </div>
        <h1 style={{ fontSize: '36px', fontWeight: 800, margin: '0 0 12px 0', color: '#0f172a' }}>
          Ticket Booking System
        </h1>
        <p style={{ fontSize: '18px', color: '#64748b', maxWidth: '600px', margin: '0 auto' }}>
          Django + DRF Backend with PostgreSQL & React + Vite + Router Frontend.
        </p>
      </header>

      <section style={{ background: '#ffffff', borderRadius: '16px', padding: '28px', border: '1px solid #e2e8f0', boxShadow: '0 4px 20px -2px rgba(0, 0, 0, 0.05)', marginBottom: '32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Activity size={22} color="#2563eb" /> Backend Health Check Endpoint
          </h2>
          <button
            onClick={fetchHealth}
            disabled={loading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '8px',
              border: '1px solid #cbd5e1',
              background: '#f8fafc',
              color: '#334155',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontWeight: 600,
              fontSize: '14px',
              transition: 'all 0.2s',
            }}
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} /> {loading ? 'Checking...' : 'Refresh Status'}
          </button>
        </div>

        {loading && !health ? (
          <div style={{ padding: '40px', textAlign: 'center', color: '#64748b' }}>
            Checking API connectivity to <code>/api/health/</code>...
          </div>
        ) : error ? (
          <div style={{ padding: '20px', borderRadius: '12px', background: '#fef2f2', border: '1px solid #fecaca', color: '#991b1b', display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <XCircle size={24} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontWeight: 700, marginBottom: '4px' }}>Backend Unreachable</div>
              <div style={{ fontSize: '14px', color: '#b91c1c' }}>{error}</div>
              <div style={{ fontSize: '12px', marginTop: '8px', color: '#64748b' }}>Ensure Django server is running on <code>http://localhost:8000</code>.</div>
            </div>
          </div>
        ) : health ? (
          <div style={{ padding: '20px', borderRadius: '12px', background: '#f0fdf4', border: '1px solid #bbf7d0' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#166534', fontWeight: 700, fontSize: '18px', marginBottom: '16px' }}>
              <CheckCircle size={22} color="#16a34a" /> Backend is Healthy ({health.status.toUpperCase()})
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
              <div style={{ background: '#ffffff', padding: '12px 16px', borderRadius: '8px', border: '1px solid #dcfce7' }}>
                <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Service</div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#0f172a', marginTop: '2px' }}>{health.service}</div>
              </div>
              <div style={{ background: '#ffffff', padding: '12px 16px', borderRadius: '8px', border: '1px solid #dcfce7' }}>
                <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Database Status</div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: '#0f172a', marginTop: '2px' }}>{health.database}</div>
              </div>
              <div style={{ background: '#ffffff', padding: '12px 16px', borderRadius: '8px', border: '1px solid #dcfce7' }}>
                <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600 }}>Timestamp</div>
                <div style={{ fontSize: '13px', fontWeight: 500, color: '#0f172a', marginTop: '2px' }}>{new Date(health.timestamp).toLocaleString()}</div>
              </div>
            </div>

            {health.apps && (
              <div style={{ marginTop: '16px' }}>
                <div style={{ fontSize: '12px', color: '#64748b', textTransform: 'uppercase', fontWeight: 600, marginBottom: '8px' }}>Configured Django Apps</div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {health.apps.map((app) => (
                    <span key={app} style={{ background: '#e0f2fe', color: '#0369a1', padding: '4px 10px', borderRadius: '6px', fontSize: '13px', fontWeight: 600 }}>
                      {app}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : null}
      </section>

      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '20px' }}>
        <div style={{ padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', background: '#ffffff' }}>
          <Server size={28} color="#2563eb" style={{ marginBottom: '12px' }} />
          <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 8px 0' }}>Django DRF Backend</h3>
          <p style={{ fontSize: '14px', color: '#64748b', lineHeight: 1.5, margin: 0 }}>
            Structured with 5 modular apps: <code>accounts</code>, <code>venues</code>, <code>events</code>, <code>bookings</code>, and <code>waitlist</code>.
          </p>
        </div>

        <div style={{ padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', background: '#ffffff' }}>
          <Database size={28} color="#0891b2" style={{ marginBottom: '12px' }} />
          <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 8px 0' }}>PostgreSQL Database</h3>
          <p style={{ fontSize: '14px', color: '#64748b', lineHeight: 1.5, margin: 0 }}>
            Reliable, ACID-compliant relational data modeling.
          </p>
        </div>

        <div style={{ padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', background: '#ffffff' }}>
          <Layers size={28} color="#7c3aed" style={{ marginBottom: '12px' }} />
          <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 8px 0' }}>React 19 + Vite Router</h3>
          <p style={{ fontSize: '14px', color: '#64748b', lineHeight: 1.5, margin: 0 }}>
            Type-safe client with Axios API wrapper and client-side routing.
          </p>
          <div style={{ marginTop: '16px' }}>
            <Link to="/about" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', color: '#2563eb', textDecoration: 'none', fontWeight: 600, fontSize: '14px' }}>
              View System Overview <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};
