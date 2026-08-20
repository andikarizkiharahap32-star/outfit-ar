import os
import time
import random
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

class ZaloraWomenResearchScraper:
    def __init__(self, target_count=500):
        self.target_count = target_count
        self.count = 0
        self.target_dir = os.path.join('uploads', 'products')
        # Keywords diperluas untuk mencakup variasi atasan wanita
        self.keywords = ["kaos", "blouse", "kemeja", "t-shirt", "shirt", "hoodie", "top", "atasan", "tunik", "crop top"]
        self.driver = None
        
        # Buat folder jika belum ada
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)

    def init_driver(self):
        """Inisialisasi dengan pengunci versi Chrome 147 agar tidak mismatch."""
        options = uc.ChromeOptions()
        options.add_argument('--no-first-run')
        options.add_argument('--password-store=basic')
        options.add_argument('--start-maximized')
        options.add_argument('--disable-popup-blocking')
        
        print("🚀 Memulai Engine Scraper Wanita (Advanced Anti-Detect)...")
        try:
            # Mengunci ke versi 147 sesuai spesifikasi laptop Anda
            self.driver = uc.Chrome(options=options, version_main=147)
        except Exception as e:
            print(f"⚠️ Mencoba mode auto-version karena: {e}")
            self.driver = uc.Chrome(options=options)

    def download_image(self, url, filename):
        """Proses download dengan header simulasi browser asli."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
                'Referer': 'https://www.zalora.co.id/'
            }
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200:
                with open(os.path.join(self.target_dir, filename), 'wb') as f:
                    f.write(response.content)
                return True
        except Exception:
            return False
        return False

    def scrape(self):
        self.init_driver()
        
        # Link 10 Halaman yang Anda berikan
        urls = [
            "https://www.zalora.co.id/p/lozy-hijab-hooja-set-light-forest-green-white-4144205",
            "https://www.zalora.co.id/p/lozy-hijab-naomi-set-black-black-4173119",
            "https://www.zalora.co.id/p/klamby-klamby-verra-knit-cardigan-morning-dove-5001198",
            "https://www.zalora.co.id/p/klamby-klamby-ratimaya-tunic-white-dove-m-4896535",
            "https://www.zalora.co.id/p/klamby-klamby-crestella-blouse-butter-cream-4953081",
            "https://www.zalora.co.id/p/klamby-klamby-mariri-shirt-espresso-bliss-4898235",
            "https://www.zalora.co.id/p/klamby-klamby-shara-outer-vest-white-pearl-4191433",
            "https://www.zalora.co.id/p/jenahara-kovra-shirt-25k040-black-5184113",
            "https://www.zalora.co.id/p/cotton-bee-cotton-bee-lunara-tunik-set-tunik-kulot-khimar-setelan-wanita-xl-black-5277363",
            "https://www.zalora.co.id/p/lish-rachel-denim-shirt-black-denim-black-4741522"
        ]

        try:
            for page_idx, url in enumerate(urls, 1):
                if self.count >= self.target_count:
                    break
                
                print(f"\n📑 HALAMAN {page_idx} | Progress Dataset Wanita: {self.count}/{self.target_count}")
                self.driver.get(url)
                
                # Jeda manusiawi agar tidak dicurigai bot
                time.sleep(random.uniform(7, 10))

                # --- ADVANCED LAZY-LOAD TRIGGER ---
                # Scroll bertahap 800 pixel sebanyak 7 kali per halaman
                for s in range(7):
                    self.driver.execute_script(f"window.scrollTo(0, {(s+1)*800});")
                    time.sleep(1.5)

                # Mendeteksi semua elemen gambar produk
                images = self.driver.find_elements(By.TAG_NAME, "img")
                
                for img in images:
                    if self.count >= self.target_count: break
                    
                    try:
                        alt_text = (img.get_attribute("alt") or "").lower()
                        # Gambar Zalora sering tersimpan di 'data-src' sebelum tampil di layar
                        img_url = img.get_attribute("data-src") or img.get_attribute("src")

                        # Logika Filter: Harus mengandung kata kunci atasan wanita
                        if img_url and any(kw in alt_text for kw in self.keywords):
                            if "http" in img_url and "dynamic" in img_url:
                                # Dapatkan URL gambar resolusi tinggi
                                clean_url = img_url.split('?')[0] if '?' in img_url else img_url
                                
                                filename = f"women_top_{self.count}.jpg"
                                if self.download_image(clean_url, filename):
                                    print(f"   ✅ Berhasil: {filename} ({alt_text[:25]})")
                                    self.count += 1
                                    
                    except Exception:
                        continue

        except Exception as e:
            print(f"💥 Kesalahan Fatal: {e}")
        finally:
            print(f"\n✨ PROSES SELESAI!")
            print(f"📊 Total Dataset Wanita Berhasil Diambil: {self.count}")
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass

if __name__ == "__main__":
    # Target 500 gambar untuk skripsi
    scraper = ZaloraWomenResearchScraper(target_count=500)
    scraper.scrape()