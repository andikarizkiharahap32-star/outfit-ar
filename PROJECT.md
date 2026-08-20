# Project: OutfitAR ML Hardening & Verification

## Architecture
OutfitAR is an AR fashion try-on application featuring skin tone detection and outfit recommendation.
- **Backend**: FastAPI web server with REST endpoints.
  - `app.main`: Main entrypoint.
  - `app.routers.recommendations`: Endpoint `/api/v1/recommendations` and skin tone detection database logs.
- **Machine Learning**:
  - **CNN Classifier** (`backend/ml/cnn/`): Skin tone classification (EfficientNet-B0 + custom dense head). Preprocesses face images, extracts CNN feature vectors, and ensembles predictions with HSV color calculations.
  - **KNN Recommender** (`backend/ml/knn/`): Recommends outfits based on skin tone compatibility, slots, and product feature vectors.
  - **Seasonal Color Analysis**: Ranks and filters products by matching skin tone levels and utilizing the Gap Diversity MMR algorithm.

## Milestones
| # | Name | Scope | Dependencies | Status | Conversation ID |
|---|------|-------|-------------|--------|-----------------|
| 1 | E2E Testing Track | Define test infra, write E2E test suite (Tiers 1-4) covering all features and the 15 bugs. Publish `TEST_READY.md`. | none | IN_PROGRESS | 601a79f2-267b-44f5-b64e-83802392364b |
| 2 | Implementation Track | Resolve the 15 bugs in CNN training, feature extraction, KNN recommender, and recommendations router. Verify with unit tests. | none | IN_PROGRESS | ea9b681e-07e6-4f27-b31f-33d01a43421d |
| 3 | Final Validation Track | Pass 100% of E2E test suite (Phase 1) and run adversarial coverage hardening / Tier 5 (Phase 2). | 1, 2 | PLANNED | TBD |

## Interface Contracts
### Recommendations Endpoint (`POST /api/v1/recommendations`)
- **Request Body**:
  ```json
  {
    "gender": "pria" | "wanita",
    "skin_tone_level": int (1=Dark, 2=Fair, 3=Light),
    "top_k": int (optional)
  }
  ```
- **Response Body**:
  ```json
  {
    "status": "success",
    "data": [
      {
        "product_id": int,
        "name": string,
        "category_slot": string,
        "score": float,
        ...
      }
    ],
    "diversity_score": float
  }
  ```

### Skin Tone Classifier (`backend/ml/cnn/skin_tone_classifier.py`)
- `predict_skin_tone(image_path)`: Predicts level (1, 2, or 3) and extracts feature vector (shape 1280).

### KNN Outfit Recommender (`backend/ml/knn/outfit_recommender.py`)
- `recommend(skin_tone_level, gender, top_k)`: Performs KNN-based pre-filtering or returns compat list.

## Code Layout
- `backend/app/routers/recommendations.py` — API recommendation and detection router
- `backend/ml/cnn/train_cnn.py` — CNN Training entrypoint
- `backend/ml/cnn/efficientnet_backbone.py` — CNN Backbone & Dense Head construction
- `backend/ml/cnn/skin_tone_classifier.py` — CNN prediction & ensemble wrapper
- `backend/ml/cnn/feature_extractor.py` — Feature extraction helper
- `backend/ml/knn/outfit_recommender.py` — KNN logic & database product compatibility
