import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Sparkles } from 'lucide-react';

export default function LoadingSpinner({ text, fullScreen = false }) {
  // Array teks yang akan berganti-ganti untuk memberikan ilusi AI sedang bekerja keras
  const aiPhrases = [
    "Menyinkronkan Data Neural...",
    "Mengekstrak Fitur Visual...",
    "Menghitung Jarak Euclidean...",
    "Mencocokkan Palet Warna...",
    "Merender Model 3D..."
  ];

  const [phraseIndex, setPhraseIndex] = useState(0);

  // Efek untuk mengganti teks setiap 2 detik jika tidak ada prop 'text' yang dikirim
  useEffect(() => {
    if (text) return; // Jika teks di-hardcode dari luar, matikan rotasi teks

    const interval = setInterval(() => {
      setPhraseIndex((prev) => (prev + 1) % aiPhrases.length);
    }, 2000);

    return () => clearInterval(interval);
  }, [text]);

  const displayMessage = text || aiPhrases[phraseIndex];

  const content = (
    <div className="flex flex-col items-center justify-center gap-6 p-8">
      {/* 🚀 ANIMASI CINCIN RADAR AI */}
      <div className="relative flex items-center justify-center w-20 h-20">
        {/* Lingkaran Luar (Biru - Berputar Searah Jarum Jam) */}
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 3, ease: "linear" }}
          className="absolute inset-0 border-2 border-transparent border-t-blue-500 border-r-blue-500/30 rounded-full shadow-[0_0_15px_rgba(59,130,246,0.5)]"
        />
        
        {/* Lingkaran Dalam (Ungu - Berputar Berlawanan Arah) */}
        <motion.div
          animate={{ rotate: -360 }}
          transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
          className="absolute inset-2 border-2 border-transparent border-b-purple-500 border-l-purple-500/30 rounded-full shadow-[0_0_10px_rgba(168,85,247,0.4)]"
        />
        
        {/* Ikon Pusat yang Berdenyut */}
        <motion.div
          animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
          transition={{ repeat: Infinity, duration: 1.5, ease: "easeInOut" }}
        >
          <Sparkles className="text-white opacity-80" size={24} />
        </motion.div>
      </div>

      {/* 📝 TEKS STATUS */}
      <div className="flex flex-col items-center gap-2">
        <motion.p 
          key={displayMessage} // Kunci ini membuat animasi berjalan setiap teks berganti
          initial={{ opacity: 0, y: 5 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -5 }}
          className="text-[10px] font-black tracking-[0.4em] text-blue-400 uppercase text-center"
        >
          {displayMessage}
        </motion.p>
        
        {/* Progress Bar palsu kecil di bawah teks */}
        <div className="w-32 h-0.5 bg-white/10 rounded-full overflow-hidden">
            <motion.div 
                className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
                initial={{ width: "0%" }}
                animate={{ width: "100%" }}
                transition={{ repeat: Infinity, duration: 2, ease: "linear" }}
            />
        </div>
      </div>
    </div>
  );

  // Jika dipanggil dengan prop fullScreen={true}, bungkus dengan background hitam transparan
  if (fullScreen) {
    return (
      <div className="fixed inset-0 z-[9999] bg-[#050508]/80 backdrop-blur-sm flex items-center justify-center">
        {content}
      </div>
    );
  }

  return content;
}