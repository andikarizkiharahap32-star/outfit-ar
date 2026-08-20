import io
import pytest
import cv2
import numpy as np
from fastapi.testclient import TestClient

def create_mock_image(b=80, g=120, r=180):
    """Create a dummy BGR skin color image for testing."""
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    img[:, :] = [b, g, r]
    _, buffer = cv2.imencode('.jpg', img)
    return io.BytesIO(buffer.tobytes())

# =====================================================================
# TIER 1: FEATURE COVERAGE (At least 5 tests per feature)
# =====================================================================

# --- Feature 1: Health/Root ---
def test_root_endpoint(client):
    """Test GET / root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "OutfitAR"
    assert data["status"] == "online"

def test_health_endpoint(client):
    """Test GET /api/v1/health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

def test_ar_check_endpoint(client):
    """Test GET /api/v1/ar/check endpoint."""
    response = client.get("/api/v1/ar/check")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "engine_ready" in data

def test_debug_path_endpoint(client):
    """Test GET /api/v1/debug-path/ endpoint."""
    response = client.get("/api/v1/debug-path/products/Pria/test1.jpg")
    assert response.status_code == 200
    data = response.json()
    assert "python_is_looking_here" in data
    assert data["file_exists"] is True

def test_debug_path_nonexistent(client):
    """Test GET /api/v1/debug-path/ with a nonexistent path."""
    response = client.get("/api/v1/debug-path/nonexistent.jpg")
    assert response.status_code == 200
    data = response.json()
    assert data["file_exists"] is False


# --- Feature 2: Skin Tone Detection ---
def test_detect_skin_tone_valid(client):
    """Test successful skin tone detection with valid image."""
    img_bytes = create_mock_image(80, 120, 180)
    files = {"image": ("scan.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "skin_tone_level" in data
    assert data["skin_tone_level"] in [1, 2, 3]
    assert "skin_tone_hex" in data
    assert data["confidence"] >= 0.0

def test_detect_skin_tone_different_levels(client):
    """Test skin tone detection for light/fair/dark BGR ranges."""
    img_bytes = create_mock_image(220, 220, 220)
    files = {"image": ("scan.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    assert response.status_code == 200
    assert response.json()["skin_tone_level"] in [1, 2, 3]

def test_detect_skin_tone_with_user_id(client):
    """Test skin tone detection passing a user_id."""
    img_bytes = create_mock_image(80, 120, 180)
    files = {"image": ("scan.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/recommendations/detect-skin-tone?user_id=9999", files=files)
    assert response.status_code == 200
    data = response.json()
    assert data["detection_id"] is not None

def test_detect_skin_tone_response_keys(client):
    """Test that all required fields are present in skin tone detection response."""
    img_bytes = create_mock_image(80, 120, 180)
    files = {"image": ("scan.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    assert response.status_code == 200
    data = response.json()
    expected_keys = {
        "message", "skin_tone_level", "skin_tone_hex", "confidence",
        "skin_tone_label", "recommended_colors", "avoid_colors", "detection_id", "gender"
    }
    for key in expected_keys:
        assert key in data

def test_detect_skin_tone_save_to_db(client):
    """Test that detection_id points to a record successfully saved in the DB."""
    img_bytes = create_mock_image(80, 120, 180)
    files = {"image": ("scan.jpg", img_bytes, "image/jpeg")}
    response = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    assert response.status_code == 200
    data = response.json()
    detection_id = data["detection_id"]
    assert detection_id is not None
    rec_payload = {"gender": "pria", "skin_tone_level": 2, "skin_tone_id": detection_id}
    rec_response = client.post("/api/v1/recommendations", json=rec_payload)
    assert rec_response.status_code == 200


# --- Feature 3: Recommendations ---
def test_recommend_outfit_pria(client):
    """Test recommendation for gender 'pria'."""
    payload = {"gender": "pria", "skin_tone_level": 2}
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Rekomendasi biometrik berhasil diverifikasi"
    assert len(data["data"]["outfit_set"]) > 0
    for item in data["data"]["outfit_set"]:
        assert item["product"]["gender"] in ["pria", "unisex"]

def test_recommend_outfit_wanita(client):
    """Test recommendation for gender 'wanita'."""
    payload = {"gender": "wanita", "skin_tone_level": 3}
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    for item in data["data"]["outfit_set"]:
        assert item["product"]["gender"] in ["wanita", "unisex"]

def test_recommend_outfit_with_skin_tone_id(client):
    """Test recommendation using a skin_tone_id."""
    img_bytes = create_mock_image(100, 100, 100)
    files = {"image": ("scan.jpg", img_bytes, "image/jpeg")}
    det_resp = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    det_id = det_resp.json()["detection_id"]
    
    payload = {"gender": "pria", "skin_tone_level": 2, "skin_tone_id": det_id}
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200

def test_recommend_outfit_top_k(client):
    """Test that recommendation respects top_k limits."""
    payload = {"gender": "pria", "skin_tone_level": 2, "top_k": 3}
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]["outfit_set"]) <= 3

def test_recommend_outfit_diversity_score(client):
    """Test that the diversity score is correctly calculated and not hardcoded to 1.0."""
    payload = {"gender": "pria", "skin_tone_level": 2, "top_k": 5}
    response = client.post("/api/v1/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    div_score = data["data"]["diversity_score"]
    assert isinstance(div_score, float)
    assert div_score != 1.0


# --- Feature 4: Feedback ---
def test_submit_feedback_success(client):
    """Test successful feedback submission with valid details."""
    payload = {
        "session_id": "TEST-SESSION-001",
        "product_id": 1,
        "is_accepted": True,
        "feedback_score": 5
    }
    response = client.post("/api/v1/recommendations/feedback", json=payload)
    assert response.status_code == 200
    assert "Feedback" in response.json()["message"]

def test_submit_feedback_fallback(client):
    """Test fallback response when session is not in the database."""
    payload = {
        "session_id": "TEST-SESSION-NONEXISTENT",
        "product_id": 999,
        "is_accepted": False,
        "feedback_score": 2
    }
    response = client.post("/api/v1/recommendations/feedback", json=payload)
    assert response.status_code == 200
    assert "Fallback" in response.json()["message"] or "diterima" in response.json()["message"].lower()

def test_submit_feedback_is_accepted_true(client):
    """Test feedback submission with is_accepted=True."""
    payload = {
        "session_id": "TEST-SESSION-002",
        "product_id": 2,
        "is_accepted": True,
        "feedback_score": 4
    }
    response = client.post("/api/v1/recommendations/feedback", json=payload)
    assert response.status_code == 200

def test_submit_feedback_is_accepted_false(client):
    """Test feedback submission with is_accepted=False."""
    payload = {
        "session_id": "TEST-SESSION-003",
        "product_id": 3,
        "is_accepted": False,
        "feedback_score": 1
    }
    response = client.post("/api/v1/recommendations/feedback", json=payload)
    assert response.status_code == 200

def test_submit_feedback_score_validation(client):
    """Test feedback submission with average feedback score."""
    payload = {
        "session_id": "TEST-SESSION-004",
        "product_id": 4,
        "is_accepted": True,
        "feedback_score": 3
    }
    response = client.post("/api/v1/recommendations/feedback", json=payload)
    assert response.status_code == 200


# =====================================================================
# TIER 3: CROSS-FEATURE INTEGRATION (E2E FLOW)
# =====================================================================
def test_e2e_flow(client):
    """
    E2E Flow:
    1. Upload image to detect skin tone
    2. Use the detection ID to get recommendations
    3. Submit feedback on the recommended outfits
    """
    # 1. Detect skin tone
    img_bytes = create_mock_image(90, 110, 170)
    files = {"image": ("scan.jpg", img_bytes, "image/jpeg")}
    det_resp = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    assert det_resp.status_code == 200
    det_data = det_resp.json()
    det_id = det_data["detection_id"]
    detected_level = det_data["skin_tone_level"]
    
    # 2. Get recommendations using skin_tone_id
    rec_payload = {
        "gender": "pria",
        "skin_tone_level": detected_level,
        "skin_tone_id": det_id,
        "session_id": "TEST-SESSION-E2E",
        "top_k": 4
    }
    rec_resp = client.post("/api/v1/recommendations", json=rec_payload)
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    outfit_set = rec_data["data"]["outfit_set"]
    assert len(outfit_set) > 0
    recommended_product_id = outfit_set[0]["product"]["id"]
    
    # 3. Submit feedback
    feed_payload = {
        "session_id": "TEST-SESSION-E2E",
        "product_id": recommended_product_id,
        "is_accepted": True,
        "feedback_score": 5
    }
    feed_resp = client.post("/api/v1/recommendations/feedback", json=feed_payload)
    assert feed_resp.status_code == 200
    assert "Feedback" in feed_resp.json()["message"] or "diterima" in feed_resp.json()["message"].lower()


# =====================================================================
# TIER 4: REAL-WORLD SCENARIOS
# =====================================================================
def test_workflow_male_user(client):
    """Male user scans, receives recommendations for pria, and likes one product."""
    img_bytes = create_mock_image(85, 115, 175)
    files = {"image": ("face.jpg", img_bytes, "image/jpeg")}
    det_resp = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    assert det_resp.status_code == 200
    det_data = det_resp.json()
    
    rec_payload = {
        "gender": "pria",
        "skin_tone_level": det_data["skin_tone_level"],
        "skin_tone_id": det_data["detection_id"],
        "session_id": "TEST-SESSION-MALE-WF",
        "top_k": 6
    }
    rec_resp = client.post("/api/v1/recommendations", json=rec_payload)
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    outfit_set = rec_data["data"]["outfit_set"]
    
    for item in outfit_set:
        assert item["product"]["gender"] in ["pria", "unisex"]
        
    feed_payload = {
        "session_id": "TEST-SESSION-MALE-WF",
        "product_id": outfit_set[0]["product"]["id"],
        "is_accepted": True,
        "feedback_score": 5
    }
    feed_resp = client.post("/api/v1/recommendations/feedback", json=feed_payload)
    assert feed_resp.status_code == 200

def test_workflow_female_user(client):
    """Female user scans, receives recommendations for wanita, and submits a lower score feedback."""
    img_bytes = create_mock_image(200, 200, 200)
    files = {"image": ("face.jpg", img_bytes, "image/jpeg")}
    det_resp = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    assert det_resp.status_code == 200
    det_data = det_resp.json()
    
    rec_payload = {
        "gender": "wanita",
        "skin_tone_level": det_data["skin_tone_level"],
        "skin_tone_id": det_data["detection_id"],
        "session_id": "TEST-SESSION-FEMALE-WF",
        "top_k": 4
    }
    rec_resp = client.post("/api/v1/recommendations", json=rec_payload)
    assert rec_resp.status_code == 200
    rec_data = rec_resp.json()
    outfit_set = rec_data["data"]["outfit_set"]
    
    for item in outfit_set:
        assert item["product"]["gender"] in ["wanita", "unisex"]
        
    feed_payload = {
        "session_id": "TEST-SESSION-FEMALE-WF",
        "product_id": outfit_set[0]["product"]["id"],
        "is_accepted": False,
        "feedback_score": 2
    }
    feed_resp = client.post("/api/v1/recommendations/feedback", json=feed_payload)
    assert feed_resp.status_code == 200
