import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Camera, UploadSimple, Scan, CheckCircle, Warning, ArrowRight, ArrowsClockwise, Sparkle, TShirt } from '@phosphor-icons/react'
import { skinToneAPI } from '../services/api'
import useStore from '../store/useStore'
import { motion, AnimatePresence } from 'framer-motion'

export default function SkinTonePage() {
  const navigate = useNavigate()
  const { setSkinTone, skinTone, setGender } = useStore()
  const fileRef = useRef(null)
  const videoRef = useRef(null)
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [mode, setMode] = useState('upload') 
  const [stream, setStream] = useState(null)
  const [selectedGender, setSelectedGender] = useState('pria')

  // Mapping label tampilan ke nilai backend
  const GENDER_OPTIONS = [
    { label: 'Pria', value: 'pria' },
    { label: 'Wanita', value: 'wanita' },
    { label: 'Hijab', value: 'wanitahijab' },
  ]

  const handleFile = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setPreview(URL.createObjectURL(file))
    setError('')
    detectFromFile(file)
  }

  const detectFromFile = async (file) => {
    setLoading(true);
    setError('');
    try {
      const res = await skinToneAPI.detect(file);
      
      if (typeof res === 'string' && res.includes('<!DOCTYPE html>')) {
        setError("Ngrok Error: Silakan klik 'Visit Site' dulu di browser HP/Laptop kamu.");
        return;
      }

      if (!res) {
        setError("Server tidak mengirimkan data. Coba upload ulang.");
        return;
      }

      setSkinTone({
        level: res.skin_tone_level || 3,
        hex: res.skin_tone_hex || "#D2B48C",
        label: res.skin_tone_label || "Medium",
        confidence: res.confidence || 0.95, 
        detection_id: res.detection_id || null,
        gender: res.gender || "pria"
      });
      
      // Jangan override gender dari CNN — biarkan user yang memilih secara eksplisit
      // agar hasil rekomendasi selalu sesuai pilihan user
    } catch (err) {
      setError(err.message || 'Gagal mendeteksi skin tone');
    } finally {
      setLoading(false);
    }
  };

  const startCamera = async () => {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
      setStream(s)
      setMode('camera')
      setTimeout(() => { if (videoRef.current) videoRef.current.srcObject = s }, 100)
    } catch {
      setError('Tidak dapat mengakses kamera.')
    }
  }

  const capturePhoto = () => {
    const canvas = document.createElement('canvas')
    canvas.width  = videoRef.current.videoWidth
    canvas.height = videoRef.current.videoHeight
    canvas.getContext('2d').drawImage(videoRef.current, 0, 0)
    canvas.toBlob((blob) => {
      const file = new File([blob], 'capture.jpg', { type: 'image/jpeg' })
      setPreview(URL.createObjectURL(blob))
      stream?.getTracks().forEach(t => t.stop())
      setStream(null)
      setMode('upload')
      detectFromFile(file)
    }, 'image/jpeg', 0.92)
  }

  const reset = () => {
    setPreview(null); setError(''); setSkinTone(null)
    stream?.getTracks().forEach(t => t.stop()); setStream(null); setMode('upload')
  }

  const handleLihatOutfit = () => {
    setGender(selectedGender);
    navigate('/recommendations', { state: { gender: selectedGender } });
  }

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1, duration: 0.6, ease: [0.32, 0.72, 0, 1] }
    }
  }
  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1, transition: { duration: 0.8, ease: [0.32, 0.72, 0, 1] } }
  }

  return (
    <div className="w-full max-w-[1400px] mx-auto px-6 py-12 md:py-24">
      
      {/* Editorial Header */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.8, ease: [0.32, 0.72, 0, 1] }} className="mb-16">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-[10px] font-semibold text-white/60 tracking-widest uppercase mb-6">
          <Scan size={14} weight="light" className="text-violet-400" /> Analisis Biometrik
        </div>
        <h1 className="font-display text-5xl md:text-6xl font-medium tracking-tight text-white mb-4">
          Deteksi <span className="text-white/40 italic">Skin Tone</span>
        </h1>
        <p className="text-white/50 text-lg max-w-xl font-light">
          Unggah foto atau gunakan kamera. EfficientNet-B0 akan mengekstrak fitur HSV dari wajah Anda.
        </p>
      </motion.div>

      <motion.div variants={containerVariants} initial="hidden" animate="visible" className="grid lg:grid-cols-12 gap-8">
        
        {/* Sisi Kiri: Input Zone */}
        <motion.div variants={itemVariants} className="lg:col-span-7 space-y-6">

          {/* === GENDER SELECTOR (WAJIB DIPILIH DULU) === */}
          <div>
            <p className="text-[10px] font-semibold text-white/40 uppercase tracking-[0.2em] mb-3">Pilih Kategori</p>
            <div className="flex gap-3">
              {GENDER_OPTIONS.map(opt => (
                <button
                  key={opt.value}
                  onClick={() => setSelectedGender(opt.value)}
                  className={`flex-1 py-3 rounded-2xl text-sm font-semibold transition-all duration-300 border ${
                    selectedGender === opt.value
                      ? 'bg-white text-black border-white shadow-lg scale-[1.02]'
                      : 'bg-white/5 text-white/50 border-white/10 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Toggle Upload / Kamera */}
          <div className="flex gap-4">
            <button onClick={() => { setMode('upload'); stream?.getTracks().forEach(t=>t.stop()); setStream(null) }}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl text-sm font-semibold transition-all duration-500 ${mode==='upload' ? 'bg-white text-black shadow-lg' : 'bg-white/5 text-white/50 hover:bg-white/10 border border-white/10'}`}>
              <UploadSimple size={18} weight={mode==='upload' ? "fill" : "light"} /> Upload Foto
            </button>
            <button onClick={startCamera}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-2xl text-sm font-semibold transition-all duration-500 ${mode==='camera' ? 'bg-white text-black shadow-lg' : 'bg-white/5 text-white/50 hover:bg-white/10 border border-white/10'}`}>
              <Camera size={18} weight={mode==='camera' ? "fill" : "light"} /> Kamera Langsung
            </button>
          </div>

          <div className="outer-shell aspect-[4/3]">
            <div className="inner-core flex items-center justify-center relative overflow-hidden">
              {mode === 'camera' && stream ? (
                <div className="relative w-full h-full">
                  <video ref={videoRef} autoPlay playsInline className="w-full h-full object-cover" />
                  <div className="absolute inset-0 border-[4px] border-black/20 pointer-events-none" />
                  <div className="absolute bottom-6 inset-x-0 flex justify-center">
                    <button onClick={capturePhoto} className="btn-premium bg-white text-black px-8 py-3 rounded-full font-semibold flex items-center gap-2">
                      <Camera size={18} weight="fill" /> Ambil Foto
                    </button>
                  </div>
                </div>
              ) : preview ? (
                <div className="relative w-full h-full">
                  <img src={preview} alt="preview" className="w-full h-full object-cover" />
                  {loading && (
                    <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex flex-col items-center justify-center gap-6 z-10">
                      <div className="relative">
                        <div className="w-16 h-16 rounded-full border border-white/20" />
                        <div className="absolute top-0 left-0 w-16 h-16 rounded-full border-t border-violet-500 animate-spin" />
                        <Scan size={24} weight="light" className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-white/50" />
                      </div>
                      <p className="text-xs text-white/60 font-semibold tracking-[0.3em] uppercase">Menganalisis Pigmen...</p>
                    </div>
                  )}
                </div>
              ) : (
                <button onClick={() => fileRef.current.click()}
                  className="absolute inset-0 w-full h-full flex flex-col items-center justify-center gap-6 text-white/40 hover:text-white/80 transition-colors group">
                  <div className="w-20 h-20 rounded-full border border-white/10 bg-white/5 group-hover:bg-white/10 flex items-center justify-center transition-colors">
                    <UploadSimple size={32} weight="light" />
                  </div>
                  <p className="font-medium text-sm tracking-wide">Pilih atau seret foto ke sini</p>
                </button>
              )}
            </div>
          </div>
          <input ref={fileRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />

          <AnimatePresence>
            {error && (
              <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="p-4 rounded-2xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start gap-3">
                <Warning size={18} weight="fill" className="mt-0.5 shrink-0" />
                <p>{error}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Sisi Kanan: Result Zone */}
        <motion.div variants={itemVariants} className="lg:col-span-5">
          <AnimatePresence mode="wait">
            {skinTone ? (
              <motion.div 
                key="result"
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.6, ease: [0.32, 0.72, 0, 1] }}
                className="space-y-6 h-full flex flex-col"
              >
                <div className="outer-shell flex-1">
                  <div className="inner-core p-8 flex flex-col">
                    <div className="flex items-center gap-2 text-white/60 text-xs font-semibold mb-8 uppercase tracking-widest">
                      <CheckCircle size={16} weight="fill" className="text-green-400" /> Analisis Selesai
                    </div>
                    
                    <div className="flex items-center gap-6 mb-10">
                      <div className="w-24 h-24 rounded-full shadow-2xl border border-white/10 relative" style={{ backgroundColor: skinTone.hex }}>
                         <div className="absolute inset-0 rounded-full border border-white/20 shadow-[inset_0_4px_10px_rgba(0,0,0,0.2)]" />
                      </div>
                      <div>
                        <p className="text-[10px] font-semibold text-white/40 uppercase tracking-[0.2em] mb-1">Terdeteksi</p>
                        <h2 className="text-4xl font-medium tracking-tight text-white mb-2">{skinTone.label}</h2>
                        <p className="text-white/60 text-sm">{skinTone.hex} • {(skinTone.confidence*100).toFixed(1)}% Akurat</p>
                      </div>
                    </div>

                    <div className="space-y-8 flex-1">
                      <div>
                        <p className="text-[10px] text-white/40 font-semibold uppercase tracking-[0.2em] mb-4">Warna Harmonis</p>
                        <div className="flex gap-3 flex-wrap">
                          {skinTone.recommended_colors?.map(c => (
                            <div key={c} className="w-12 h-12 rounded-full border border-white/10 shadow-lg relative group" style={{ backgroundColor: c }}>
                              <div className="absolute inset-0 rounded-full bg-white opacity-0 group-hover:opacity-20 transition-opacity" />
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      <div className="mt-auto pt-8 flex flex-col gap-4">
                        <button onClick={handleLihatOutfit} className="btn-premium w-full py-4 bg-white text-black rounded-full font-semibold transition-all flex items-center justify-center gap-3">
                          <Sparkle size={18} weight="fill" /> Lihat Mix & Match <ArrowRight size={18} weight="bold" />
                        </button>

                        <button onClick={() => navigate('/ar/baju-pro-1')} className="w-full py-4 bg-white/5 hover:bg-white/10 border border-white/10 text-white rounded-full font-semibold transition-all flex items-center justify-center gap-3">
                          <TShirt size={18} weight="light" /> Coba Virtual Try-On
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                <button onClick={reset} className="w-full py-4 text-white/40 hover:text-white text-sm flex items-center justify-center gap-2 transition-colors">
                  <ArrowsClockwise size={16} weight="light" /> Ulangi Analisis
                </button>
              </motion.div>
            ) : (
              <motion.div 
                key="empty"
                className="outer-shell h-full min-h-[400px]"
              >
                <div className="inner-core p-8 flex flex-col items-center justify-center text-center">
                  <Scan size={48} weight="light" className="text-white/20 mb-6" />
                  <p className="text-white/60 font-medium text-lg">Menunggu Input</p>
                  <p className="text-sm text-white/40 mt-3 max-w-[200px] leading-relaxed">Hasil ekstraksi fitur kulit akan muncul di sini.</p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </div>
  )
}