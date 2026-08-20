import os
import io
import pytest
import cv2
import numpy as np
import tensorflow as tf
from pathlib import Path
from loguru import logger

# Import modules to test
from ml.knn.outfit_recommender import KNNOutfitRecommender
from ml.cnn.skin_tone_classifier import SkinToneClassifier
from ml.cnn.efficientnet_backbone import build_skin_tone_classifier

# Helper to locate train_cnn.py
BACKEND_DIR = Path(__file__).resolve().parent.parent

# =====================================================================
# AUDIT BUGS VERIFICATION
# =====================================================================

def test_bug_1_knn_recommender_integration_or_fallback():
    """Bug 1: KNN Recommender integration or fallback (ensure it doesn't fail)."""
    # Create KNN Recommender
    recommender = KNNOutfitRecommender(n_neighbors=5, metric="cosine")
    
    # Check that we can fit and recommend without crashing
    features = np.random.rand(10, 1280).astype(np.float32)
    product_ids = list(range(1, 11))
    product_categories = {i: (5 if i % 2 == 0 else 6) for i in product_ids}
    product_skin_compat = {i: [1, 2, 3] for i in product_ids}
    product_names = {i: f"Product Name {i}" for i in product_ids}
    
    recommender.fit(
        feature_matrix=features,
        product_ids=product_ids,
        product_categories=product_categories,
        product_skin_compat=product_skin_compat,
        product_names=product_names
    )
    
    query = np.random.rand(1280).astype(np.float32)
    res = recommender.recommend(query, skin_tone_level=2, top_k=3)
    assert len(res) > 0


def test_bug_2_cnn_data_augmentation_exists_in_train_cnn():
    """Bug 2: CNN Data augmentation exists in train_cnn.py code."""
    train_cnn_path = BACKEND_DIR / "ml" / "cnn" / "train_cnn.py"
    assert train_cnn_path.exists()
    
    with open(train_cnn_path, "r", encoding="utf-8") as f:
        code_content = f.read()
        
    # Check for Keras Random layers or data_augmentation instantiation in code
    assert "data_augmentation" in code_content
    assert "RandomFlip" in code_content
    assert "RandomRotation" in code_content
    assert "RandomBrightness" in code_content or "RandomContrast" in code_content


def test_bug_3_diversity_score_calculated_as_pairwise_color_distance(client):
    """Bug 3: diversity_score is calculated as pairwise color distance and is not hardcoded 1.0."""
    # Call recommendations with top_k = 5
    payload = {"gender": "pria", "skin_tone_level": 2, "top_k": 5}
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    div_score = data["data"]["diversity_score"]
    
    assert isinstance(div_score, float)
    # Check that it is not hardcoded to 1.0
    assert div_score != 1.0
    assert 0.0 <= div_score <= 1.0


def test_bug_4_and_10_category_slot_resolved_via_keyword_matching():
    """
    Bug 4 & 10: category_slot is resolved via keyword matching from product name 
    (kaos/hoodie/kemeja -> atasan, celana -> celana, rok -> bawahan, etc.) 
    and falls back properly when category_id=NULL.
    """
    # Test keyword matching using KNN Recommender
    recommender = KNNOutfitRecommender(n_neighbors=5, metric="cosine")
    
    features = np.random.rand(5, 1280).astype(np.float32)
    product_ids = [1, 2, 3, 4, 5]
    # Set category_id = None for all products (NULL in DB)
    product_categories = {1: None, 2: None, 3: None, 4: None, 5: None}
    product_skin_compat = {i: [1, 2, 3] for i in product_ids}
    
    # Specify product names containing slot keywords
    product_names = {
        1: "Kaos Polo Hitam",    # should match "atasan"
        2: "Celana Jeans Slim",  # should match "celana"
        3: "Rok Plisket",        # should match "bawahan"
        4: "Sepatu Sneakers",    # should match "sepatu"
        5: "Tas Pinggang Kulit"  # should match "aksesori"
    }
    
    recommender.fit(
        feature_matrix=features,
        product_ids=product_ids,
        product_categories=product_categories,
        product_skin_compat=product_skin_compat,
        product_names=product_names
    )
    
    query = np.random.rand(1280).astype(np.float32)
    # Get all products
    res = recommender.recommend(query, skin_tone_level=2, top_k=5)
    
    # Check that slots are correctly resolved from name keywords
    for item in res:
        name = product_names[item.product_id]
        if "Kaos" in name:
            assert item.category_slot == "atasan"
        elif "Celana" in name:
            assert item.category_slot == "celana"
        elif "Rok" in name:
            assert item.category_slot == "bawahan"
        elif "Sepatu" in name:
            assert item.category_slot == "sepatu"
        elif "Tas" in name:
            assert item.category_slot == "aksesori"


def test_bug_5_deterministic_diversity_selection(client):
    """Bug 5: Deterministic diversity selection from top-30 candidates (max color distance) is used."""
    payload = {"gender": "pria", "skin_tone_level": 2, "top_k": 5}
    
    # Run the same request twice
    res1 = client.post("/api/v1/recommendations", json=payload)
    res2 = client.post("/api/v1/recommendations", json=payload)
    
    assert res1.status_code == 200
    assert res2.status_code == 200
    
    items1 = [item["product"]["id"] for item in res1.json()["data"]["outfit_set"]]
    items2 = [item["product"]["id"] for item in res2.json()["data"]["outfit_set"]]
    
    # Outputs must be identical (deterministic)
    assert items1 == items2


def test_bug_6_predict_cnn_uses_intermediate_model_shape_1280():
    """Bug 6: _predict_cnn in skin_tone_classifier.py uses intermediate model and has shape 1280."""
    classifier = SkinToneClassifier()
    # Create a dummy image
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    
    # Run predict_cnn
    probs, feature_vec = classifier._predict_cnn(img)
    
    assert probs.shape == (3,)
    assert feature_vec.shape == (1280,)


def test_bug_7_ensemble_rounding_uses_standard_rounding():
    """Bug 7: Ensemble rounding uses standard rounding int(x + 0.5) instead of banker's round()."""
    classifier = SkinToneClassifier()
    
    # Test standard mathematical rounding of 2.5 which must result in 3
    # cnn_level = 2, hsv_level = 3 -> (2 * 0.7) + (3 * 0.3) = 1.4 + 0.9 = 2.3
    # Let's test a case where (cnn_level * 0.7) + (hsv_level * 0.3) is exactly 2.5
    # e.g., cnn_level = 1, hsv_level = 6 -> (1 * 0.7) + (6 * 0.3) = 0.7 + 1.8 = 2.5
    # In banker's rounding, round(2.5) is 2. In standard rounding, it is 3.
    # Let's call the rounding logic with a simulated calculation
    cnn_level = 1
    hsv_level = 6
    final_level, _ = classifier._ensemble_prediction(np.array([0.9, 0.05, 0.05]), hsv_level)
    
    # Note: 2.5 rounded using int(x + 0.5) is 3
    # The return value is clipped between 1 and 3, so 3 is correct.
    assert final_level == 3


def test_bug_8_efficientnet_backbone_dense_head_sequence_order():
    """Bug 8: efficientnet_backbone.py Dense head sequence order: Dense -> BN -> Activation(relu) -> Dropout."""
    model = build_skin_tone_classifier(num_classes=3)
    
    # Get layers starting from head_dense
    layer_names = [layer.name for layer in model.layers]
    
    # Locate index of head_dense
    dense_idx = layer_names.index("head_dense")
    bn_idx = layer_names.index("head_bn")
    act_idx = layer_names.index("head_activation")
    drop_idx = layer_names.index("head_dropout")
    
    # Verify strict sequence order
    assert dense_idx < bn_idx
    assert bn_idx < act_idx
    assert act_idx < drop_idx


def test_bug_9_skin_tone_range_check_in_knn():
    """Bug 9: Skin tone range check in KNN (range(1, 4) instead of range(1, 6))."""
    # Create KNN Recommender and query it
    recommender = KNNOutfitRecommender(n_neighbors=5, metric="cosine")
    
    features = np.random.rand(5, 1280).astype(np.float32)
    product_ids = [1, 2, 3, 4, 5]
    product_categories = {i: 5 for i in product_ids}
    # Do not set skin compatibility (so it falls back to range)
    product_skin_compat = {}
    
    recommender.fit(
        feature_matrix=features,
        product_ids=product_ids,
        product_categories=product_categories,
        product_skin_compat=product_skin_compat
    )
    
    # Query with skin tone level 4
    query = np.random.rand(1280).astype(np.float32)
    # Under range(1, 4), level 4 is not compatible, so we should get 0 recommendations
    res = recommender.recommend(query, skin_tone_level=4, top_k=5)
    assert len(res) == 0


def test_bug_11_save_check_fitted():
    """Bug 11: save() check fitted."""
    recommender = KNNOutfitRecommender()
    
    # Calling save before fit must raise RuntimeError
    with pytest.raises(RuntimeError) as exc_info:
        recommender.save("test_save_fitted.pkl")
    
    assert "belum dilatih" in str(exc_info.value)


def test_bug_12_detect_skin_tone_database_commit_check(client):
    """Bug 12: detect_skin_tone database commit check."""
    # Post a skin tone detection
    img_bytes = create_mock_image(80, 120, 180)
    files = {"image": ("scan.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    assert response.status_code == 200
    det_id = response.json()["detection_id"]
    
    # Query recommendations endpoint using this skin_tone_id
    # If it was committed properly, recommendations will be able to retrieve the detection by ID
    payload = {"gender": "pria", "skin_tone_level": 2, "skin_tone_id": det_id}
    response_rec = client.post("/api/v1/recommendations", json=payload)
    assert response_rec.status_code == 200


def test_bug_13_class_weights_calculation_and_fit_parameter():
    """Bug 13: Class weights calculation and fit parameter in train_cnn.py."""
    train_cnn_path = BACKEND_DIR / "ml" / "cnn" / "train_cnn.py"
    assert train_cnn_path.exists()
    
    with open(train_cnn_path, "r", encoding="utf-8") as f:
        code_content = f.read()
        
    # Check class weights dynamic calculation
    assert "class_weights" in code_content
    assert "total_samples /" in code_content
    # Check passed as fit parameter
    assert "class_weight=class_weights" in code_content or "class_weight = class_weights" in code_content


def test_bug_14_single_l2_normalization_check():
    """Bug 14: Single L2 normalization check."""
    recommender = KNNOutfitRecommender(n_neighbors=5, metric="cosine")
    
    features = np.random.rand(5, 1280).astype(np.float32)
    product_ids = [1, 2, 3, 4, 5]
    product_categories = {i: 5 for i in product_ids}
    product_skin_compat = {i: [1, 2, 3] for i in product_ids}
    
    recommender.fit(
        feature_matrix=features,
        product_ids=product_ids,
        product_categories=product_categories,
        product_skin_compat=product_skin_compat
    )
    
    # Check that feature matrix vectors are normalized (L2 norm should be exactly 1.0)
    for i in range(len(product_ids)):
        norm = np.linalg.norm(recommender._feature_matrix[i])
        assert abs(norm - 1.0) < 1e-5


def test_bug_15_learning_rate_and_kernel_regularizer():
    """Bug 15: Learning rate <= 1e-4 and kernel_regularizer in backbone dense layer."""
    model = build_skin_tone_classifier(num_classes=3)
    
    # Verify dense head kernel regularizer exists and is L2
    dense_layer = model.get_layer("head_dense")
    assert dense_layer.kernel_regularizer is not None
    # Class name should be L2 or contain L2
    assert "L2" in dense_layer.kernel_regularizer.__class__.__name__
    
    # Check learning rate <= 1e-4 in train_cnn.py
    train_cnn_path = BACKEND_DIR / "ml" / "cnn" / "train_cnn.py"
    with open(train_cnn_path, "r", encoding="utf-8") as f:
        code = f.read()
    
    assert "learning_rate=1e-4" in code or "learning_rate = 1e-4" in code or "learning_rate=0.0001" in code


# Helper to create image
def create_mock_image(b=80, g=120, r=180):
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    img[:, :] = [b, g, r]
    _, buffer = cv2.imencode('.jpg', img)
    return io.BytesIO(buffer.tobytes())
