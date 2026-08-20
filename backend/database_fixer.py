# -*- coding: utf-8 -*-
import os
import random
import uuid
import mysql.connector

# Konfigurasi Database (Sesuai dengan Laragon default)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'outfit_ar'
}

# --- SMART PATH FINDER (Pelacak Folder Otomatis) ---
# Mencari letak folder 'uploads' secara dinamis (fleksibel dijalankan dari mana saja)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

def get_target_dir(folder_name):
    # Percobaan 1: Mencari di dalam folder backend (outfit-ar/backend/uploads/products/...)
    target = os.path.join(CURRENT_DIR, 'uploads', 'products', folder_name)
    if not os.path.exists(target):
        # Percobaan 2: Jika tidak ada, cari di luar folder backend (outfit-ar/uploads/products/...)
        # Ini berguna kalau script dijalankan dari root project
        target = os.path.join(os.path.dirname(CURRENT_DIR), 'uploads', 'products', folder_name)
    return target

def fix_and_seed_database():
    """
    Script sapu bersih database dan injeksi ulang (seeding).
    Sangat berguna saat testing atau demo presentasi skripsi jika data acak-acakan.
    """
    print("🚀 Memulai Proses Sapu Bersih & Injeksi TOTAL Database MySQL...")
    
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # ================================================================
        # 1. EKSEKUSI SAPU BERSIH 
        # ================================================================
        print("🧹 1. Menghapus data lama yang berantakan dan mereset ID ke 1...")
        
        # Matikan cek Foreign Key sementara agar bisa menghapus tabel induk tanpa error Constraint
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("DELETE FROM ar_sessions;")
        cursor.execute("DELETE FROM product_features;")
        cursor.execute("DELETE FROM products;")
        
        # Reset auto_increment (ID) kembali ke 1 setelah dihapus
        cursor.execute("ALTER TABLE ar_sessions AUTO_INCREMENT = 1;")
        cursor.execute("ALTER TABLE product_features AUTO_INCREMENT = 1;")
        cursor.execute("ALTER TABLE products AUTO_INCREMENT = 1;")
        
        # Hidupkan kembali proteksi Foreign Key
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        
        # Pastikan kolom gender mendukung ENUM 'wanitahijab' (antisipasi kalau tabel lama belum update)
        try:
            cursor.execute("ALTER TABLE products MODIFY COLUMN gender ENUM('pria', 'wanita', 'wanitahijab', 'unisex') DEFAULT 'pria';")
        except:
            pass 
            
        conn.commit()
        print("✅ Database berhasil dibersihkan total!")

        # ================================================================
        # 2. PROSES SEEDING SEMUA KATEGORI (PRIA, WANITA, HIJAB)
        # ================================================================
        print("\n📦 2. Memulai injeksi data untuk SEMUA KATEGORI (Pria, Wanita, Hijab)...")
        
        # Daftar spesifikasi kategori yang akan di-scan dan dimasukkan ke database
        categories_to_seed = [
            {'folder': 'Pria', 'gender': 'pria', 'tipe': ['Kemeja Pria', 'Kaos Pria', 'Jaket Bomber', 'Celana Chino', 'Sweater Pria'], 'brand': 'Zalora Men'},
            {'folder': 'Wanita', 'gender': 'wanita', 'tipe': ['Blouse Korea', 'Dress Bunga', 'Kaos Casual', 'Cardigan Rajut', 'Rok Plisket'], 'brand': 'Zalora Women'},
            {'folder': 'wanitahijab', 'gender': 'wanitahijab', 'tipe': ['Gamis Syari', 'Tunik Hijab', 'Blouse Lengan Panjang', 'Abaya', 'Outer Hijab'], 'brand': 'Zalora Hijab'}
        ]

        total_success = 0

        for cat in categories_to_seed:
            target_dir = get_target_dir(cat['folder'])
            print(f"\n   🔍 Memindai folder: {cat['folder']}...")
            
            if not os.path.exists(target_dir):
                print(f"   ⚠️ WARNING: Folder fisik '{cat['folder']}' tidak ditemukan. Melewati kategori {cat['gender']}.")
                continue

            images = [f for f in os.listdir(target_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
            
            if not images:
                print(f"   ⚠️ WARNING: Tidak ada file gambar di dalam folder '{cat['folder']}'.")
                continue

            cat_count = 0
            
            # Looping setiap gambar di folder dan buatkan data dummy-nya
            for index, filename in enumerate(images):
                external_id = f"ZLR-{cat['gender'][:3].upper()}-{uuid.uuid4().hex[:8].upper()}"
                tipe_baju = random.choice(cat['tipe'])
                name = f"{tipe_baju} Premium #{index + 1}"
                brand = cat['brand']
                price = random.randint(100, 500) * 1000  # Harga random 100k - 500k
                
                # Simpan URL relatif yang bisa diakses oleh frontend
                image_url = f"products/{cat['folder']}/{filename}"
                gender = cat['gender'] 
                
                sql = """
                INSERT INTO products 
                (product_external_id, name, brand, price, image_url, source_platform, gender, is_active) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                val = (external_id, name, brand, price, image_url, 'zalora', gender, 1)
                
                try:
                    cursor.execute(sql, val)
                    cat_count += 1
                    total_success += 1
                except mysql.connector.IntegrityError:
                    pass # Abaikan kalau data duplikat (id bentrok)
            
            print(f"   ✅ Berhasil memasukkan {cat_count} produk ke kategori '{cat['gender']}'.")
        
        # Simpan perubahan (WAJIB di MySQL)
        conn.commit()
        print(f"\n🎉 SELESAI! Total {total_success} Produk dari semua kategori berhasil dimasukkan.")

    except mysql.connector.Error as err:
        print(f"💥 Error Database: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    fix_and_seed_database()