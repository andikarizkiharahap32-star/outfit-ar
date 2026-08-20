import React, { useState, useEffect } from 'react';
import { CaretLeft, CaretRight, Package } from '@phosphor-icons/react';
import { motion, AnimatePresence } from 'framer-motion';

export default function CarouselSlider({ items, title, onSelect }) {
  const [currentIndex, setCurrentIndex] = useState(0);

  // Beritahu parent component item mana yang sedang aktif saat pertama kali dimuat
  useEffect(() => {
    if (items && items.length > 0 && onSelect) {
      onSelect(items[currentIndex]);
    }
  }, []);

  const handleNext = () => {
    if (!items || items.length === 0) return;
    const nextIndex = (currentIndex + 1) % items.length;
    setCurrentIndex(nextIndex);
    if (onSelect) onSelect(items[nextIndex]);
  };

  const handlePrev = () => {
    if (!items || items.length === 0) return;
    const prevIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
    setCurrentIndex(prevIndex);
    if (onSelect) onSelect(items[prevIndex]);
  };

  if (!items || items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 w-48 bg-white/5 border border-white/10 rounded-2xl text-white/30">
        <Package size={32} weight="light" className="mb-2" />
        <p className="text-[10px] font-semibold uppercase tracking-widest text-center">No {title}<br/>Available</p>
      </div>
    );
  }

  const currentItem = items[currentIndex];
  // Asumsi data image_url sudah dibersihkan oleh Halaman Utama
  const safeImageUrl = currentItem?.image_url || "https://via.placeholder.com/200";

  return (
    <div className="flex flex-col items-center w-full relative">
      <h3 className="text-[10px] font-semibold text-white/40 mb-4 uppercase tracking-[0.3em]">{title}</h3>
      
      <div className="flex items-center justify-center gap-6 w-full">
        <button 
          onClick={handlePrev} 
          className="p-3 bg-white/5 hover:bg-white/10 rounded-full border border-white/10 text-white/60 hover:text-white transition-all shadow-lg hover:scale-105 active:scale-95 flex items-center justify-center"
        >
          <CaretLeft size={20} weight="bold"/>
        </button>
        
        {/* Kotak Gambar dengan Efek Glassmorphism */}
        <div className="outer-shell w-48 h-64 md:w-56 md:h-72">
          <div className="inner-core p-4 bg-[#050505]/60 flex flex-col h-full items-center justify-center overflow-hidden relative">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentItem.id || currentIndex}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3, ease: [0.32, 0.72, 0, 1] }}
                className="w-full h-full"
              >
                <img
                  src={safeImageUrl}
                  alt={currentItem.name || "Outfit"}
                  className="w-full h-full object-contain filter drop-shadow-2xl"
                />
              </motion.div>
            </AnimatePresence>
          </div>
        </div>
        
        <button 
          onClick={handleNext} 
          className="p-3 bg-white/5 hover:bg-white/10 rounded-full border border-white/10 text-white/60 hover:text-white transition-all shadow-lg hover:scale-105 active:scale-95 flex items-center justify-center"
        >
          <CaretRight size={20} weight="bold"/>
        </button>
      </div>

      <div className="mt-6 text-center max-w-[200px]">
        <p className="text-sm font-medium text-white/90 truncate">{currentItem.name}</p>
        <p className="text-[10px] text-white/40 font-semibold uppercase tracking-widest mt-1">
          {currentItem.color || "Unknown Color"}
        </p>
      </div>
    </div>
  );
}