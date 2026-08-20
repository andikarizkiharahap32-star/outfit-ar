import React from 'react';
import { CheckCircle, Warning, Fingerprint } from '@phosphor-icons/react';
import { motion } from 'framer-motion';

export default function MatchIndicator({ isMatch, score, message, isWaiting }) {
  
  if (isWaiting) {
    return (
      <motion.div 
        initial={{ opacity: 0, y: 10 }} 
        animate={{ opacity: 1, y: 0 }} 
        className="outer-shell w-full max-w-sm mx-auto"
      >
        <div className="inner-core bg-[#050505]/60 px-8 py-6 flex flex-col items-center justify-center gap-4">
          <Fingerprint weight="light" className="text-white/40 animate-pulse" size={36} />
          <p className="text-white/40 font-semibold tracking-[0.2em] uppercase text-[10px]">Analyzing Combination...</p>
        </div>
      </motion.div>
    );
  }

  if (isMatch) {
    return (
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }} 
        animate={{ opacity: 1, scale: 1 }} 
        transition={{ ease: [0.32, 0.72, 0, 1], duration: 0.5 }}
        className="outer-shell w-full max-w-sm mx-auto relative"
      >
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-emerald-500/10 blur-3xl rounded-full pointer-events-none" />
        <div className="inner-core bg-[#050505]/60 border-emerald-500/20 px-8 py-6 flex flex-col items-center justify-center gap-3 relative z-10 overflow-hidden">
          <CheckCircle weight="light" className="text-emerald-400" size={40} />
          <div className="text-center">
              <p className="text-emerald-400 font-semibold tracking-[0.2em] uppercase text-sm mb-1">Perfect Match</p>
              <p className="text-emerald-500/50 text-[10px] font-semibold tracking-widest uppercase">
                {message || `Color Harmony: ${score}%`}
              </p>
          </div>
        </div>
      </motion.div>
    );
  } else {
    return (
      <motion.div 
        initial={{ opacity: 0, scale: 0.95 }} 
        animate={{ opacity: 1, scale: 1 }}
        transition={{ ease: [0.32, 0.72, 0, 1], duration: 0.5 }} 
        className="outer-shell w-full max-w-sm mx-auto relative"
      >
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-48 h-48 bg-red-500/10 blur-3xl rounded-full pointer-events-none" />
        <div className="inner-core bg-[#050505]/60 border-red-500/20 px-8 py-6 flex flex-col items-center justify-center gap-3 relative z-10 overflow-hidden">
          <Warning weight="light" className="text-red-400" size={40} />
          <div className="text-center">
              <p className="text-red-400 font-semibold tracking-[0.2em] uppercase text-sm mb-1">Color Clash</p>
              <p className="text-red-500/50 text-[10px] font-semibold tracking-widest uppercase">
                {message || `Color Harmony: ${score}%`}
              </p>
          </div>
        </div>
      </motion.div>
    );
  }
}