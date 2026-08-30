import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

print("--- SEDANG MENGECEK MEDIAPIPE VERSI BARU ---")

try:
    # Mencoba akses modul deteksi badan (Pose) gaya baru
    base_options = python.BaseOptions(model_asset_path='pose_landmarker.task')
    options = vision.PoseLandmarkerOptions(base_options=base_options)
    print("[OK] BERHASIL: MediaPipe Tasks terdeteksi!")
except Exception as e:
    print(f"[ERROR] ERROR: {e}")

try:
    # Cek apakah solusi lama masih bisa dipanggil (Legacy)
    import mediapipe.solutions.pose as mp_pose
    print("[OK] BERHASIL: Solusi Legacy (solutions.pose) juga aktif!")
except Exception as e:
    print(f"[INFO] INFO: Solusi legacy tidak ditemukan, tapi ini normal di versi baru.")

print("------------------------------------------")