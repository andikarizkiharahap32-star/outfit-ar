import { create } from 'zustand'
import { persist } from 'zustand/middleware'

const generateSafeId = () => {
  return 'sess-' + Math.random().toString(36).substring(2, 15) + Date.now().toString(36);
};

const useStore = create(
  persist(
    (set) => ({
      user: null,
      token: null,
      skinTone: null, 
      recommendations: null,
      gender: 'pria', 
      sessionId: generateSafeId(),
      activeProductId: null,

      setAuth: (user, token) => set({ user, token }),
      setSkinTone: (data) => set({ skinTone: data }),
      setRecommendations: (data) => set({ recommendations: data }),
      setGender: (g) => set({ gender: g }),
      setActiveProduct: (id) => set({ activeProductId: id }),
      clearAuth: () => set({ user: null, token: null }),
    }),
    {
      name: 'outfit-ar-store',
      // Hanya simpan data yang benar-benar perlu di memori browser
      partialize: (state) => ({
        skinTone: state.skinTone,
        gender: state.gender,
        sessionId: state.sessionId,
      }),
    }
  )
)

export default useStore