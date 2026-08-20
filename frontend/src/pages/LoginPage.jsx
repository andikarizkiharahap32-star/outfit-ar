import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, Lock, ArrowRight, ArrowLeft, Sparkles, User } from 'lucide-react';
import { motion } from 'framer-motion';

import { authAPI } from '../services/api';
import useStore from '../store/useStore';

export default function LoginPage() {
  const navigate = useNavigate();
  const setUser = useStore((state) => state.setUser);
  
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLogin, setIsLogin] = useState(true); // Toggle antara Login & Register
  
  // 👇 Tambahan State Loading agar tombol tidak bisa di-spam klik
  const [loading, setLoading] = useState(false); 

  // 👇 Tambahan kata 'async' di sini sangat penting untuk await API
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
        if (isLogin) {
            // PROSES LOGIN
            const res = await authAPI.login({ email, password });
            
            // Simpan token dengan aman (menyesuaikan format token umum FastAPI)
            const token = res.access_token || res.token || (res.access && res.access.token);
            if (token) localStorage.setItem('outfit_ar_token', token);
            
            // Simpan profil user
            if (res.user) setUser(res.user);
            
            // Langsung arahkan ke Skin Tone Page
            navigate('/skin-tone'); 
        } else {
            // PROSES DAFTAR
            await authAPI.register({ name, email, password });
            
            // Otomatis Login setelah sukses mendaftar
            const res = await authAPI.login({ email, password });
            const token = res.access_token || res.token || (res.access && res.access.token);
            if (token) localStorage.setItem('outfit_ar_token', token);
            if (res.user) setUser(res.user);
            
            // Langsung arahkan ke Skin Tone Page (keren & profesional)
            navigate('/skin-tone');
        }
    } catch (error) {
        console.error("Error during authentication:", error);
        // Tampilkan pesan error dari backend jika ada, jika tidak pakai pesan default
        alert(error.message || "Terjadi kesalahan saat mencoba masuk/daftar. Periksa koneksi backend Anda.");
    } finally {
        setLoading(false); // Matikan loading apapun hasilnya
    }
  };

  return (
    <div className="min-h-screen bg-[#050508] relative overflow-hidden flex items-center justify-center p-6 font-sans">
      
      {/* Background Effects (Sangat Premium) */}
      <div className="absolute top-[-10%] left-[-10%] w-[600px] h-[600px] bg-purple-600/30 rounded-full blur-[140px] animate-[pulse_8s_ease-in-out_infinite]" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[500px] h-[500px] bg-blue-600/20 rounded-full blur-[120px] animate-[pulse_10s_ease-in-out_infinite_reverse]" />
      <div className="absolute top-[40%] right-[30%] w-[300px] h-[300px] bg-pink-500/10 rounded-full blur-[100px] animate-[bounce_12s_infinite]" />
      <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/carbon-fibre.png')] opacity-[0.03] pointer-events-none" />

      {/* Tombol Kembali */}
      <button 
        onClick={() => navigate('/')}
        className="absolute top-8 left-8 text-gray-400 hover:text-white flex items-center gap-2 transition-colors z-50 bg-white/5 px-4 py-2 rounded-full border border-white/10 backdrop-blur-md"
      >
        <ArrowLeft size={16} /> Beranda
      </button>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="w-full max-w-md relative z-10"
      >
        <div className="bg-[#0A0A0F]/80 backdrop-blur-3xl border border-white/5 p-8 sm:p-10 rounded-[40px] shadow-[0_0_80px_rgba(147,51,234,0.15)] relative overflow-hidden">
          
          {/* Efek Garis Menyala di atas form */}
          <div className="absolute top-0 inset-x-0 h-[2px] bg-gradient-to-r from-transparent via-purple-500 to-transparent opacity-50" />

          <div className="text-center mb-10">
            <motion.div 
              animate={{ rotate: 360 }}
              transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
              className="w-20 h-20 bg-gradient-to-br from-purple-600 via-pink-500 to-blue-500 rounded-3xl mx-auto flex items-center justify-center mb-6 shadow-[0_0_30px_rgba(147,51,234,0.4)] relative"
            >
              <div className="absolute inset-1 bg-[#0A0A0F] rounded-[22px] flex items-center justify-center">
                <Sparkles className="text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400" size={32} />
              </div>
            </motion.div>
            
            <h1 className="text-4xl font-black text-transparent bg-clip-text bg-gradient-to-r from-white to-gray-400 tracking-tighter uppercase italic drop-shadow-lg">
              {isLogin ? 'Welcome Back' : 'Join OutfitAR'}
            </h1>
            <p className="text-gray-400 text-sm mt-3 font-medium">
              {isLogin ? 'Akses koleksi Skin Tone & AR Anda sekarang.' : 'Buka portal ke masa depan fashion AI.'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {!isLogin && (
               <div className="relative group">
                 <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                   <User className="text-gray-500 group-focus-within:text-purple-400 transition-colors" size={18} />
                 </div>
                 {/* 👇 Field Nama sekarang terhubung dengan state `name` 👇 */}
                 <input 
                   type="text" placeholder="Nama Lengkap" required
                   value={name} onChange={(e) => setName(e.target.value)}
                   className="w-full bg-black/50 border border-white/10 text-white rounded-2xl py-4 pl-12 pr-4 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder:text-gray-600"
                 />
               </div>
            )}

            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Mail className="text-gray-500 group-focus-within:text-purple-400 transition-colors" size={18} />
              </div>
              <input 
                type="email" placeholder="Alamat Email" required
                value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-black/50 border border-white/10 text-white rounded-2xl py-4 pl-12 pr-4 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder:text-gray-600"
              />
            </div>

            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                <Lock className="text-gray-500 group-focus-within:text-purple-400 transition-colors" size={18} />
              </div>
              <input 
                type="password" placeholder="Kata Sandi" required
                value={password} onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-black/50 border border-white/10 text-white rounded-2xl py-4 pl-12 pr-4 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all placeholder:text-gray-600"
              />
            </div>

            {/* 👇 Tombol disable saat loading agar pengguna tidak klik 2 kali 👇 */}
            <motion.button 
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              type="submit" disabled={loading}
              className="w-full bg-gradient-to-r from-purple-600 via-pink-500 to-blue-600 hover:from-purple-500 hover:via-pink-400 hover:to-blue-500 text-white font-black tracking-widest py-4 rounded-2xl flex items-center justify-center gap-3 transition-all shadow-[0_0_30px_rgba(147,51,234,0.4)] hover:shadow-[0_0_40px_rgba(147,51,234,0.6)] mt-6 disabled:opacity-50 disabled:cursor-not-allowed border border-white/20"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  MEMPROSES...
                </div>
              ) : (
                <>
                  {isLogin ? 'MASUK SEKARANG' : 'DAFTAR SEKARANG'}
                  <ArrowRight size={20} />
                </>
              )} 
            </motion.button>
          </form>

          <div className="mt-8 text-center">
            <p className="text-gray-400 text-sm">
              {isLogin ? "Belum punya akun?" : "Sudah punya akun?"}{" "}
              <button 
                type="button"
                onClick={() => setIsLogin(!isLogin)} 
                className="text-purple-400 hover:text-purple-300 font-bold tracking-wide transition-colors"
              >
                {isLogin ? 'Daftar di sini' : 'Masuk di sini'}
              </button>
            </p>
          </div>

        </div>
      </motion.div>
    </div>
  );
}