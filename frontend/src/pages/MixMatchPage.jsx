import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Sparkle, WarningCircle } from '@phosphor-icons/react';
import CarouselSlider from '../components/ui/CarouselSlider';
import MatchIndicator from '../components/ui/MatchIndicator';
import useStore from '../store/useStore';
import api, { BACKEND_URL, productAPI } from '../services/api';

// Fungsi untuk membersihkan URL Gambar (Anti-Patah)
function buildImageUrl(rawPath) {
  if (!rawPath) return '';
  
  if (rawPath.startsWith('http://') || rawPath.startsWith('https://')) {
    return rawPath;
  }
  
  let clean = rawPath.replace(/\\/g, '/').replace(/\/+/g, '/').trim();
  if (clean.startsWith('/')) clean = clean.substring(1);
  clean = clean.replace(/\b(products|Pria|Wanita|Unisex)\s+/ig, '$1/');
  
  if (!clean.toLowerCase().startsWith('products/') && !clean.toLowerCase().startsWith('uploads/') && !clean.toLowerCase().startsWith('storage/')) {
    clean = 'products/' + clean;
  }
  
  // Menggunakan BACKEND_URL tersentralisasi dari api.js
  const base = BACKEND_URL.replace(/\/+$/, '');
  
  if (!clean.toLowerCase().startsWith('uploads/') && !clean.toLowerCase().startsWith('storage/')) {
    return `${base}/uploads/${clean}`;
  }
  return `${base}/${clean}`;
}

export default function MixMatchPage() {
  const navigate = useNavigate();
  // Baca gender dari Zustand store — diset oleh SkinTonePage saat user klik "Lihat Mix & Match"
  const storeGender = useStore(state => state.gender);
  const activeGender = storeGender || 'pria';

  // State untuk menyimpan data Real dari MySQL
  const [tops, setTops] = useState([]);
  const [bottoms, setBottoms] = useState([]);
  
  const [selectedTop, setSelectedTop] = useState(null);
  const [selectedBottom, setSelectedBottom] = useState(null);
  
  const [isLoadingData, setIsLoadingData] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [matchResult, setMatchResult] = useState({ isMatch: true, score: 100, msg: "Memulai Analisis..." });

  // 1. FETCH DATA SUNGGUHAN DARI BACKEND MENGGUNAKAN API.JS
  useEffect(() => {
    const fetchRealProducts = async () => {
      setIsLoadingData(true);
      try {
        const data = await productAPI.list({ limit: 100, gender: activeGender });
        const items = data.data || data.items || [];
        
        const fetchedTops = [];
        const fetchedBottoms = [];

        // Langsung pakai URL tanpa blob fetch massal (blob fetch 100+ request = lambat)
        items.forEach((p) => {
          const name = (p.name || "").toLowerCase();
          p.image_url = buildImageUrl(p.image_url); // Langsung build URL, tanpa fetch tambahan
          
          // Pemisah Atasan & Bawahan berdasarkan nama produk
          if (name.includes("celana") || name.includes("jeans") || name.includes("chino") || 
              name.includes("jogger") || name.includes("rok") || name.includes("pants") ||
              name.includes("shorts") || name.includes("legging") || name.includes("skirt")) {
            fetchedBottoms.push(p);
          } else {
            fetchedTops.push(p);
          }
        });

        setTops(fetchedTops);
        setBottoms(fetchedBottoms);
        
      } catch (err) {
        console.error("Fetch Error:", err);
      } finally {
        setIsLoadingData(false);
      }
    };

    fetchRealProducts();
  }, []);

  // 2. AI ANALYZER (LOGIKA WARNA REAL-TIME)
  useEffect(() => {
    if (!selectedTop || !selectedBottom) return;

    setIsAnalyzing(true);
    
    const timer = setTimeout(() => {
      const topColor = (selectedTop.color || "").toLowerCase();
      const botColor = (selectedBottom.color || "").toLowerCase();

      // Warna netral yang bisa dipakai dengan semua kombinasi
      const neutrals = ["hitam", "putih", "abu", "cream", "krem", "beige", "white", "black", "grey", "gray"];
      const isTopNeutral = neutrals.some(n => topColor.includes(n));
      const isBotNeutral = neutrals.some(n => botColor.includes(n));

      // Pasangan warna yang secara teori mode cocok (complementary)
      const goodPairs = [
        ["biru", "cokelat"], ["biru", "krem"], ["biru", "putih"], ["biru", "abu"],
        ["hijau", "krem"], ["hijau", "cokelat"], ["hijau", "putih"],
        ["kuning", "biru"], ["kuning", "hitam"], ["kuning", "abu"],
        ["merah", "hitam"], ["merah", "abu"], ["merah", "biru"],
        ["ungu", "abu"], ["ungu", "krem"], ["ungu", "hitam"],
        ["oranye", "biru"], ["oranye", "hitam"], ["oranye", "abu"],
      ];

      // Warna yang bertabrakan (clash)
      const clashPairs = [
        ["merah", "oranye"], ["merah", "pink"], ["hijau", "ungu"],
        ["biru", "oranye"], ["kuning", "hijau"], ["merah", "hijau"],
      ];

      let score = 60;
      let msg = "Kombinasi Standar";

      if (topColor === botColor) {
        score = 95; msg = "Monokromatik yang Elegan";
      } else if (isTopNeutral && isBotNeutral) {
        score = 92; msg = "Paduan Netral yang Sempurna";
      } else if (isTopNeutral || isBotNeutral) {
        score = 88; msg = "Kombinasi Netral yang Aman";
      } else if (goodPairs.some(([a, b]) => 
        (topColor.includes(a) && botColor.includes(b)) || 
        (topColor.includes(b) && botColor.includes(a))
      )) {
        score = 85; msg = "Kombinasi Komplementer yang Bagus";
      } else if (clashPairs.some(([a, b]) => 
        (topColor.includes(a) && botColor.includes(b)) || 
        (topColor.includes(b) && botColor.includes(a))
      )) {
        score = 42; msg = "Warna Bertabrakan — Kurang Cocok";
      } else {
        score = 65; msg = "Kombinasi Eksperimental";
      }

      const isMatch = score >= 70;
      setMatchResult({ isMatch, score, msg });
      setIsAnalyzing(false);
    }, 800); // Dikurangi dari 1200ms ke 800ms

    return () => clearTimeout(timer);
  }, [selectedTop, selectedBottom]);

  if (isLoadingData) {
      return (
          <div className="min-h-screen bg-[#050505] text-white flex flex-col items-center justify-center gap-6">
              <div className="w-16 h-16 border-2 border-t-white border-white/10 rounded-full animate-spin" />
              <p className="text-[10px] font-semibold tracking-[0.5em] text-white/50 uppercase animate-pulse">Menghubungkan ke Database...</p>
          </div>
      );
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white p-6 font-sans flex flex-col lg:flex-row items-center justify-center gap-10 overflow-hidden relative">
      
      {/* Efek Latar Belakang */}
      <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-white/5 blur-[100px] rounded-full pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-white/5 blur-[100px] rounded-full pointer-events-none" />

      {/* Tombol Kembali */}
      <button 
        onClick={() => navigate('/products')}
        className="absolute top-8 left-8 z-50 flex items-center gap-3 px-6 py-3 bg-white/5 backdrop-blur-md border border-white/10 rounded-full text-white/60 hover:text-white hover:bg-white/10 transition-all text-xs font-semibold uppercase tracking-widest"
      >
        <ArrowLeft size={16} weight="bold" /> Katalog
      </button>

      {/*  AREA KIRI: STUDIO KOMBINASI  */}
      <div className="outer-shell w-full max-w-md z-10 mt-16 lg:mt-0">
        <div className="inner-core bg-[#050505]/60 flex flex-col items-center p-8 md:p-12">
          <div className="flex items-center gap-3 mb-6">
              <Sparkle size={20} weight="fill" className="text-white/60 animate-pulse" />
              <h1 className="text-2xl font-medium tracking-widest text-white uppercase">Outfit Studio</h1>
          </div>
          
          {tops.length > 0 ? (
              <CarouselSlider title="Atasan (Top)" items={tops} onSelect={setSelectedTop} />
          ) : (
              <div className="h-48 flex items-center justify-center text-white/30 text-xs">Atasan kosong/gagal dimuat</div>
          )}
          
          <div className="w-full border-b border-white/10 my-4 border-dashed relative">
             <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[#050505] px-6 py-1 rounded-full text-[9px] text-white/40 font-semibold tracking-[0.3em] border border-white/5 shadow-lg">
                MIX WITH
             </div>
          </div>

          {bottoms.length > 0 ? (
              <CarouselSlider title="Bawahan (Bottom)" items={bottoms} onSelect={setSelectedBottom} />
          ) : (
              <div className="h-48 flex items-center justify-center text-white/30 text-xs">Bawahan kosong/gagal dimuat</div>
          )}
        </div>
      </div>

      {/* 🧠 AREA KANAN: PANEL ANALISIS AI 🧠 */}
      <div className="flex flex-col gap-6 w-full max-w-sm z-10">
        <div className="text-center lg:text-left">
            <p className="text-[10px] text-white/40 font-semibold uppercase tracking-[0.4em] mb-2">Diagnostic Engine</p>
            <h2 className="text-5xl font-medium italic tracking-tighter mb-4 text-white">
                AI Analysis
            </h2>
        </div>

        <MatchIndicator 
            isWaiting={isAnalyzing} 
            isMatch={matchResult.isMatch} 
            score={matchResult.score} 
            message={matchResult.msg} 
        />

        <div className="outer-shell mt-2">
          <div className="inner-core p-5 bg-white/5">
              <p className="text-xs text-white/50 leading-relaxed font-light text-center">
                  Algoritma menganalisis keharmonisan spektrum warna antara {selectedTop?.name || 'atasan'} dan {selectedBottom?.name || 'bawahan'}.
              </p>
          </div>
        </div>

        <button 
            disabled={isAnalyzing || !matchResult.isMatch}
            // Karena belum ada 3D untuk celana, untuk di arahkan ke AR Try-On untuk baju atasannya saja jika "Match"
            onClick={() => selectedTop && navigate(`/ar/${selectedTop.id}`)}
            className={`mt-4 py-5 rounded-[20px] text-xs font-semibold uppercase tracking-widest transition-all duration-300 flex items-center justify-center gap-3 ${
                isAnalyzing || !matchResult.isMatch 
                ? 'bg-white/5 text-white/30 cursor-not-allowed border border-white/5' 
                : 'btn-premium bg-white text-black hover:bg-gray-200'
            }`}
        >
            {isAnalyzing ? 'Menganalisis...' : (!matchResult.isMatch ? 'Ganti Kombinasi' : 'Visualize Top in AR')}
        </button>
      </div>

    </div>
  );
}