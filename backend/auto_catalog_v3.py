import os
import cv2
import numpy as np
import mysql.connector
from sklearn.cluster import KMeans
import uuid

# --- KONFIGURASI ---
# Setting database Laragon default
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'outfit_ar'),
}

def get_dominant_color(image_path):
    """
    Fungsi untuk mengekstrak warna dominan baju dari gambar dataset.
    Menggunakan algoritma K-Means Clustering dari Scikit-Learn.
    """
    try:
        image = cv2.imread(image_path)
        if image is None: return "#808080" # Default abu-abu kalau gagal baca gambar
        
        # Konversi BGR (OpenCV) ke RGB (Standar Web)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize jadi kecil (50x50) agar proses K-Means sangat cepat
        image = cv2.resize(image, (50, 50))
        
        # Ubah gambar 2D jadi array 1D berisi daftar piksel RGB
        pixels = image.reshape((-1, 3))
        
        # Cari 3 warna paling dominan (clusters)
        clt = KMeans(n_clusters=3, n_init=10)
        clt.fit(pixels)
        
        centers = clt.cluster_centers_
        counts = np.bincount(clt.labels_)
        
        # Urutkan warna dari yang paling banyak muncul
        for i in np.argsort(counts)[::-1]:
            color = centers[i].astype(int)
            # Filter: abaikan warna yang terlalu putih (biasanya itu background/latar studio)
            if not np.all(color > 240): 
                # Kembalikan dalam format kode HEX warna (misal: #FF5733)
                return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"
                
        return "#808080"
    except:
        return "#808080"

def setup_and_run():
    """
    Fungsi utama untuk membaca semua gambar di folder uploads/products
    dan memasukkannya secara otomatis ke database MySQL.
    """
    try:
        # 1. Cek Koneksi ke Database
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        print("[INFO] Koneksi Database Berhasil!")

        # 2. Pastikan Tabel Ada (Emergency Fix kalau tabel kehapus)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INT AUTO_INCREMENT PRIMARY KEY,
                product_external_id VARCHAR(50) UNIQUE,
                name VARCHAR(255),
                brand VARCHAR(100) DEFAULT 'Zalora Collection',
                color VARCHAR(20),
                gender ENUM('pria', 'wanita', 'unisex'),
                image_url TEXT,
                source_platform VARCHAR(50) DEFAULT 'zalora'
            )
        """)
        print("[INFO] Struktur Tabel Dipastikan Aman.")

        # Folder tempat menyimpan hasil download scraper
        base_path = os.path.join('uploads', 'products')
        if not os.path.exists(base_path):
            print(f"[ERROR] Folder tidak ditemukan: {base_path}")
            return

        print("[START] Mulai Memasukkan Data...")
        
        count = 0
        # os.walk akan menelusuri semua sub-folder di dalam uploads/products
        for root, dirs, files in os.walk(base_path):
            for file in files:
                # Hanya proses file gambar
                if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                    file_path = os.path.join(root, file)
                    
                    # Logika Gender: Tebak dari nama file (kalau ada kata "women")
                    gender = "wanita" if "women" in file.lower() else "pria"
                    
                    # Deteksi Warna dominan baju pakai fungsi K-Means di atas
                    hex_color = get_dominant_color(file_path)
                    
                    # Path ramah URL (ubah backslash Windows jadi slash standar URL)
                    web_path = file_path.replace('\\', '/')
                    
                    # Query INSERT dengan fitur ON DUPLICATE KEY (kalau ID udah ada, update aja warnanya, jangan error)
                    sql = """INSERT INTO products (product_external_id, name, color, image_url, gender) 
                             VALUES (%s, %s, %s, %s, %s) 
                             ON DUPLICATE KEY UPDATE color=%s, gender=%s"""
                    
                    prod_id = str(uuid.uuid4())[:8] # Generate ID acak 8 karakter
                    prod_name = f"Atasan {gender.capitalize()} Zalora"
                    
                    # Eksekusi query
                    cursor.execute(sql, (prod_id, prod_name, hex_color, web_path, gender, hex_color, gender))
                    count += 1
                    
                    if count % 10 == 0:
                        print(f"[PROCESS] Terproses: {count} gambar...")

        # Simpan semua perubahan ke database MySQL
        conn.commit()
        print(f"\n[DONE] SELESAI! {count} data masuk ke database.")
        
    except mysql.connector.Error as err:
        print(f"[ERROR] Error Database: {err}")
    finally:
        # Tutup koneksi agar tidak memory leak
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    setup_and_run()