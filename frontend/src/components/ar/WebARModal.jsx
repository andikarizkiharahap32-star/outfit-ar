// WebARModal.jsx
// Panel AR Full-Screen dengan MediaPipe Pose + Three.js rigged cloth
// Muncul sebagai modal overlay dari halaman ARTryOnPage

import { useEffect, useRef, useCallback, Suspense, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { Environment, ContactShadows } from '@react-three/drei'
import { motion, AnimatePresence } from 'framer-motion'
import { X, Activity, Camera, RotateCcw } from 'lucide-react'
import ClothModel from './ClothModel'
import { useClothStore } from './useClothStore'

// ─── Konfigurasi MediaPipe Pose ───────────────────────────────────────────────
const POSE_CONFIG = {
  modelComplexity: 1,
  smoothLandmarks: true,
  enableSegmentation: false,
  minDetectionConfidence: 0.6,
  minTrackingConfidence: 0.5,
}

// ─── Komponen Scene Three.js ───────────────────────────────────────────────────
function ARScene({ modelPath }) {
  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[2, 4, 3]} intensity={1.2} castShadow />
      <directionalLight position={[-2, 2, -1]} intensity={0.3} />
      <Environment preset="city" />
      <Suspense fallback={null}>
        <ClothModel
          modelPath={modelPath}
          scale={1.0}
          position={[0, -1.2, 0]}
        />
      </Suspense>
      <ContactShadows
        position={[0, -1.8, 0]}
        opacity={0.25}
        scale={3}
        blur={2}
      />
    </>
  )
}

// ─── HUD Status Pose ──────────────────────────────────────────────────────────
function PoseStatusHUD() {
  const poseReady = useClothStore(s => s.poseReady)
  return (
    <div style={{
      position: 'absolute',
      top: 16,
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 20,
      background: 'rgba(0,0,0,0.55)',
      color: '#fff',
      fontSize: 11,
      padding: '5px 14px',
      borderRadius: 20,
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      backdropFilter: 'blur(8px)',
      border: '1px solid rgba(255,255,255,0.1)',
      pointerEvents: 'none',
    }}>
      <Activity size={12} style={{ color: poseReady ? '#4ade80' : '#f87171' }} />
      <span style={{ opacity: 0.85 }}>{poseReady ? 'Pose Terdeteksi' : 'Menunggu Pose…'}</span>
      <span style={{
        width: 7, height: 7, borderRadius: '50%',
        background: poseReady ? '#4ade80' : '#f87171',
        display: 'inline-block',
        boxShadow: poseReady ? '0 0 6px #4ade80' : '0 0 6px #f87171',
      }} />
    </div>
  )
}

// ─── Komponen Utama Modal ─────────────────────────────────────────────────────
export default function WebARModal({ isOpen, onClose, productImageUrl, productName, modelPath }) {
  const finalModelPath = modelPath || '/models/baju_rigged.glb';
  const videoRef  = useRef(null)
  const poseRef   = useRef(null)
  const cameraRef = useRef(null)
  const [cameraError, setCameraError] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const updatePose  = useClothStore(s => s.updatePose)
  const setARActive = useClothStore(s => s.setARActive)
  const setTextureUrl = useClothStore(s => s.setTextureUrl)

  // Pasang gambar produk sebagai tekstur saat modal dibuka
  useEffect(() => {
    if (isOpen && productImageUrl) {
      setTextureUrl(productImageUrl)
    }
  }, [isOpen, productImageUrl, setTextureUrl])

  // ── Inisialisasi MediaPipe Pose ─────────────────────────────────────
  const initPose = useCallback(async () => {
    try {
      // Dynamic import agar tidak membebani bundle utama
      const { Pose } = await import('@mediapipe/pose')

      const pose = new Pose({
        locateFile: (file) =>
          `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
      })

      pose.setOptions(POSE_CONFIG)

      pose.onResults((results) => {
        updatePose(results.poseLandmarks ?? null)
      })

      poseRef.current = pose
      return pose
    } catch (err) {
      console.warn('[AR] MediaPipe Pose gagal dimuat:', err.message)
      return null
    }
  }, [updatePose])

  // ── Inisialisasi kamera ────────────────────────────────────────────
  const initCamera = useCallback(async (pose) => {
    if (!videoRef.current || !pose) return

    try {
      const { Camera } = await import('@mediapipe/camera_utils')

      const cam = new Camera(videoRef.current, {
        onFrame: async () => {
          if (pose && videoRef.current) {
            await pose.send({ image: videoRef.current })
          }
        },
        width: 1280,
        height: 720,
        facingMode: 'user',
      })

      await cam.start()
      cameraRef.current = cam
      setARActive(true)
      setIsLoading(false)
    } catch (err) {
      console.warn('[AR] Kamera tidak tersedia:', err.message)
      setCameraError(true)
      setIsLoading(false)
    }
  }, [setARActive])

  // ── Lifecycle: buka/tutup modal ────────────────────────────────────
  useEffect(() => {
    if (!isOpen) return

    setIsLoading(true)
    setCameraError(false)

    let mounted = true

    const start = async () => {
      const pose = await initPose()
      if (mounted) await initCamera(pose)
    }

    start()

    return () => {
      mounted = false
      cameraRef.current?.stop?.()
      poseRef.current?.close?.()
      setARActive(false)
      updatePose(null)
    }
  }, [isOpen, initPose, initCamera, setARActive, updatePose])

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          style={{
            position: 'fixed',
            inset: 0,
            zIndex: 1000,
            background: '#000',
            overflow: 'hidden',
          }}
        >
          {/* Layer 1: Feed kamera (background AR) */}
          <video
            ref={videoRef}
            autoPlay
            playsInline
            muted
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: 'scaleX(-1)',
              zIndex: 0,
            }}
          />

          {/* Loading overlay */}
          {isLoading && (
            <div style={{
              position: 'absolute', inset: 0, zIndex: 30,
              background: 'rgba(0,0,0,0.85)',
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', gap: 16,
            }}>
              <div style={{
                width: 48, height: 48,
                border: '3px solid rgba(255,255,255,0.1)',
                borderTopColor: '#7c3aed',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
              }} />
              <p style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12, letterSpacing: 4, textTransform: 'uppercase' }}>
                Memuat AR…
              </p>
            </div>
          )}

          {/* Error kamera */}
          {cameraError && !isLoading && (
            <div style={{
              position: 'absolute', inset: 0, zIndex: 15,
              background: 'linear-gradient(to bottom, #0a0a0f, #050508)',
              display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', gap: 12,
              color: '#fff',
            }}>
              <Camera size={48} style={{ opacity: 0.3 }} />
              <p style={{ fontSize: 14, fontWeight: 'bold', opacity: 0.7 }}>Kamera tidak tersedia</p>
              <p style={{ fontSize: 11, opacity: 0.4, textAlign: 'center', maxWidth: 200 }}>
                Model 3D ditampilkan dalam mode preview tanpa kamera
              </p>
            </div>
          )}

          {/* Layer 2: Canvas Three.js (transparan di atas video) */}
          <Canvas
            style={{
              position: 'absolute',
              inset: 0,
              zIndex: 1,
            }}
            camera={{ position: [0, 0, 3], fov: 50 }}
            gl={{
              alpha: true,
              antialias: true,
              preserveDrawingBuffer: false,
            }}
            onCreated={({ gl }) => {
              gl.setClearColor(0x000000, 0)
            }}
          >
            <ARScene modelPath={finalModelPath} />
          </Canvas>

          {/* Layer 3: HUD status pose */}
          {!isLoading && <PoseStatusHUD />}

          {/* Layer 4: Tombol Tutup + Info Produk */}
          <div style={{
            position: 'absolute',
            top: 0, left: 0, right: 0,
            zIndex: 20,
            padding: '16px 20px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
          }}>
            {/* Info Produk */}
            {productName && (
              <div style={{
                background: 'rgba(0,0,0,0.6)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 12,
                padding: '8px 14px',
                maxWidth: 200,
              }}>
                <p style={{ color: 'rgba(255,255,255,0.5)', fontSize: 9, textTransform: 'uppercase', letterSpacing: 2, marginBottom: 2 }}>
                  Sedang dicoba
                </p>
                <p style={{ color: '#fff', fontSize: 12, fontWeight: 'bold', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {productName}
                </p>
              </div>
            )}

            {/* Tombol Tutup */}
            <motion.button
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              onClick={onClose}
              style={{
                marginLeft: 'auto',
                background: 'rgba(0,0,0,0.6)',
                backdropFilter: 'blur(8px)',
                border: '1px solid rgba(255,255,255,0.15)',
                borderRadius: '50%',
                width: 44, height: 44,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: '#fff',
                cursor: 'pointer',
              }}
            >
              <X size={20} />
            </motion.button>
          </div>

          {/* Label AR di pojok bawah */}
          <div style={{
            position: 'absolute',
            bottom: 24, left: '50%',
            transform: 'translateX(-50%)',
            zIndex: 20,
            background: 'rgba(124,58,237,0.25)',
            backdropFilter: 'blur(8px)',
            border: '1px solid rgba(124,58,237,0.4)',
            borderRadius: 20,
            padding: '6px 16px',
            color: '#c4b5fd',
            fontSize: 10,
            fontWeight: 'bold',
            letterSpacing: 3,
            textTransform: 'uppercase',
            pointerEvents: 'none',
          }}>
            ✦ AR TRY-ON AKTIF ✦
          </div>

          {/* CSS Keyframes untuk spinner */}
          <style>{`
            @keyframes spin { to { transform: rotate(360deg); } }
          `}</style>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
