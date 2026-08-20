## 2026-06-28T09:20:20Z
Your task is to implement and activate the KNN recommendation system for the OutfitAR application.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A Forensic Auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Here is your step-by-step tasks:

1. Service Diagnostics & Database Setup:
   - Verify if the MySQL/MariaDB database is running. If not, start it (e.g. check standard services or search for running mysqld, or start the Windows service if possible, or start Laragon's mysql).
   - Verify database connectivity using backend/venv_fix/Scripts/python.exe.

2. R1. Batch Feature Extraction Script (backend/scripts/populate_features.py):
   - Query all products from the database where `feature_vector IS NULL`.
   - Implement concurrent image streaming from the product `image_url` via HTTP (max 5 parallel requests, 10s timeout, without saving to disk).
   - Use `OutfitFeatureExtractor` (imported from `ml.cnn.feature_extractor.OutfitFeatureExtractor`) to extract the 1377-dimensional feature vectors. Note: you must decode the streamed image bytes into BGR format using OpenCV (e.g., cv2.imdecode(np.frombuffer(content, np.uint8), cv2.IMREAD_COLOR)) before feeding it to `extractor.extract(img)`.
   - Save the feature vector as a JSON list of floats to the `feature_vector` column of the `products` table in the database.
   - Implement graceful error handling per product (if any HTTP error, timeout, or OpenCV decode failure occurs, log a WARNING, increment the failure counter, and continue).
   - Show progress bar / print current progress and display a final summary: total processed, succeeded, failed.
   - Run the script and verify that at least the first 10 products are populated with non-NULL feature vectors in the database.

3. R2 & R3. KNN Integration as Pre-filter (backend/app/routers/recommendations.py):
   - Modify the `recommend_outfit` endpoint in `backend/app/routers/recommendations.py` to integrate KNN as a pre-filter.
   - Use a global KNN Recommender instance (`KNNOutfitRecommender` imported from `ml.knn.outfit_recommender`).
   - Implement lazy initialization: Fit the KNN recommender on the first request if it is not already initialized, using all products that have `feature_vector IS NOT NULL` in the database.
   - Query all such products, load their `feature_vector` lists, category IDs, skin tone compatibility, and names, and call `recommender.fit()`.
   - If the number of products with non-NULL features is < 10, fallback automatically to the original Seasonal Color Analysis logic.
   - For R3 query vector: represent the user's skin tone as a 96-dimensional color histogram.
     To do this: retrieve the user's skin tone RGB color (from SKIN_TONE_MAP or skin_tone_id). Create a 1x1 BGR image, convert it to HSV space, and compute the 96-dim color histogram using cv2.calcHist (similar to how HSV histogram is calculated in `OutfitFeatureExtractor._extract_color_histogram` for a single image).
   - Zero-pad this 96-dimensional histogram to a 1377-dimensional vector (since `OutfitFeatureExtractor` has 1377 dimensions, with color histogram at index 1280 to 1375).
   - Perform L2 normalization on this 1377-dim vector.
   - Pass the normalized 1377-dim vector to `recommender.recommend()` to get the 50 closest candidate products.
   - Re-rank those 50 candidate products using the Seasonal Color Analysis scoring logic that already exists in recommendations.py.
   - Ensure the structure of the API response does not change (backward compatible).
   - Set the `algorithm_ver` field in the response to `"v5.0-knn+seasonal"` when KNN is used.
   - Save the skin tone detection feature vector inside `SkinToneDetection.feature_vector` in `/detect-skin-tone` if applicable, or ensure it compiles cleanly.

4. Testing & Verification:
   - Run pytest using backend/venv_fix/Scripts/python.exe -m pytest -v to verify all tests pass.
   - Test recommendations endpoint manually with Invoke-WebRequest or curl as specified in Acceptance Criteria.
   - Write your handoff report containing commands used, build/test results, and changes made in C:\Final_outfitAR\outfit-ar\.agents\worker_m2_m3\handoff.md.
