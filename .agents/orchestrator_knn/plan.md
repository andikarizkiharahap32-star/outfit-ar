# Project: OutfitAR KNN System Activation

## Architecture
- Backend: FastAPI + SQLAlchemy async, database MySQL/MariaDB.
- Model: `OutfitFeatureExtractor` in `backend/ml/cnn/feature_extractor.py` (EfficientNet-B0 base, 1377-dim vectors).
- Recommender: `KNNOutfitRecommender` in `backend/ml/knn/outfit_recommender.py`.
- Router: `backend/app/routers/recommendations.py` which currently uses Seasonal Color Analysis only.
- Database: MySQL/MariaDB with `products` table having a `feature_vector` JSON column (currently NULL).

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Setup & Exploration | Find ML files, check database connectivity, run existing tests, inspect router code. | None | DONE |
| 2 | Populate Script (R1) | Implement `backend/scripts/populate_features.py` with multi-threading / concurrent async streams (max 5 parallel, 10s timeout, graceful error handling). | M1 | DONE |
| 3 | KNN Integration (R2, R3) | Modify `backend/app/routers/recommendations.py` to use KNN model (lazy initialization), query vector padding + L2 normalization, pre-filtering (50 candidates), fallback (<10 vectors), and re-ranking. | M2 | DONE |
| 4 | Verification & Audit | Verify endpoints (HTTP 200, output structure, algorithm version "v5.0-knn+seasonal"), run Forensic Auditor, run Challenger. | M3 | DONE |

## Interface Contracts
- `backend/ml/cnn/feature_extractor.py` -> `OutfitFeatureExtractor`
  - Function: `extract_features(image_bytes)` -> Returns np.ndarray of shape (1377,)
- `backend/ml/knn/outfit_recommender.py` -> `KNNOutfitRecommender`
  - Class initialized with product data and fit on features.
  - Query with feature vector to get nearest neighbors.

## Code Layout
- `backend/ml/cnn/` - Feature extraction module
- `backend/ml/knn/` - KNN recommender module
- `backend/app/routers/` - FastAPI routers (including `recommendations.py`)
- `backend/scripts/` - Maintenance and utility scripts
