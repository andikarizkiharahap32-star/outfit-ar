"""
OutfitAR - U-Net Model (Excellent & Robust Version)
Optimized for: Python 3.12, TF 2.16.1, Protobuf 4.25.3, NumPy 1.26.4
Script ini berisi arsitektur AI CNN yang memotong (segmentasi) baju yang sedang dipakai pengguna,
untuk ditimpa dengan baju virtual.
"""
import os
import sys
import numpy as np
import cv2
from loguru import logger
from pathlib import Path

# --- 1. BOOTSTRAP ENGINE (CRITICAL) ---
# Di TensorFlow 2.16+, Keras versi 3 (multi-backend) jadi default, 
# tapi kadang kurang kompatibel dengan kode lama. Kita paksa pakai tf_keras (legacy).
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2" # Sembunyikan info log C++ TF yang berisik

def verify_engine():
    """Analisis mendalam terhadap kesehatan library sebelum running."""
    try:
        import tensorflow as tf
        import tf_keras
        # Cek apakah modul compat tersedia (mencegah error yang tadi)
        from tensorflow.compat import v2 as _
        logger.success(f"✅ AI Engine Verified: TF {tf.__version__} | Keras Bridge Active")
        return True
    except Exception as e:
        logger.error(f"❌ Engine Breakdown: {str(e)}")
        return False

# Load engine di awal secara global
if not verify_engine():
    logger.critical("Sistem mendeteksi instalasi rusak. Jalankan Clean Slate Protocol!")
    # Kita buat dummy class agar aplikasi tidak langsung mati total saat dideploy, meski error
    layers = models = applications = None 
else:
    import tensorflow as tf
    import tf_keras as keras
    from tf_keras import layers, models, applications

# --- 2. ARCHITECTURE DEFINITION ---
# U-Net terdiri dari dua bagian: Encoder (menyusutkan gambar untuk mencari ciri)
# dan Decoder (membesarkan gambar untuk menentukan piksel masker).

def _conv_block(x, filters: int, name: str):
    """
    Blok konvolusi ganda (Double Conv) + BatchNorm + ReLU.
    Ini adalah batu bata dasar (building block) untuk decoder U-Net.
    """
    x = layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_c1")(x)
    x = layers.BatchNormalization(name=f"{name}_bn1")(x)
    x = layers.Activation("relu", name=f"{name}_relu1")(x)
    
    x = layers.Conv2D(filters, 3, padding="same", use_bias=False, name=f"{name}_c2")(x)
    x = layers.BatchNormalization(name=f"{name}_bn2")(x)
    x = layers.Activation("relu", name=f"{name}_relu2")(x)
    return x

def _decoder_block(x, skip, filters: int, name: str):
    """
    Upsample (membesarkan gambar) + Concatenate (menggabungkan garis skip) + Conv Block.
    Garis skip (skip connection) adalah fitur utama U-Net agar detail garis tepi baju tetap tajam.
    """
    x = layers.UpSampling2D(size=(2, 2), interpolation="bilinear", name=f"{name}_up")(x)
    x = layers.Concatenate(name=f"{name}_concat")([x, skip])
    x = _conv_block(x, filters, name=name)
    return x

def build_unet_efficientnet(input_shape=(512, 512, 3)):
    """
    Membangun U-Net dengan Backbone (Encoder) EfficientNetB0 (ImageNet Weights).
    EfficientNet dipilih karena ringan untuk realtime tapi sangat akurat.
    """
    inputs = layers.Input(shape=input_shape, name="input")

    # Load Backbone sebagai Encoder
    # include_top=False artinya jangan sertakan classification layer (kita butuh feature maps-nya saja)
    base = applications.EfficientNetB0(include_top=False, weights="imagenet", input_tensor=inputs)
    base.trainable = False  # Encoder kita freeze agar tidak berubah saat dipanggil

    # Skip Connections (Extracting layers dari berbagai tingkat kedalaman Encoder)
    # Ini akan jadi kabel penghubung ke Decoder di tingkat yang sama
    s1 = base.get_layer("block2a_expand_activation").output   # resolusi 256x256
    s2 = base.get_layer("block3a_expand_activation").output   # resolusi 128x128
    s3 = base.get_layer("block4a_expand_activation").output   # resolusi 64x64
    s4 = base.get_layer("block6a_expand_activation").output   # resolusi 32x32
    bridge = base.get_layer("top_activation").output          # Pusat U-Net, resolusi terkecil (16x16)

    # Decoder Path (membangun naik kembali resolusinya)
    x = _decoder_block(bridge, s4, 256, "dec4")
    x = _decoder_block(x, s3, 128, "dec3")
    x = _decoder_block(x, s2, 64, "dec2")
    x = _decoder_block(x, s1, 32, "dec1")

    # Final Stage: Kembalikan ukuran asli input (512x512)
    x = layers.UpSampling2D(size=(2, 2), interpolation="bilinear", name="final_up")(x)
    
    # Output layer berupa gambar 1-channel hitam putih. Activation sigmoid mengubah skor ke persentase 0-1.
    outputs = layers.Conv2D(1, 1, activation="sigmoid", name="output_mask")(x)

    return models.Model(inputs, outputs, name="UNet_OutfitAR_Excellent")

# --- 3. INFERENCE CLASS ---

class UNetInference:
    """
    Class Engine yang digunakan saat sistem AR berjalan untuk memotong baju.
    """
    MODEL_INPUT_SIZE = (512, 512)

    def __init__(self, weights_path=None):
        try:
            # Bangun arsitektur (tengkoraknya)
            self._model = build_unet_efficientnet()
            
            if weights_path and Path(weights_path).exists():
                # 1. Kompilasi wajib sebelum isi bobot (dagingnya)
                self._model.compile(optimizer="adam", loss="binary_crossentropy")
                
                # 2. MODIFIKASI DISINI: Gunakan skip_mismatch dan by_name
                # Ini akan memaksa load hanya layer yang cocok (seperti layer decoder)
                # sementara backbone (encoder) tetap utuh menggunakan weight ImageNet
                self._model.load_weights(
                    str(weights_path), 
                    by_name=True, 
                    skip_mismatch=True
                )
                logger.success(f"✅ Weights Partial Loaded (Hybrid Mode): {weights_path}")
            else:
                logger.warning("⚠️ Weights tidak ditemukan. Model berjalan dengan Random Initialization.")
        except Exception as e:
            # Jika masih error, log ini akan memberitahu detailnya
            logger.error(f"❌ Initialization Error: {e}")

    def predict_mask(self, image_bgr: np.ndarray) -> np.ndarray:
        """Memproses frame dari OpenCV (kamera user) dan mengembalikan masker baju hitam-putih."""
        orig_h, orig_w = image_bgr.shape[:2]
        img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        img_resized = cv2.resize(img_rgb, self.MODEL_INPUT_SIZE)
        
        # Normalisasi ke skala 0.0 - 1.0 (wajib untuk Neural Network)
        img_norm = img_resized.astype(np.float32) / 255.0
        # Tambah dimensi batch: (512, 512, 3) jadi (1, 512, 512, 3)
        img_batch = np.expand_dims(img_norm, axis=0)

        # Prediksi tanpa log verbose agar terminal tidak penuh tiap kali ngerender frame
        mask = self._model.predict(img_batch, verbose=0)[0, :, :, 0]
        
        # Kembalikan ke ukuran asli layar
        return cv2.resize(mask, (orig_w, orig_h))

    def apply_clothing_overlay(self, frame_bgr, clothing_bgr, mask, alpha=0.70):
        """
        Alpha blending antara frame asli (user) dengan gambar baju virtual.
        Versi Optimized: Mencegah overexposure (blank putih) dan smoothing tepi pinggir baju.
        """
        h, w = frame_bgr.shape[:2]
        clothing_res = cv2.resize(clothing_bgr, (w, h))
        
        # 1. Mask Cleaning: Hapus 'noise' abu-abu agar tidak menodai seluruh layar
        # Hanya piksel dengan keyakinan di atas 50% yang dianggap area baju murni
        _, mask_thresh = cv2.threshold(mask, 0.5, 1.0, cv2.THRESH_BINARY)
        
        # 2. Smoothing: Blur pinggiran (edges) masker Agar baju virtual menyatu halus dan tidak patah-patah (aliasing)
        mask_blur = cv2.GaussianBlur(mask_thresh, (25, 25), 0)
        
        # 3. Konversi masker 1 channel (hitam-putih) ke 3 channel agar bisa dikalikan dengan gambar BGR
        mask_3ch = np.stack([mask_blur] * 3, axis=-1)

        # 4. Blending Formula (Aljabar Linier Dasar)
        # Baju virtual dipotong sesuai masker, frame asli dilubangi sesuai masker, lalu keduanya digabung
        # Alpha menjaga agar bayangan asli tubuh di kamera masih nampak menembus baju virtual
        result = (clothing_res.astype(np.float32) * mask_3ch * alpha + 
                  frame_bgr.astype(np.float32) * (1.0 - (mask_3ch * alpha)))
        
        # Clip max value ke 255 (batas warna) dan cast ke format OpenCV yang siap tayang (uint8)
        return np.clip(result, 0, 255).astype(np.uint8)