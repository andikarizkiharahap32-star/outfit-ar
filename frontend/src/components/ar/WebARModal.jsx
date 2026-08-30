// WebARModal.jsx
// AR Full-Screen dengan MediaPipe Pose + Canvas 2D product image overlay
// Tidak pakai Three.js GLB loader (produk tidak punya file .glb)
// Sesuai AGENTS.md: position-based tracking untuk unrigged models

import { useEffect, useRef, useCallback, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { X, Camera } from "lucide-react"

// Konstanta MediaPipe Pose landmarks
const MP_LEFT_SHOULDER  = 11
const MP_RIGHT_SHOULDER = 12
const MP_LEFT_HIP       = 23
const MP_RIGHT_HIP      = 24

const POSE_CONFIG = {
  modelComplexity: 0,
  smoothLandmarks: true,
  enableSegmentation: false,
  minDetectionConfidence: 0.5,
  minTrackingConfidence: 0.5,
}

export default function WebARModal({ isOpen, onClose, productImageUrl, productName }) {
  const videoRef     = useRef(null)
  const canvasRef    = useRef(null)
  const poseRef      = useRef(null)
  const streamRef    = useRef(null)
  const landmarksRef = useRef(null)
  const animFrameRef = useRef(null)
  const productImgRef = useRef(null)
  const prevScaleRef  = useRef(null)
  const prevRotRef    = useRef(null)

  const [cameraError, setCameraError] = useState(false)
  const [isLoading, setIsLoading]     = useState(true)
  const [poseReady, setPoseReady]     = useState(false)

  useEffect(() => {
    if (!productImageUrl) return
    const img = new Image()
    img.crossOrigin = "anonymous"
    img.src = productImageUrl
    productImgRef.current = img
  }, [productImageUrl])

  const drawLoop = useCallback(() => {
    const canvas = canvasRef.current
    const img    = productImgRef.current
    if (!canvas) { animFrameRef.current = requestAnimationFrame(drawLoop); return }

    const ctx = canvas.getContext("2d")
    const W = canvas.width
    const H = canvas.height
    ctx.clearRect(0, 0, W, H)

    const lms = landmarksRef.current

    if (img && img.complete && img.naturalWidth > 0 && lms && lms.length >= 25) {
      const lSh  = lms[MP_LEFT_SHOULDER]
      const rSh  = lms[MP_RIGHT_SHOULDER]
      const lHip = lms[MP_LEFT_HIP]
      const rHip = lms[MP_RIGHT_HIP]

      const lShX = lSh.x * W
      const rShX = rSh.x * W
      const lShY = lSh.y * H
      const rShY = rSh.y * H

      const shoulderDist = Math.abs(lShX - rShX)

      // Sideways Freeze (AGENTS.md rule)
      if (shoulderDist >= 0.12 * W) {
        const midShX = (lShX + rShX) / 2
        const midShY = (lShY + rShY) / 2

        const imgW = shoulderDist * 2.2
        const imgH = imgW * (img.naturalHeight / img.naturalWidth)

        // Shoulder rotation - clamp -0.35 s/d 0.35 rad (AGENTS.md rule)
        let angle = Math.atan2(rShY - lShY, rShX - lShX)
        angle = Math.max(-0.35, Math.min(0.35, angle))

        prevScaleRef.current = imgW
        prevRotRef.current   = angle

        ctx.save()
        ctx.translate(midShX, midShY)
        ctx.rotate(angle)
        ctx.globalAlpha = 0.88
        ctx.drawImage(img, -imgW / 2, -imgH * 0.1, imgW, imgH)
        ctx.restore()
        setPoseReady(true)
      } else if (prevScaleRef.current) {
        // Freeze di nilai sebelumnya
        const imgW = prevScaleRef.current
        const imgH = imgW * (img.naturalHeight / img.naturalWidth)
        const midShX = (lShX + rShX) / 2
        const midShY = (lShY + rShY) / 2
        ctx.save()
        ctx.translate(midShX, midShY)
        ctx.rotate(prevRotRef.current || 0)
        ctx.globalAlpha = 0.88
        ctx.drawImage(img, -imgW / 2, -imgH * 0.1, imgW, imgH)
        ctx.restore()
      }
    } else if (img && img.complete && img.naturalWidth > 0) {
      const fw = Math.min(W * 0.6, 300)
      const fh = fw * (img.naturalHeight / img.naturalWidth)
      ctx.globalAlpha = 0.5
      ctx.drawImage(img, (W - fw) / 2, H * 0.15, fw, fh)
    }

    animFrameRef.current = requestAnimationFrame(drawLoop)
  }, [])

  const initPose = useCallback(async () => {
    try {
      const { Pose } = await import("@mediapipe/pose")
      const pose = new Pose({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`
      })
      pose.setOptions(POSE_CONFIG)
      pose.onResults((results) => {
        landmarksRef.current = results.poseLandmarks ?? null
      })
      poseRef.current = pose
      return pose
    } catch (err) {
      console.warn("[AR] MediaPipe Pose gagal:", err.message)
      return null
    }
  }, [])

  const initCamera = useCallback(async (pose) => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } }
      })
      const video = videoRef.current
      if (!video) { stream.getTracks().forEach(t => t.stop()); return }
      video.srcObject = stream
      streamRef.current = stream
      video.onloadedmetadata = () => {
        video.play()
        const c = canvasRef.current
        if (c) { c.width = video.videoWidth; c.height = video.videoHeight }
        setIsLoading(false)
        animFrameRef.current = requestAnimationFrame(drawLoop)
      }
      if (pose) {
        const sendFrame = async () => {
          if (!streamRef.current) return
          if (video && video.readyState >= 2) {
            try { await pose.send({ image: video }) } catch (_) {}
          }
          setTimeout(sendFrame, 33)
        }
        setTimeout(sendFrame, 800)
      }
    } catch (err) {
      console.warn("[AR] Kamera tidak tersedia:", err.message)
      setCameraError(true)
      setIsLoading(false)
      animFrameRef.current = requestAnimationFrame(drawLoop)
    }
  }, [drawLoop])

  useEffect(() => {
    if (!isOpen) return
    setIsLoading(true)
    setCameraError(false)
    setPoseReady(false)
    landmarksRef.current  = null
    prevScaleRef.current  = null
    prevRotRef.current    = null

    let mounted = true
    const start = async () => {
      const pose = await initPose()
      if (mounted) await initCamera(pose)
    }
    start()

    return () => {
      mounted = false
      cancelAnimationFrame(animFrameRef.current)
      streamRef.current?.getTracks?.().forEach(t => t.stop())
      streamRef.current = null
      poseRef.current?.close?.()
      poseRef.current = null
    }
  }, [isOpen, initPose, initCamera])

  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
          style={{ position: "fixed", inset: 0, zIndex: 1000, background: "#000", overflow: "hidden" }}
        >
          {/* Layer 1: Video feed */}
          <video
            ref={videoRef} autoPlay playsInline muted
            style={{
              position: "absolute", inset: 0, width: "100%", height: "100%",
              objectFit: "cover", transform: "scaleX(-1)", zIndex: 0,
            }}
          />

          {/* Layer 2: Canvas overlay baju (juga di-mirror agar sinkron dengan video) */}
          <canvas
            ref={canvasRef}
            style={{
              position: "absolute", inset: 0, width: "100%", height: "100%",
              transform: "scaleX(-1)", zIndex: 1, pointerEvents: "none",
            }}
          />

          {/* Loading */}
          {isLoading && (
            <div style={{
              position: "absolute", inset: 0, zIndex: 30,
              background: "rgba(0,0,0,0.85)",
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", gap: 16,
            }}>
              <div style={{
                width: 48, height: 48,
                border: "3px solid rgba(255,255,255,0.1)",
                borderTopColor: "#7c3aed", borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }} />
              <p style={{ color: "rgba(255,255,255,0.6)", fontSize: 12, letterSpacing: 4, textTransform: "uppercase" }}>
                Memuat AR...
              </p>
            </div>
          )}

          {/* Camera error */}
          {cameraError && !isLoading && (
            <div style={{
              position: "absolute", inset: 0, zIndex: 2,
              background: "linear-gradient(to bottom, #0a0a0f, #050508)",
              display: "flex", flexDirection: "column",
              alignItems: "center", justifyContent: "center", gap: 12, color: "#fff",
            }}>
              <Camera size={48} style={{ opacity: 0.3 }} />
              <p style={{ fontSize: 14, fontWeight: "bold", opacity: 0.7 }}>Kamera tidak tersedia</p>
              <p style={{ fontSize: 11, opacity: 0.4, textAlign: "center", maxWidth: 200 }}>
                Preview produk ditampilkan tanpa kamera
              </p>
            </div>
          )}

          {/* HUD Pose status */}
          {!isLoading && (
            <div style={{
              position: "absolute", top: 16, left: "50%", transform: "translateX(-50%)",
              zIndex: 20, background: "rgba(0,0,0,0.55)", color: "#fff", fontSize: 11,
              padding: "5px 14px", borderRadius: 20,
              display: "flex", alignItems: "center", gap: 6,
              backdropFilter: "blur(8px)", border: "1px solid rgba(255,255,255,0.1)",
              pointerEvents: "none",
            }}>
              <span style={{ opacity: 0.85 }}>
                {poseReady ? "Pose Terdeteksi" : "Arahkan badan ke kamera..."}
              </span>
              <span style={{
                width: 7, height: 7, borderRadius: "50%",
                background: poseReady ? "#4ade80" : "#f87171",
                display: "inline-block",
                boxShadow: poseReady ? "0 0 6px #4ade80" : "0 0 6px #f87171",
              }} />
            </div>
          )}

          {/* Header */}
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0,
            zIndex: 20, padding: "16px 20px",
            display: "flex", justifyContent: "space-between", alignItems: "flex-start",
          }}>
            {productName && (
              <div style={{
                background: "rgba(0,0,0,0.6)", backdropFilter: "blur(8px)",
                border: "1px solid rgba(255,255,255,0.1)",
                borderRadius: 12, padding: "8px 14px", maxWidth: 200,
              }}>
                <p style={{ color: "rgba(255,255,255,0.5)", fontSize: 9, textTransform: "uppercase", letterSpacing: 2, marginBottom: 2 }}>
                  Sedang dicoba
                </p>
                <p style={{ color: "#fff", fontSize: 12, fontWeight: "bold", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {productName}
                </p>
              </div>
            )}
            <motion.button
              whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.9 }}
              onClick={onClose}
              style={{
                marginLeft: "auto", background: "rgba(0,0,0,0.6)", backdropFilter: "blur(8px)",
                border: "1px solid rgba(255,255,255,0.15)",
                borderRadius: "50%", width: 44, height: 44,
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#fff", cursor: "pointer",
              }}
            >
              <X size={20} />
            </motion.button>
          </div>

          {/* Label AR */}
          <div style={{
            position: "absolute", bottom: 24, left: "50%", transform: "translateX(-50%)",
            zIndex: 20, background: "rgba(124,58,237,0.25)", backdropFilter: "blur(8px)",
            border: "1px solid rgba(124,58,237,0.4)", borderRadius: 20, padding: "6px 16px",
            color: "#c4b5fd", fontSize: 10, fontWeight: "bold", letterSpacing: 3,
            textTransform: "uppercase", pointerEvents: "none",
          }}>
            AR TRY-ON AKTIF
          </div>

          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
