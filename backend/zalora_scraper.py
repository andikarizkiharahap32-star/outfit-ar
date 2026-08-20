import os
import time
import random
import requests
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException

class ZaloraResearchScraper:
    """
    Script Scraper Otomatis untuk mengumpulkan dataset gambar baju dari Zalora.
    Digunakan untuk membangun dataset pelatihan AI di skripsi.
    """
    def __init__(self, target_count=500):
        self.target_count = target_count # Target berapa banyak gambar yang mau didownload
        self.count = 0
        self.target_dir = os.path.join('uploads', 'products')
        
        # Kata kunci yang boleh diambil gambarnya (hanya atasan)
        self.keywords = ["kaos", "kemeja", "hoodie", "t-shirt", "shirt", "polo", "sweatshirt"]
        self.driver = None
        
        # Buat folder jika belum ada
        if not os.path.exists(self.target_dir):
            os.makedirs(self.target_dir)

    def init_driver(self):
        """
        Inisialisasi Selenium WebDriver.
        Menggunakan `undetected_chromedriver` (uc) untuk mem-bypass deteksi bot Cloudflare/WAF Zalora.
        """
        options = uc.ChromeOptions()
        options.add_argument('--no-first-run')
        options.add_argument('--no-service-autorun')
        options.add_argument('--password-store=basic')
        options.add_argument('--start-maximized') # Fullscreen agar lebih banyak gambar yang di-render
        
        print("🚀 Menyiapkan Engine Scraper (Anti-Detect Mode)...")
        try:
            # Mengunci ke versi Chrome tertentu (misal 147) agar ChromeDriver tidak mismatch
            self.driver = uc.Chrome(options=options, version_main=147)
        except Exception as e:
            print(f"⚠️ Mencoba inisialisasi ulang driver: {e}")
            # Fallback jika versi 147 gagal
            self.driver = uc.Chrome(options=options)

    def download_image(self, url, filename):
        """Mendownload gambar dengan validasi header."""
        try:
            # Meniru browser asli (Headers Spoofer) agar tidak di-block server Zalora
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Referer': 'https://www.zalora.co.id/'
            }
            # Timeout 15 detik kalau nge-lag
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                with open(os.path.join(self.target_dir, filename), 'wb') as f:
                    f.write(response.content)
                return True
        except Exception as e:
            print(f"   ❌ Gagal download {filename}: {e}")
        return False

    def scrape(self):
        self.init_driver()
        
        # Daftar 20 Halaman (page 1 sampai 20) untuk memastikan target 500 tercapai
        base_url = "https://www.zalora.co.id/search?q=atasan+pria+kaos+&search_method=submit+search&categoryId=35&categoryId=10293&categoryId=31"
        urls = [base_url] + [f"{base_url}&page={i}" for i in range(2, 21)]

        try:
            for page_idx, url in enumerate(urls, 1):
                if self.count >= self.target_count:
                    break
                
                print(f"\n📑 MEMPROSES HALAMAN {page_idx} | Progress: {self.count}/{self.target_count}")
                self.driver.get(url)
                
                # Human-like wait (Random delay 6-10 detik agar tidak dikira bot spam)
                time.sleep(random.uniform(6, 10)) 

                # --- ADVANCED SCROLLING (Lazy Load Discovery) ---
                # E-commerce modern seperti Zalora menerapkan "Lazy Loading".
                # Gambar tidak akan dimuat (di-load) oleh server sebelum kursor user turun (scroll) ke elemen tersebut.
                for s in range(5):
                    # Scroll ke bawah secara bertahap tiap 1000 pixel
                    self.driver.execute_script(f"window.scrollTo(0, {(s+1)*1000});")
                    time.sleep(1.5) # Tunggu gambar ke-load

                # Temukan semua elemen gambar di halaman web (TAG <img>)
                images = self.driver.find_elements(By.TAG_NAME, "img")
                
                for img in images:
                    if self.count >= self.target_count: break
                    
                    try:
                        alt_text = (img.get_attribute("alt") or "").lower()
                        # Ambil link gambar dari 'data-src' (lazy load asli) atau 'src' (sudah ke-load)
                        img_url = img.get_attribute("data-src") or img.get_attribute("src")

                        # Validasi: Pastikan alt_text (judul gambar) punya kata kunci atasan (kaos/kemeja)
                        if img_url and any(kw in alt_text for kw in self.keywords):
                            # Filter link gambar produk asli Zalora (biasanya ada "dynamic" di link-nya)
                            if "http" in img_url and "dynamic" in img_url: 
                                
                                # Bersihkan URL dari parameter '?width=...' agar mendapat resolusi tinggi/asli
                                clean_url = img_url.split('?')[0] if '?' in img_url else img_url
                                
                                filename = f"zalora_research_{self.count}.jpg"
                                if self.download_image(clean_url, filename):
                                    print(f"   ✅ Saved: {filename} ({alt_text[:30]}...)")
                                    self.count += 1
                                    
                    except:
                        continue

        except Exception as e:
            print(f"💥 Fatal Error: {e}")
        finally:
            self.finish()

    def finish(self):
        """Menutup browser setelah selesai."""
        print(f"\n🎯 SELESAI! Total data untuk skripsi: {self.count} gambar.")
        if self.driver:
            try:
                self.driver.close()
                self.driver.quit()
            except:
                # Menekan error "WinError 6" yang kadang muncul saat Chrome ditutup paksa
                pass

if __name__ == "__main__":
    scraper = ZaloraResearchScraper(target_count=500)
    scraper.scrape()