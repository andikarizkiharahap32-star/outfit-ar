import pytest
from fastapi.testclient import TestClient
import pymysql
import os
from pathlib import Path

from app.main import app
from app.config.settings import get_settings

settings = get_settings()

@pytest.fixture(scope="session")
def db_connection_check():
    """Verify that the database is running and reachable."""
    try:
        conn = pymysql.connect(
            host=settings.db_host,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            port=settings.db_port,
            connect_timeout=5
        )
        conn.close()
        return True
    except Exception as e:
        pytest.fail(f"Database connection failed: {e}")

@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(scope="session", autouse=True)
def seed_test_data():
    """Seeds the database with test products before testing, and cleans them up after."""
    settings = get_settings()
    conn = pymysql.connect(
        host=settings.db_host,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        port=settings.db_port
    )
    cursor = conn.cursor()
    
    # 1. Clean up any previous test data
    cursor.execute("DELETE FROM products WHERE product_external_id LIKE 'TEST-PROD-%'")
    cursor.execute("DELETE FROM users WHERE id = 9999")
    conn.commit()
    
    # Insert test user with ID 9999 so that foreign key checks pass
    cursor.execute("INSERT INTO users (id, name, email, password_hash) VALUES (9999, 'Test User', 'test_user_9999@example.com', 'dummy_hash')")
    conn.commit()
    
    # 2. Insert test products
    test_products = [
        # Pria products
        ("TEST-PROD-001", "Kemeja Casual Pria Premium", "TestBrand", 5, "#FFFFFF", 150000.00, "products/Pria/test1.jpg", "pria"),
        ("TEST-PROD-002", "Kaos Pria Polos", "TestBrand", 6, "#000000", 75000.00, "products/Pria/test2.jpg", "pria"),
        ("TEST-PROD-003", "Celana Chino Pria", "TestBrand", 7, "#A52A2A", 250000.00, "products/Pria/test3.jpg", "pria"),
        ("TEST-PROD-004", "Sepatu Sneakers Pria", "TestBrand", 10, "#0000FF", 450000.00, "products/Pria/test4.jpg", "pria"),
        ("TEST-PROD-005", "Jaket Hoodie Casual Pria", "TestBrand", 8, "#808080", 300000.00, "products/Pria/test5.jpg", "pria"),
        # Wanita products
        ("TEST-PROD-006", "Blouse Korea Hijab Wanita", "TestBrand", 6, "#FFC0CB", 180000.00, "products/Wanita/test1.jpg", "wanita"),
        ("TEST-PROD-007", "Celana Kulot Wanita Casual", "TestBrand", 7, "#FFFFFF", 120000.00, "products/Wanita/test2.jpg", "wanita"),
        ("TEST-PROD-008", "Rok Plisket Hijab Bawahan", "TestBrand", 12, "#E74C3C", 110000.00, "products/Wanita/test3.jpg", "wanita"),
        ("TEST-PROD-009", "Sandal Teplek Wanita", "TestBrand", 11, "#FFA500", 95000.00, "products/Wanita/test4.jpg", "wanita"),
        ("TEST-PROD-010", "Kaos Casual Wanita", "TestBrand", 6, "#008000", 60000.00, "products/Wanita/test5.jpg", "wanita"),
    ]
    
    root = Path(__file__).resolve().parent.parent
    upload_pria = root / "uploads" / "products" / "Pria"
    upload_wanita = root / "uploads" / "products" / "Wanita"
    upload_pria.mkdir(parents=True, exist_ok=True)
    upload_wanita.mkdir(parents=True, exist_ok=True)
    
    # Create empty mock image files
    for i in range(1, 6):
        (upload_pria / f"test{i}.jpg").touch(exist_ok=True)
        (upload_wanita / f"test{i}.jpg").touch(exist_ok=True)
    
    # Insert products into DB
    for ext_id, name, brand, cat_id, color, price, img_url, gender in test_products:
        compat_json = '[1, 2, 3]'
        sql = """
        INSERT INTO products 
        (product_external_id, name, brand, category_id, color, price, image_url, source_platform, gender, skin_tone_compat, is_active) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'zalora', %s, %s, 1)
        """
        cursor.execute(sql, (ext_id, name, brand, cat_id, color, price, img_url, gender, compat_json))
        
    conn.commit()
    cursor.close()
    conn.close()
    
    yield
    
    # Teardown: delete test products
    conn = pymysql.connect(
        host=settings.db_host,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        port=settings.db_port
    )
    cursor = conn.cursor()
    cursor.execute("DELETE FROM products WHERE product_external_id LIKE 'TEST-PROD-%'")
    cursor.execute("DELETE FROM recommendations WHERE session_id LIKE 'TEST-SESSION-%'")
    cursor.execute("DELETE FROM skin_tone_detections WHERE image_path LIKE 'uploads/skins/scan_test-%' OR user_id = 9999")
    cursor.execute("DELETE FROM users WHERE id = 9999")
    conn.commit()
    cursor.close()
    conn.close()
    
    # Clean up physical files
    for i in range(1, 6):
        try:
            (upload_pria / f"test{i}.jpg").unlink(missing_ok=True)
            (upload_wanita / f"test{i}.jpg").unlink(missing_ok=True)
        except Exception:
            pass
