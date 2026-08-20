import os
import pandas as pd
import numpy as np
from PIL import Image
from loguru import logger
from sklearn.model_selection import train_test_split
from imblearn.over_sampling import SMOTE

# Tentukan lokasi folder untuk menyimpan gambar dataset hasil preprocessing
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, "Dataset_Seasonal")

# Kategori Musim (Seasonal Colors) untuk rekomendasi warna kulit
LABELS = ["Spring", "Summer", "Autumn", "Winter"]

def hex_to_rgb(hex_code):
    """
    Fungsi untuk mengubah kode warna HEX (misal: #FFFFFF) menjadi RGB (255, 255, 255).
    Diperlukan karena komputer (AI) memproses gambar dalam bentuk array RGB.
    """
    hex_code = str(hex_code).lstrip('#')
    # Kalau formatnya salah/kosong, kembalikan warna hitam
    if len(hex_code) != 6:
        return [0, 0, 0]
    return [int(hex_code[i:i+2], 16) for i in (0, 2, 4)]

def generate_solid_image(rgb, size=(100, 100)):
    """
    Fungsi untuk membuat gambar kotak (solid color) berdasarkan kode RGB.
    Gambar ini nanti yang akan dipelajari (di-training) oleh model CNN.
    """
    return Image.new("RGB", size, tuple(rgb))

def get_dummy_dataset():
    """
    Jika file 'seasonal_colors.csv' tidak ada, buat dataset dummy (palsu)
    agar program tetap jalan dan tidak error saat sidang/demo.
    """
    data = []
    
    # Warna-warna cerah/hangat (Spring)
    spring_colors = ["#FADBD8", "#F9E79F", "#A9DFBF", "#F5B041", "#EC7063"] * 10
    for c in spring_colors: data.append((c, "Spring"))
    
    # Warna-warna terang/dingin (Summer)
    summer_colors = ["#D2B4DE", "#AED6F1", "#A2D9CE", "#E8DAEF", "#85C1E9"] * 12
    for c in summer_colors: data.append((c, "Summer"))
    
    # Warna-warna gelap/hangat (Autumn)
    autumn_colors = ["#E67E22", "#D35400", "#A04000", "#B9770E", "#7E5109"] * 8
    for c in autumn_colors: data.append((c, "Autumn"))
    
    # Warna-warna gelap/dingin (Winter)
    winter_colors = ["#1F618D", "#154360", "#76448A", "#512E5F", "#17202A"] * 15
    for c in winter_colors: data.append((c, "Winter"))
    
    df = pd.DataFrame(data, columns=["hex_code", "label"])
    return df

def main():
    logger.info("Mulai Pra-Pemrosesan Seasonal Color Dataset...")
    
    csv_path = os.path.join(BASE_DIR, "seasonal_colors.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        logger.info(f"Dataset CSV ditemukan: {len(df)} baris.")
    else:
        logger.warning("File seasonal_colors.csv tidak ditemukan. Menggunakan dataset bawaan/dummy...")
        df = get_dummy_dataset()

    # Ubah data kolom HEX menjadi format Array RGB (X) dan ambil target Kelas (y)
    df['rgb'] = df['hex_code'].apply(hex_to_rgb)
    X = np.array(df['rgb'].tolist())
    y = df['label'].values

    logger.info("Distribusi kelas sebelum SMOTE:")
    unique, counts = np.unique(y, return_counts=True)
    for u, c in zip(unique, counts):
        logger.info(f" - {u}: {c}")

    # --- TEKNIK OVERSAMPLING (SMOTE) ---
    # Jika dataset jumlahnya tidak seimbang (imbalance), SMOTE akan menduplikasi 
    # data minoritas agar jumlahnya seimbang (menghindari model bias).
    logger.info("Menerapkan SMOTE Oversampling...")
    smote = SMOTE(random_state=42)
    X_resampled, y_resampled = smote.fit_resample(X, y)

    logger.info("Distribusi kelas SESUDAH SMOTE:")
    unique_resampled, counts_resampled = np.unique(y_resampled, return_counts=True)
    for u, c in zip(unique_resampled, counts_resampled):
        logger.info(f" - {u}: {c}")

    # Membagi dataset menjadi Data Latih (Train) 80% dan Data Uji (Validation) 20%
    X_train, X_valid, y_train, y_valid = train_test_split(X_resampled, y_resampled, test_size=0.2, random_state=42, stratify=y_resampled)

    logger.info("Menghasilkan gambar 100x100 piksel menggunakan Pillow (PIL)...")
    
    # Looping untuk memproses data train dan validasi sekaligus
    for split_name, X_data, y_data in [("train", X_train, y_train), ("valid", X_valid, y_valid)]:
        split_dir = os.path.join(DATASET_DIR, split_name)
        
        # Buat folder per kategori (Spring, Summer, Autumn, Winter)
        for label in LABELS:
            os.makedirs(os.path.join(split_dir, label), exist_ok=True)
            
        # Ubah array RGB jadi gambar dan simpan ke folder
        for i, (rgb, label) in enumerate(zip(X_data, y_data)):
            # Pastikan nilai RGB tidak kurang dari 0 atau lebih dari 255
            rgb_int = [int(max(0, min(255, val))) for val in rgb]
            img = generate_solid_image(rgb_int, size=(100, 100))
            
            save_path = os.path.join(split_dir, label, f"color_{i}.jpg")
            img.save(save_path)

    logger.info(f"[DONE] Pra-pemrosesan selesai! Dataset gambar tersimpan di: {DATASET_DIR}")

if __name__ == "__main__":
    main()
