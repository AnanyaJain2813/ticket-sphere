import { useState, useEffect } from 'react';

export const useHoldCountdown = (expiresAtIso: string | null) => {
  const calculateRemainingSeconds = (expiryStr: string | null): number => {
    if (!expiryStr) return 0;
    const expiryTime = new Date(expiryStr).getTime();
    const now = Date.now();
    const diff = Math.max(0, Math.floor((expiryTime - now) / 1000));
    return diff;
  };

  const [secondsLeft, setSecondsLeft] = useState<number>(() =>
    calculateRemainingSeconds(expiresAtIso)
  );

  useEffect(() => {
    setSecondsLeft(calculateRemainingSeconds(expiresAtIso));

    if (!expiresAtIso) return;

    const interval = setInterval(() => {
      const remaining = calculateRemainingSeconds(expiresAtIso);
      setSecondsLeft(remaining);
      if (remaining <= 0) {
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [expiresAtIso]);

  const formattedTime = `${Math.floor(secondsLeft / 60)}:${(secondsLeft % 60)
    .toString()
    .padStart(2, '0')}`;

  return {
    secondsLeft,
    formattedTime,
    isExpired: secondsLeft <= 0 && expiresAtIso !== null,
  };
};
