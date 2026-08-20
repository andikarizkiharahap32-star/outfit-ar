# Handoff Report - KNN Recommendation System Context Gathering

## 1. Observation
I investigated the codebase to gather all necessary context for the activation of the KNN Recommendation System. Here are the direct findings:

### 1.1 OutfitFeatureExtractor
- **File Path**: `C:\Final_outfitAR\outfit-ar\backend\ml\cnn\feature_extractor.py`
- **Class Structure**:
  ```python
  class OutfitFeatureExtractor:
      """
      Mengekstrak multi-modal features dari gambar produk:
          1. CNN Features   : EfficientNet-B0 deep features (1280-dim)
          2. Color Features : HSV histogram (96-dim)
          3. Texture Score  : LBP-based texture scalar

      Total feature = 1280 + 96 + 1 = 1377 dimensi
      """
      def __init__(self, use_color: bool = True, use_texture: bool = True) -> None: ...
      def extract(self, image_bgr: np.ndarray) -> np.ndarray: ...
      def extract_batch(self, images_bgr: list[np.ndarray]) -> np.ndarray: ...
      def save_cache(self, feature_matrix: np.ndarray, product_ids: list[int], path: str | Path) -> None: ...
      def load_cache(self, path: str | Path) -> tuple[np.ndarray, list[int]]: ...
  ```

### 1.2 KNNOutfitRecommender
- **File Path**: `C:\Final_outfitAR\outfit-ar\backend\ml\knn\outfit_recommender.py`
- **Class Structure**:
  ```python
  class KNNOutfitRecommender:
      """
      Mesin rekomendasi outfit berbasis KNN dengan Gap Diversity.
      """
      def __init__(self, n_neighbors: int = 20, metric: str = "cosine") -> None: ...
      def fit(
          self,
          feature_matrix: np.ndarray,
          product_ids: list[int],
          product_categories: dict[int, int],
          product_skin_compat: dict[int, list[int]],
          product_names: Optional[dict[int, str]] = None,
      ) -> "KNNOutfitRecommender": ...
      def recommend(
          self,
          query_features: np.ndarray,
          skin_tone_level: int,
          top_k: int = 10,
          diversity_threshold: float = 0.3,
          target_slots: Optional[list[str]] = None,
      ) -> list[OutfitCandidate]: ...
      def recommend_complete_outfit(
          self,
          query_features: np.ndarray,
          skin_tone_level: int,
          diversity_threshold: float = 0.3,
      ) -> OutfitSet: ...
      def save(self, path: str | Path) -> None: ...
      def load(self, path: str | Path) -> "KNNOutfitRecommender": ...
  ```

### 1.3 Recommendations Router
- **File Path**: `C:\Final_outfitAR\outfit-ar\backend\app\routers\recommendations.py`
- **Current Behavior**:
  - The endpoint `@router.post("")` (and `/`) handles recommendation requests.
  - It fetches all products from the database where gender matches `target_gender` or `unisex` (using `select(Product).where(Product.gender.in_([target_gender, 'unisex']))`).
  - It loops through the fetched products, categorizing color with `classify_color_season()` using HSV rules.
  - It calculates a hybrid score for each product:
    - **Season Match Score** (0-50 points) based on whether the product season matches the user skin tone's primary/secondary/avoid seasons.
    - **Color Match Score** (0-50 points) based on Euclidean distance in RGB space to recommended palette colors.
  - It retrieves the top 30 candidates and applies a deterministic color-distance diversity check.
  - Slots (`atasan`, `celana`, `sepatu`, `aksesori`) are resolved using hardcoded category mappings and regex keyword checks on the product name.

### 1.4 Database Configuration & Products Table Structure
- **Environment File**: `C:\Final_outfitAR\outfit-ar\backend\.env`
  - Host: `localhost`, Port: `3306`, Database: `outfit_ar`, User: `root`, Password: `` (empty).
- **Models File**: `C:\Final_outfitAR\outfit-ar\backend\app\models\models.py`
  - **Product Table (`products`)**:
    - `id` (Integer, PK)
    - `product_external_id` (String(255), unique)
    - `name` (String(500))
    - `category_id` (Integer, FK to `categories.id`)
    - `color` (String(100))
    - `price` (DECIMAL(12, 2))
    - `image_url` (Text)
    - `gender` (SQLEnum: 'pria', 'wanita', 'wanitahijab', 'unisex')
    - `skin_tone_compat` (JSON: e.g. list `[1, 2, 3]`)
    - `feature_vector` (JSON: raw float array)
    - `is_active` (Boolean)
  - **ProductFeature Table (`product_features`)**:
    - `id` (Integer, PK)
    - `product_id` (Integer, FK to `products.id`)
    - `feature_vector` (JSON)
    - `color_histogram` (JSON)
    - `texture_score` (Float)
    - `model_version` (String, default `"efficientnet-b0"`)
  - **SkinToneDetection Table (`skin_tone_detections`)**:
    - `id` (Integer, PK)
    - `user_id` (Integer, FK to `users.id`)
    - `skin_tone_level` (Integer)
    - `skin_tone_hex` (String(7))
    - `confidence` (Float)
    - `image_path` (Text)
    - `feature_vector` (JSON, currently NULL or unused in `recommendations.py` save logic)

### 1.5 Python Environment
- **Path**: `C:\Final_outfitAR\outfit-ar\backend\venv_fix\`
- **Python Version**: `3.12.8` (Checked via command execution)
- **Key Installed Packages**:
  - `tensorflow` (2.16.1), `keras` (3.14.0), `scikit-learn` (1.9.0), `numpy` (1.26.4), `pymysql` (PyMySQL), `aiomysql` (0.3.2), `SQLAlchemy` (2.0.49).

### 1.6 Verification / Run Errors
- When trying to query the database using the test command or database check script, the following error is thrown:
  ```
  pymysql.err.OperationalError: (2003, "Can't connect to MySQL server on 'localhost' ([WinError 10061] No connection could be made because the target machine actively refused it)")
  ```
  This indicates the MySQL Server (usually provided by Laragon in this project environment) is currently offline.

---

## 2. Logic Chain
1. To activate the KNN recommendation system, the FastAPI backend must be able to load the KNN models (`recommender.load(settings.knn_model_path)`) and map query images/faces to product image features.
2. Currently, the recommendations router does not load or use the `KNNOutfitRecommender` or the `OutfitFeatureExtractor` during `/recommendations` API calls.
3. In `recommendations.py`, `detect_skin_tone` performs CNN inference but does not store `feature_vector` inside the `SkinToneDetection` table during creation, although the model returns `feature_vector` in `SkinToneResult`.
4. In `recommendations.py`, the recommendation loop processes all products matching the gender in memory, which is inefficient.
5. Implementing the KNN pre-filter requires:
   - Saving the 1280-dim `feature_vector` in the `SkinToneDetection` table when `detect_skin_tone` executes.
   - Initializing `KNNOutfitRecommender` on startup or dynamically loading the trained `.pkl` model file.
   - Fetching the query product/skin features from the database by `skin_tone_id`.
   - Running the KNN search (`recommender.recommend`) to filter down candidates to a subset of `top_k` products, rather than querying all products.

---

## 3. Caveats
- Since the MySQL server is currently offline on localhost:3306, the database itself was not queried for actual live records (however, the SQLAlchemy models and `.env` config are verified).
- No actual feature extraction from physical files was ran (the training script `train_models.py` has a fallback `DUMMY` feature mode for development).

---

## 4. Conclusion
The infrastructure for KNN recommendation is mostly in place (Python environment, database schemas, feature extraction code, and ML backbone are sound). However, the recommendations endpoint is currently unintegrated with the KNN recommender, and the MySQL database must be running to enable live recommendations and tests.

---

## 5. Verification Method
- **Test Runner Command**:
  ```powershell
  C:\Final_outfitAR\outfit-ar\backend\venv_fix\Scripts\python.exe -m pytest -v
  ```
  Once the MySQL server is started (e.g. via Laragon), all 60 tests in the suite should pass.
- **Database Seeder**:
  Verify product population using:
  ```powershell
  C:\Final_outfitAR\outfit-ar\backend\venv_fix\Scripts\python.exe database/db_seeder_wanita.py
  ```
- **ML Training Pipeline**:
  Run the model trainer to generate the KNN pickle file:
  ```powershell
  C:\Final_outfitAR\outfit-ar\backend\venv_fix\Scripts\python.exe scripts/train_models.py
  ```
