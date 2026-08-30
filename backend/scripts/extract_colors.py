import os
import pymysql
import cv2
import numpy as np
from sklearn.cluster import KMeans
from loguru import logger

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',
    'database': 'outfit_ar',
    'cursorclass': pymysql.cursors.DictCursor
}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOADS_DIR = os.path.join(BASE_DIR, "uploads")

def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

def extract_dominant_color(image_path, k=3):
    if not os.path.exists(image_path):
        return "#000000"
    
    # Read image
    img = cv2.imread(image_path)
    if img is None:
        return "#000000"
    
    # Convert to RGB
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Crop to center 50% to focus on the clothing and ignore borders
    h, w, _ = img.shape
    start_y, end_y = int(h * 0.25), int(h * 0.75)
    start_x, end_x = int(w * 0.25), int(w * 0.75)
    cropped = img[start_y:end_y, start_x:end_x]
    
    # Flatten pixels
    pixels = cropped.reshape(-1, 3)
    
    # Filter out near-white background (Zalora often has white/gray backgrounds)
    # If a pixel is very bright (all channels > 240), it's likely background
    non_white_pixels = pixels[np.any(pixels < 240, axis=1)]
    
    # Fallback to all pixels if the shirt itself is white
    if len(non_white_pixels) < 100:
        non_white_pixels = pixels
        
    # KMeans clustering
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit(non_white_pixels)
    
    # Find the most frequent cluster
    labels = kmeans.labels_
    counts = np.bincount(labels)
    dominant_cluster_index = np.argmax(counts)
    
    dominant_rgb = kmeans.cluster_centers_[dominant_cluster_index]
    
    return rgb_to_hex(dominant_rgb)

def main():
    logger.info("Mulai ekstraksi warna dari gambar produk...")
    
    try:
        connection = pymysql.connect(**DB_CONFIG)
        with connection.cursor() as cursor:
            # Ambil semua produk
            cursor.execute("SELECT id, name, image_url, color FROM products")
            products = cursor.fetchall()
            
            logger.info(f"Ditemukan {len(products)} produk untuk diproses.")
            
            updates = []
            for idx, p in enumerate(products):
                if not p['image_url']:
                    continue
                
                # Path gambar asli
                img_path = os.path.join(UPLOADS_DIR, p['image_url'].replace('/', os.sep))
                
                # Ekstrak warna
                new_hex = extract_dominant_color(img_path)
                
                updates.append((new_hex, p['id']))
                
                if idx % 50 == 0:
                    logger.info(f"Diproses {idx}/{len(products)}...")
            
            # Update batch ke database
            if updates:
                cursor.executemany("UPDATE products SET color = %s WHERE id = %s", updates)
                connection.commit()
                logger.info(f"[OK] Berhasil memperbarui {len(updates)} produk dengan warna asli!")
                
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        if 'connection' in locals() and connection.open:
            connection.close()

if __name__ == "__main__":
    main()
