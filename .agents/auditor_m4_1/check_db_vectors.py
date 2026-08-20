import pymysql
import json
import numpy as np

def main():
    print("Connecting to database...")
    db_config = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': '',
        'database': 'outfit_ar',
        'cursorclass': pymysql.cursors.DictCursor
    }
    
    connection = pymysql.connect(**db_config)
    try:
        with connection.cursor() as cursor:
            # Check products with feature_vector
            cursor.execute("SELECT id, name, feature_vector FROM products WHERE feature_vector IS NOT NULL LIMIT 20")
            products = cursor.fetchall()
            
            cursor.execute("SELECT COUNT(*) as cnt FROM products")
            total_products = cursor.fetchone()['cnt']
            
            cursor.execute("SELECT COUNT(*) as cnt FROM products WHERE feature_vector IS NOT NULL")
            populated_products = cursor.fetchone()['cnt']
            
            print(f"Total products in DB: {total_products}")
            print(f"Products with feature_vector IS NOT NULL: {populated_products}")
            
            if not products:
                print("No products have feature_vector populated!")
                return
                
            print("\nAnalyzing sample feature vectors:")
            for p in products:
                pid = p['id']
                name = p['name']
                fv_str = p['feature_vector']
                
                # Check if it's a valid JSON array
                try:
                    fv = json.loads(fv_str)
                except Exception as e:
                    print(f"Product {pid}: Invalid JSON feature vector - {e}")
                    continue
                    
                if not isinstance(fv, list):
                    print(f"Product {pid}: feature_vector is not a list")
                    continue
                    
                fv_len = len(fv)
                print(f"Product {pid} ({name[:30]}): feature_vector length = {fv_len}")
                
                if fv_len != 1377:
                    print(f"  WARNING: Dimension is {fv_len} instead of 1377")
                    continue
                    
                # Inspect parts:
                cnn_part = np.array(fv[:1280])
                hsv_part = np.array(fv[1280:1376])
                tex_part = fv[1376]
                
                cnn_mean = np.mean(cnn_part)
                cnn_std = np.std(cnn_part)
                hsv_sum = np.sum(hsv_part)
                
                # Check each channel sum in HSV (3 channels, 32 bins each)
                h_sum = np.sum(hsv_part[:32])
                s_sum = np.sum(hsv_part[32:64])
                v_sum = np.sum(hsv_part[64:96])
                
                print(f"  CNN part (0-1280): mean = {cnn_mean:.6f}, std = {cnn_std:.6f}")
                print(f"  HSV part (1280-1376): sum = {hsv_sum:.6f} (H_sum = {h_sum:.4f}, S_sum = {s_sum:.4f}, V_sum = {v_sum:.4f})")
                print(f"  Texture part (1376): {tex_part}")
                
                # Check if all zeros or dummy
                if np.all(cnn_part == 0) or np.all(hsv_part == 0):
                    print("  WARNING: Feature vector contains all zeros!")
                    
    except Exception as e:
        print(f"Database error: {e}")
    finally:
        connection.close()

if __name__ == "__main__":
    main()
