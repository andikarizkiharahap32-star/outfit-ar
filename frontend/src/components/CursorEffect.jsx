import React, { useEffect, useState } from 'react';

export default function CursorEffect() {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [clicked, setClicked] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    // Cek jika user buka dari HP (efek cursor dimatikan di HP agar tidak berat)
    const checkMobile = () => setIsMobile(window.innerWidth < 768);
    checkMobile();

    const moveCursor = (e) => {
      setPosition({ x: e.clientX, y: e.clientY });
    };

    const handleClick = () => {
      setClicked(true);
      setTimeout(() => setClicked(false), 300);
    };

    window.addEventListener('mousemove', moveCursor);
    window.addEventListener('mousedown', handleClick);
    window.addEventListener('resize', checkMobile);

    return () => {
      window.removeEventListener('mousemove', moveCursor);
      window.removeEventListener('mousedown', handleClick);
      window.removeEventListener('resize', checkMobile);
    };
  }, []);

  if (isMobile) return null; // Sembunyikan di HP

  return (
    <>
      {/* 1. Titik Utama Cursor (Dot) */}
      <div 
        className="fixed pointer-events-none z-[9999] w-2 h-2 bg-white rounded-full transition-transform duration-75 ease-out"
        style={{ left: position.x, top: position.y, transform: 'translate(-50%, -50%)' }}
      />

      {/* 2. Cahaya Glow yang Mengikuti (Outer Glow) */}
      <div 
        className="fixed pointer-events-none z-[9998] w-12 h-12 rounded-full bg-purple-500/20 blur-xl transition-all duration-300 ease-out"
        style={{ 
          left: position.x, 
          top: position.y, 
          transform: `translate(-50%, -50%) scale(${clicked ? 1.5 : 1})` 
        }}
      />

      {/* 3. Ripple Effect saat Klik */}
      <div 
        className={`fixed pointer-events-none z-[9999] rounded-full border border-pink-500/50 transition-all duration-500 ease-out ${
          clicked ? 'w-16 h-16 opacity-0 scale-150' : 'w-0 h-0 opacity-100 scale-0'
        }`}
        style={{ left: position.x, top: position.y, transform: 'translate(-50%, -50%)' }}
      />
    </>
  );
}