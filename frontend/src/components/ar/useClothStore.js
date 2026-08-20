// useClothStore.js
// Zustand store untuk manajemen state tekstur produk WebAR

import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'

export const useClothStore = create(
  subscribeWithSelector((set, get) => ({

    // ─── Katalog Produk ───────────────────────────────────────────────
    productCatalog: [],
    isLoadingCatalog: false,
    catalogError: null,

    // ─── Tekstur Terpilih ─────────────────────────────────────────────
    selectedTexture: null,
    selectedProductId: null,

    // ─── Pose / MediaPipe ─────────────────────────────────────────────
    poseLandmarks: null,
    poseReady: false,

    // ─── UI State ────────────────────────────────────────────────────
    activeCategory: 'all',
    searchQuery: '',
    isARActive: false,

    // ─── Actions ─────────────────────────────────────────────────────

    // Set catalog dari luar (diisi oleh ARTryOnPage dari rekomendasi)
    setProductCatalog: (catalog) => set({ productCatalog: catalog }),

    // Pilih produk dari katalog
    selectProduct: (productId) => {
      const product = get().productCatalog.find(p => p.id === productId || p.id === String(productId))
      if (!product) return
      set({
        selectedProductId: productId,
        selectedTexture: product.textureUrl || product.image_url || product.thumbnail_url || null,
      })
    },

    // Set tekstur langsung dari URL
    setTextureUrl: (url) => set({ selectedTexture: url, selectedProductId: null }),

    // Reset
    clearTexture: () => set({ selectedTexture: null, selectedProductId: null }),

    // Update pose dari MediaPipe setiap frame
    updatePose: (landmarks) => set({
      poseLandmarks: landmarks,
      poseReady: !!landmarks,
    }),

    setActiveCategory: (cat) => set({ activeCategory: cat }),
    setSearchQuery: (q) => set({ searchQuery: q }),
    setARActive: (val) => set({ isARActive: val }),
  }))
)

export const selectFilteredProducts = (state) => {
  const { productCatalog, activeCategory, searchQuery } = state
  return productCatalog.filter(p => {
    const matchCat = activeCategory === 'all' || (p.category || '').toLowerCase() === activeCategory
    const matchQ   = (p.name || '').toLowerCase().includes(searchQuery.toLowerCase())
    return matchCat && matchQ
  })
}
