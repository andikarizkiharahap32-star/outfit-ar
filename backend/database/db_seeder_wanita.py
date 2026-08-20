import os
import random
import uuid
import mysql.connector
from datetime import datetime

# Konfigurasi Database (Sesuai dengan Laragon default)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'outfit_ar'
}

# FIX 1: Dapatkan path absolut backend agar tidak error meski dijalankan dari dalam folder 'database'
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# FIX 2: Arahkan langsung ke folder 'wanitahijab' sesuai struktur folder di screenshot Anda
TARGET_DIR = os.path.join(BACKEND_DIR, 'uploads', 'products', 'wanitahijab')

def seed_database():
    print("🚀 Memulai Proses Injeksi Data ke Database MySQL...")
    
    if not os.path.exists(TARGET_DIR):
        print(f"❌ ERROR: Folder {TARGET_DIR} tidak ditemukan!")
        print("Pastikan nama foldernya benar sesuai yang ada di sebelah kiri VS Code.")
        return

    # Ambil semua file .jpg di dalam folder wanitahijab
    images = [f for f in os.listdir(TARGET_DIR) if f.endswith('.jpg') or f.endswith('.jpeg')]
    
    if not images:
        print(f"⚠️ Tidak ada gambar .jpg ditemukan di {TARGET_DIR}")
        return

    try:
        # Koneksi ke MySQL
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        success_count = 0
        
        for index, filename in enumerate(images):
            # 1. Generate Data Dummy yang Elegan
            # product_external_id harus UNIQUE sesuai schema.sql
            external_id = f"ZLR-HJB-{uuid.uuid4().hex[:8].upper()}"
            
            # Buat nama produk khusus hijab yang bervariasi
            tipe_baju = random.choice(["Gamis", "Tunik Hijab", "Blouse Lengan Panjang", "Abaya", "Kemeja Outer Hijab"])
            name = f"{tipe_baju} Premium #{index + 1}"
            
            brand = "Zalora Hijab"
            price = random.randint(150, 450) * 1000 # Harga acak 150rb - 450rb
            
            # Format image_url SESUAI folder baru
            image_url = f"products/wanitahijab/{filename}"
            
            gender = 'wanita'
            
            # 2. Query Insert ke tabel products
            sql = """
            INSERT INTO products 
            (product_external_id, name, brand, price, image_url, source_platform, gender, is_active) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            val = (external_id, name, brand, price, image_url, 'zalora', gender, 1)
            
            try:
                cursor.execute(sql, val)
                success_count += 1
                print(f"✅ Injeksi Berhasil: {name} -> {image_url}")
            except mysql.connector.IntegrityError:
                print(f"⚠️ Skip: {external_id} sudah ada di database.")
        
        # Commit perubahan ke database
        conn.commit()
        print("\n" + "="*50)
        print(f"🎉 SUKSES! {success_count} Produk Wanita Hijab berhasil dimasukkan ke Database!")
        print("="*50)

    except mysql.connector.Error as err:
        print(f"💥 Error Database: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    seed_database()