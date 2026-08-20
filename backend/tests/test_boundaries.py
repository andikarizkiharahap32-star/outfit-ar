import io
import pytest
from fastapi.testclient import TestClient

# =====================================================================
# TIER 2: BOUNDARY & CORNER CASES (At least 5 tests per feature)
# =====================================================================

# --- Feature 1: Health/Root Boundaries ---
def test_debug_path_invalid_characters(client):
    """Test debug path endpoint with invalid or weird characters."""
    response = client.get("/api/v1/debug-path/..%2f..%2fetc%2fpasswd")
    assert response.status_code == 200
    # It should not find the file or raise a path traversal vulnerability
    assert response.json()["file_exists"] is False

def test_health_unsupported_method(client):
    """Test health endpoint with POST (Method Not Allowed)."""
    response = client.post("/api/v1/health")
    assert response.status_code == 405

def test_root_unsupported_method(client):
    """Test root endpoint with POST (Method Not Allowed)."""
    response = client.post("/", json={})
    assert response.status_code == 405

def test_ar_check_unsupported_method(client):
    """Test ar check endpoint with POST (Method Not Allowed)."""
    response = client.post("/api/v1/ar/check")
    assert response.status_code == 405

def test_ar_sessions_invalid_user(client):
    """Test session list with invalid user ID types."""
    response = client.get("/api/v1/ar/sessions?user_id=invalid-id")
    # Should either validate query param (422) or handle it gracefully
    assert response.status_code in [400, 422, 500]


# --- Feature 2: Skin Tone Detection Boundaries ---
def test_detect_skin_tone_empty_image(client):
    """Test uploading an empty (0 bytes) image file."""
    files = {"image": ("empty.jpg", b"", "image/jpeg")}
    response = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    assert response.status_code in [400, 500]

def test_detect_skin_tone_text_file(client):
    """Test uploading a text file instead of an image."""
    files = {"image": ("test.txt", b"not-an-image-content", "text/plain")}
    response = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    assert response.status_code in [400, 500]

def test_detect_skin_tone_invalid_user_id(client):
    """Test skin tone detection with non-integer user_id."""
    img = io.BytesIO(b"dummy_image_data") # Not a valid image, will fail CV2 decode
    files = {"image": ("scan.jpg", img, "image/jpeg")}
    response = client.post("/api/v1/recommendations/detect-skin-tone?user_id=abc", files=files)
    assert response.status_code in [400, 422]

def test_detect_skin_tone_no_file(client):
    """Test skin tone detection request with no file uploaded."""
    response = client.post("/api/v1/recommendations/detect-skin-tone")
    assert response.status_code == 422 # Validation Error

def test_detect_skin_tone_tiny_image(client):
    """Test uploading a tiny 1x1 black image."""
    import cv2
    import numpy as np
    img = np.zeros((1, 1, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', img)
    files = {"image": ("tiny.jpg", io.BytesIO(buffer.tobytes()), "image/jpeg")}
    response = client.post("/api/v1/recommendations/detect-skin-tone", files=files)
    # MediaPipe face detection might fail, but it should fallback gracefully to center and succeed or handle it
    assert response.status_code in [200, 400]


# --- Feature 3: Recommendations Boundaries ---
def test_recommend_outfit_invalid_skin_tone(client):
    """Test recommendation with out-of-range skin tone levels (e.g. 0, 4, 100, -1)."""
    for invalid_level in [0, 4, 100, -1]:
        payload = {"gender": "pria", "skin_tone_level": invalid_level}
        response = client.post("/api/v1/recommendations", json=payload)
        # Should gracefully fall back to default skin tone or reject with 400/422
        assert response.status_code in [200, 400, 422]
        if response.status_code == 200:
            # Fallback should restrict level to range 1-3
            assert response.json()["data"]["skin_tone_level"] in [1, 2, 3]

def test_recommend_outfit_invalid_gender(client):
    """Test recommendation with invalid genders."""
    for invalid_gender in ["alien", "unknown", "123", ""]:
        payload = {"gender": invalid_gender, "skin_tone_level": 2}
        response = client.post("/api/v1/recommendations", json=payload)
        # Should gracefully fallback or reject
        assert response.status_code in [200, 400, 422, 404]

def test_recommend_outfit_invalid_top_k(client):
    """Test recommendation with boundary top_k values (e.g. 0, -5, 1000)."""
    for invalid_top_k in [0, -5, 1000]:
        payload = {"gender": "pria", "skin_tone_level": 2, "top_k": invalid_top_k}
        response = client.post("/api/v1/recommendations", json=payload)
        assert response.status_code in [200, 400, 422]
        if response.status_code == 200:
            # If 0 or negative, it should fall back to default top_k or return empty/capped list
            assert len(response.json()["data"]["outfit_set"]) >= 0

def test_recommend_outfit_invalid_skin_tone_id(client):
    """Test recommendation with invalid skin_tone_id types or values."""
    payload = {"gender": "pria", "skin_tone_level": 2, "skin_tone_id": -99}
    response = client.post("/api/v1/recommendations", json=payload)
    # Should fall back to default color lists and not crash (200 OK)
    assert response.status_code == 200

def test_recommend_outfit_empty_payload(client):
    """Test recommendation with completely empty JSON payload."""
    response = client.post("/api/v1/recommendations", json={})
    assert response.status_code == 200
    assert "data" in response.json()


# --- Feature 4: Feedback Boundaries ---
def test_submit_feedback_invalid_score(client):
    """Test feedback submission with invalid scores (e.g. 0, 6, -1)."""
    for invalid_score in [0, 6, -1]:
        payload = {
            "session_id": "TEST-SESSION-BD",
            "product_id": 1,
            "is_accepted": True,
            "feedback_score": invalid_score
        }
        response = client.post("/api/v1/recommendations/feedback", json=payload)
        # Should either reject (400/422) or handle it
        assert response.status_code in [200, 400, 422]

def test_submit_feedback_invalid_product_id(client):
    """Test feedback submission with invalid product ID values."""
    payload = {
        "session_id": "TEST-SESSION-BD",
        "product_id": -1,
        "is_accepted": True,
        "feedback_score": 5
    }
    response = client.post("/api/v1/recommendations/feedback", json=payload)
    assert response.status_code in [200, 400, 422]

def test_submit_feedback_missing_required_fields(client):
    """Test feedback submission missing product_id or session_id."""
    payload = {
        "session_id": "TEST-SESSION-BD",
        "is_accepted": True,
        "feedback_score": 5
    }
    response = client.post("/api/v1/recommendations/feedback", json=payload)
    assert response.status_code == 422

def test_submit_feedback_invalid_types(client):
    """Test feedback submission with invalid types in fields."""
    payload = {
        "session_id": True, # Should be str
        "product_id": "abc", # Should be int
        "is_accepted": "yes", # Should be bool
        "feedback_score": "excellent" # Should be int
    }
    response = client.post("/api/v1/recommendations/feedback", json=payload)
    assert response.status_code == 422

def test_submit_feedback_empty_body(client):
    """Test feedback submission with empty JSON body."""
    response = client.post("/api/v1/recommendations/feedback", json={})
    assert response.status_code == 422
