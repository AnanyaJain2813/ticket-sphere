import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, ShieldCheck, Zap, Database } from 'lucide-react';

export const AboutPage: React.FC = () => {
  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '40px 20px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1e293b' }}>
      <Link to="/" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', color: '#64748b', textDecoration: 'none', fontWeight: 600, fontSize: '14px', marginBottom: '24px' }}>
        <ArrowLeft size={16} /> Back to Dashboard
      </Link>

      <h1 style={{ fontSize: '32px', fontWeight: 800, margin: '0 0 16px 0', color: '#0f172a' }}>
        System Architecture & Stack
      </h1>
      <p style={{ fontSize: '16px', color: '#64748b', lineHeight: 1.6, marginBottom: '32px' }}>
        This full-stack system is designed for high-concurrency ticket booking across movies and live concerts.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <div style={{ padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0', background: '#ffffff' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={20} color="#2563eb" /> Backend Django Apps
          </h3>
          <ul style={{ margin: 0, paddingLeft: '20px', color: '#475569', lineHeight: 1.8 }}>
            <li><strong>accounts</strong>: User authentication, customer profiles, and session management.</li>
            <li><strong>venues</strong>: Stadiums, theaters, seating grids (coordinates, rows, categories).</li>
            <li><strong>events</strong>: Movies, concerts, performers, and scheduled showtimes.</li>
            <li><strong>bookings</strong>: Atomic holds, reservations, tickets, and payment states.</li>
            <li><strong>waitlist</strong>: Priority queues and automated seat release notifications.</li>
          </ul>
        </div>

        <div style={{ padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0', background: '#ffffff' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={20} color="#0891b2" /> Infrastructure & Services
          </h3>
          <ul style={{ margin: 0, paddingLeft: '20px', color: '#475569', lineHeight: 1.8 }}>
            <li><strong>PostgreSQL</strong>: Database with ACID compliance and row-level locking.</li>
          </ul>
        </div>

        <div style={{ padding: '20px', borderRadius: '12px', border: '1px solid #e2e8f0', background: '#ffffff' }}>
          <h3 style={{ fontSize: '18px', fontWeight: 700, margin: '0 0 10px 0', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <ShieldCheck size={20} color="#16a34a" /> Concurrency & Atomic Hold Ready
          </h3>
          <p style={{ margin: 0, color: '#475569', lineHeight: 1.6 }}>
            Prepared for atomic conditional updates (<code>select_for_update</code>) and lock-free concurrency protections to prevent race conditions during ticket rush.
          </p>
        </div>
      </div>
    </div>
  );
};
