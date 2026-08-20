import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Scan, Sparkle, ArrowRight, Lightning } from '@phosphor-icons/react';
import useStore from '../store/useStore';
import { motion } from 'framer-motion';

export default function HomePage() {
  const navigate = useNavigate();
  const skinTone = useStore((s) => s.skinTone);

  return (
    <div className="min-h-screen bg-[#050505] text-white overflow-hidden relative selection:bg-white/20">
      
      {/* Background Orbs */}
      <div className="absolute top-[-20%] left-[-10%] w-[800px] h-[800px] bg-white/5 blur-[120px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-white/5 blur-[120px] rounded-full pointer-events-none" />

      {/* Main Content */}
      <div className="relative max-w-7xl mx-auto px-6 pt-24 pb-32 min-h-screen flex items-center">
        <div className="grid lg:grid-cols-2 gap-16 items-center w-full">
          
          {/* Left Hero */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ease: [0.32, 0.72, 0, 1], duration: 1 }}
            className="space-y-8 relative z-10"
          >
            {/* Tech Stack Badge */}
            <div className="inline-flex items-center gap-3 px-5 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-md">
              <Lightning size={16} weight="fill" className="text-white/60" />
              <span className="text-[10px] uppercase tracking-widest font-semibold text-white/60">CNN EfficientNet • KNN • AR Real-time</span>
            </div>

            <h1 className="text-6xl md:text-8xl font-medium tracking-tighter leading-[1.1]">
              Outfit Sempurna <br />
              <span className="italic font-light text-white/50">Warna Kulitmu</span>
            </h1>

            <p className="text-lg text-white/40 max-w-lg font-light leading-relaxed">
              Deteksi skin tone otomatis. Rekomendasi outfit cerdas.
              Virtual Try-On AR real-time sebelum kamu beli.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 pt-4">
              <button 
                onClick={() => navigate('/skin-tone')}
                className="btn-premium group flex items-center justify-center gap-3 bg-white text-black px-8 py-5 rounded-full font-medium text-sm tracking-wide transition-all hover:scale-105"
              >
                <Scan size={20} weight="bold" />
                Mulai Scan Kulit
                <ArrowRight size={18} weight="bold" className="group-hover:translate-x-1 transition-transform" />
              </button>

              {skinTone && (
                <button 
                  onClick={() => navigate('/recommendations')}
                  className="flex items-center justify-center gap-3 px-8 py-5 border border-white/20 hover:border-white/40 hover:bg-white/5 rounded-full font-medium text-sm tracking-wide transition-all"
                >
                  <Sparkle size={20} weight="fill" className="text-white/60" />
                  Lihat Rekomendasi
                </button>
              )}
            </div>
          </motion.div>

          {/* Right Visual (Double-Bezel Card) */}
          <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ ease: [0.32, 0.72, 0, 1], duration: 1, delay: 0.2 }}
            className="relative lg:h-[600px] outer-shell"
          >
            <div className="inner-core bg-[#050505] p-2 h-full flex flex-col justify-end overflow-hidden group">
              <img 
                src="https://images.unsplash.com/photo-1602810318383-e386cc2a3ccf?q=80&w=1170&auto=format&fit=crop" 
                alt="Premium Outfit"
                className="absolute inset-0 w-full h-full object-cover opacity-60 group-hover:opacity-80 transition-opacity duration-700 group-hover:scale-105"
              />
              
              <div className="relative z-10 m-6 bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl p-6 self-start">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
                  <span className="text-[10px] font-bold uppercase tracking-widest text-white/60">AR Engine Ready</span>
                </div>
                <p className="text-sm font-medium">Virtual Try-On 3D Aktif</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Floating Status */}
      {skinTone && (
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 bg-[#050505]/80 backdrop-blur-2xl border border-white/10 px-6 py-4 rounded-full flex items-center gap-4 shadow-2xl"
        >
          <div className="w-6 h-6 rounded-full border border-white/20" style={{ backgroundColor: skinTone.hex }} />
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-white/40 mb-0.5">Skin tone terdeteksi</p>
            <p className="text-xs font-semibold">{skinTone.label} • Level {skinTone.level}</p>
          </div>
        </motion.div>
      )}
    </div>
  );
}