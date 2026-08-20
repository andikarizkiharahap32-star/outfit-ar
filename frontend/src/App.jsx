// Import React dan komponen routing dari react-router-dom
import React from 'react'; 
import { Routes, Route, Navigate } from 'react-router-dom';

// Layout adalah wrapper global — semua halaman utama dibungkus di sini
import Layout from './components/layout/Layout';

// Import semua halaman yang akan dipakai di routing
import HomePage from './pages/HomePage';
import SkinTonePage from './pages/SkinTonePage';
import RecommendationPage from './pages/RecommendationPage';
import ARTryOnPage from './pages/ARTryOnPage';
import ProductsPage from './pages/ProductsPage';
import StreamHP from './pages/StreamHP'; 
import MixMatchPage from './pages/MixMatchPage';
import LoginPage from './pages/LoginPage'; 

export default function App() {
  return (
    // Wrapper utama — min-h-screen biar konten selalu full tinggi layar
    <div className="min-h-screen bg-surface text-white font-body selection:bg-brand-500/30">
      <Routes>
        {/* Semua route di dalam Layout pakai navbar/footer yang sama */}
        <Route element={<Layout />}>
          <Route path="/" element={<HomePage />} />
          <Route path="/skin-tone" element={<SkinTonePage />} />
          <Route path="/recommendations" element={<RecommendationPage />} />
          {/* Route AR pakai productId dari URL params, langsung ke StreamHP */}
          <Route path="/ar/:productId"  element={<StreamHP />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/mix-match" element={<MixMatchPage />} />
        </Route>

        {/* Route stream khusus HP — di luar Layout karena UI-nya beda sendiri */}
        <Route path="/stream-hp/:sessionId" element={<StreamHP />} />
        
        {/* Halaman login juga di luar Layout */}
        <Route path="/login" element={<LoginPage />} />
        
        {/* Fallback: kalau URL tidak dikenal, redirect ke Home */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}