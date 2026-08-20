import { motion } from 'framer-motion'
import { CheckCircle2, XCircle, Zap } from 'lucide-react'

const SKIN_TONE_COLORS = {
  1: '#f5c8a0', 2: '#e8b48a', 3: '#c8956c', 4: '#9c6640', 5: '#6b3f20',
}

const LEVEL_LABELS = {
  1: 'Sangat Terang', 2: 'Terang', 3: 'Sedang', 4: 'Gelap', 5: 'Sangat Gelap',
}

export default function SkinToneResult({ detection }) {
  const {
    skin_tone_level, skin_tone_label, skin_tone_hex,
    confidence, recommended_colors, avoid_colors,
  } = detection

  const skinColor = SKIN_TONE_COLORS[skin_tone_level] || skin_tone_hex

  return (
    <motion.div
      className="glass space-y-6 p-6"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
    >
      {/* Header */}
      <div className="flex items-center gap-4">
        <div
          className="w-16 h-16 rounded-2xl border-4 border-[var(--glass-border)] shadow-lg flex-shrink-0"
          style={{ background: skinColor }}
        />
        <div>
          <p className="text-xs text-[var(--text-muted)] uppercase tracking-wider mb-1">Skin Tone Terdeteksi</p>
          <h2 className="font-display text-2xl">{skin_tone_label}</h2>
          <div className="flex items-center gap-3 mt-1">
            <span className="score-badge">
              <Zap size={10} />
              Level {skin_tone_level}/5
            </span>
            <span className="text-xs text-[var(--text-muted)]">
              Akurasi: {(confidence * 100).toFixed(1)}%
            </span>
          </div>
        </div>
      </div>

      {/* Confidence bar */}
      <div>
        <div className="flex justify-between text-xs text-[var(--text-muted)] mb-2">
          <span>Confidence Score</span>
          <span>{(confidence * 100).toFixed(1)}%</span>
        </div>
        <div className="h-2 rounded-full bg-[var(--dark-700)] overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-brand-600 to-brand-400"
            initial={{ width: 0 }}
            animate={{ width: `${confidence * 100}%` }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          />
        </div>
      </div>

      {/* Level scale */}
      <div>
        <p className="text-xs text-[var(--text-muted)] mb-3">Skala Skin Tone</p>
        <div className="flex gap-2">
          {Object.entries(SKIN_TONE_COLORS).map(([level, color]) => (
            <div key={level} className="flex-1 text-center">
              <div
                className={`h-8 rounded-lg transition-all ${
                  parseInt(level) === skin_tone_level
                    ? 'ring-2 ring-brand-500 ring-offset-2 ring-offset-[var(--dark-800)] scale-110'
                    : 'opacity-60'
                }`}
                style={{ background: color }}
              />
              <span className="text-[10px] text-[var(--text-muted)] mt-1 block">L{level}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Recommended colors */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 size={14} className="text-emerald-400" />
            <p className="text-xs font-medium text-emerald-400">Warna Direkomendasikan</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {recommended_colors?.map((hex) => (
              <div
                key={hex}
                className="w-8 h-8 rounded-lg border border-[var(--glass-border)] cursor-pointer hover:scale-110 transition-transform"
                style={{ background: hex }}
                title={hex}
              />
            ))}
          </div>
        </div>
        <div>
          <div className="flex items-center gap-2 mb-3">
            <XCircle size={14} className="text-red-400" />
            <p className="text-xs font-medium text-red-400">Warna Dihindari</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {avoid_colors?.map((hex) => (
              <div
                key={hex}
                className="w-8 h-8 rounded-lg border border-red-900 opacity-60 cursor-pointer relative"
                style={{ background: hex }}
                title={hex}
              >
                <div className="absolute inset-0 flex items-center justify-center text-red-500 text-lg font-bold">×</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Hex badge */}
      <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--dark-700)]">
        <span className="text-xs text-[var(--text-muted)]">Warna Kulit Terdeteksi</span>
        <div className="flex items-center gap-2">
          <div className="w-5 h-5 rounded" style={{ background: skin_tone_hex }} />
          <code className="text-xs font-mono text-[var(--text-primary)]">{skin_tone_hex}</code>
        </div>
      </div>
    </motion.div>
  )
}
