import React from 'react';
import { useHoldCountdown } from '../hooks/useHoldCountdown';

interface HoldCountdownRingProps {
  expiresAt: string | null;
  size?: number;
  strokeWidth?: number;
}

export const HoldCountdownRing: React.FC<HoldCountdownRingProps> = ({
  expiresAt,
  size = 40,
  strokeWidth = 3,
}) => {
  const { secondsLeft, formattedTime, isExpired } = useHoldCountdown(expiresAt);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  
  // Total TTL is 10 mins (600s)
  const totalSeconds = 600;
  const progress = Math.max(0, Math.min(1, secondsLeft / totalSeconds));
  const strokeDashoffset = circumference - progress * circumference;

  return (
    <div className="relative inline-flex items-center justify-center">
      <svg width={size} height={size} className="transform -rotate-90">
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke="#27273a"
          strokeWidth={strokeWidth}
          fill="transparent"
        />
        {/* Progress ring */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={isExpired ? '#ef4444' : '#f59e0b'}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          fill="transparent"
          style={{ transition: 'stroke-dashoffset 1s linear' }}
        />
      </svg>
      <span
        className={`absolute text-[11px] font-mono font-bold ${
          isExpired ? 'text-red-400' : 'text-amber-400'
        }`}
      >
        {formattedTime}
      </span>
    </div>
  );
};
