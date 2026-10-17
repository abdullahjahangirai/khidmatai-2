"""
Comprehensive Test Suite for KhidmatAI:
1. NGO Multiple-Branch Management
2. Public Interactive Map Display of Approved Branches
3. Facility Claims & Operational Editing
4. Route Directions via OSRM / Straight-Line Fallback
5. Database Integrity & Data Preservation
"""

import os
import sys
import tempfile
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure backend can be imported
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND_DIR.parent))

from backend import database as db
from backend.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    # Use isolated temporary database for test suite execution
    original_db_path = db.DB_PATH
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        test_db_path = tf.name

    db.DB_PATH = Path(test_db_path)
    db.init_db()

    # Pre-seed an approved test organization and admin
    with db.get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO organizations (id, name, registration_number, email, phone, city, address, website, description, status)
            VALUES 
            ('org-test-1', 'Al-Khidmat Foundation Test', 'REG-1001', 'alkhidmat@test.org', '021-111-222-333', 'Karachi', 'Clifton Block 2', 'https://alkhidmat.org', 'Welfare NGO', 'approved'),
            ('org-test-2', 'Saylani Welfare Test', 'REG-1002', 'saylani@test.org', '021-111-444-555', 'Karachi', 'Bahadurabad', 'https://saylani.org', 'Welfare NGO', 'approved')
        """)
        # Pre-seed a test facility
        conn.execute("""
            INSERT OR REPLACE INTO facilities (id, name, category, city, address, lat, lon, phone, is_verified, is_claimed)
            VALUES ('fac-test-1', 'Jinnah Postgraduate Medical Center', 'hospital', 'Karachi', 'Rafiqui Shaheed Road', 24.8532, 67.0450, '021-99201300', 1, 0)
        """)
        conn.commit()

    yield

    # Teardown
    db.DB_PATH = original_db_path
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except Exception:
            pass


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def org_headers():
    return {"X-Org-Email": "alkhidmat@test.org"}


@pytest.fixture
def org2_headers():
    return {"X-Org-Email": "saylani@test.org"}


@pytest.fixture
def admin_headers():
    return {"X-Admin-Key": "khidmatai-admin-secret-2026"}


# ============================================================================
# 1. NGO Branch Management Tests
# ============================================================================

def test_create_branch(client, org_headers):
    """Test NGO creating a new branch (pending by default)."""
    payload = {
        "branch_name": "Al-Khidmat Clifton Branch",
        "branch_code": "AK-KHI-01",
        "address": "Block 2, Clifton",
        "city": "Karachi",
        "zone": "South",
        "lat": 24.8138,
        "lon": 67.0299,
        "phone": "021-35876543",
        "email": "clifton@alkhidmat.org",
        "opening_hours": "09:00 - 18:00",
        "services": ["Ambulance", "Dispensary", "Ration Distribution"],
        "is_headquarters": False
    }
    r = client.post("/api/org/branches", json=payload, headers=org_headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["status"] == "pending"
    assert data["branch_name"] == "Al-Khidmat Clifton Branch"
    assert data["branch_code"] == "AK-KHI-01"
    assert "Dispensary" in data["services"]
    assert "id" in data


def test_list_and_get_branch(client, org_headers):
    """Test listing own branches and getting a specific branch."""
    r = client.get("/api/org/branches", headers=org_headers)
    assert r.status_code == 200
    branches = r.json().get("branches", [])
    assert len(branches) >= 1
    branch_id = branches[0]["id"]

    # Get single branch
    r_single = client.get(f"/api/org/branches/{branch_id}", headers=org_headers)
    assert r_single.status_code == 200
    assert r_single.json()["id"] == branch_id


def test_update_branch(client, org_headers):
    """Test editing branch details."""
    r = client.get("/api/org/branches", headers=org_headers)
    branch_id = r.json()["branches"][0]["id"]

    update_payload = {
        "phone": "021-35879999",
        "opening_hours": "24/7 Emergency",
        "services": ["Ambulance", "Dispensary", "Emergency Response"]
    }
    r_up = client.put(f"/api/org/branches/{branch_id}", json=update_payload, headers=org_headers)
    assert r_up.status_code == 200
    assert r_up.json()["phone"] == "021-35879999"
    assert r_up.json()["opening_hours"] == "24/7 Emergency"


def test_cross_org_isolation(client, org2_headers, org_headers):
    """Test that Org B cannot view, modify, or delete Org A's branch."""
    # Get Org A's branch ID
    r_a = client.get("/api/org/branches", headers=org_headers)
    branch_id_a = r_a.json()["branches"][0]["id"]

    # Org B attempts to get Org A's branch
    r_get = client.get(f"/api/org/branches/{branch_id_a}", headers=org2_headers)
    assert r_get.status_code == 404

    # Org B attempts to update Org A's branch
    r_put = client.put(f"/api/org/branches/{branch_id_a}", json={"phone": "000"}, headers=org2_headers)
    assert r_put.status_code == 404

    # Org B attempts to delete Org A's branch
    r_del = client.delete(f"/api/org/branches/{branch_id_a}", headers=org2_headers)
    assert r_del.status_code == 404


# ============================================================================
# 2. Admin Moderation & Public Map Tests
# ============================================================================

def test_admin_branch_moderation_and_public_map(client, admin_headers, org_headers):
    """Test admin reviewing, approving, rejecting, suspending branches, and map filtering."""
    # List pending branches
    r = client.get("/api/admin/branches?status=pending", headers=admin_headers)
    assert r.status_code == 200
    pending_branches = r.json().get("branches", [])
    assert len(pending_branches) >= 1
    branch_id = pending_branches[0]["id"]

    # Before approval, public map should NOT return this pending branch
    r_map = client.get("/api/branches")
    assert r_map.status_code == 200
    map_ids = [b["id"] for b in r_map.json().get("branches", [])]
    assert branch_id not in map_ids

    # Admin approves branch
    r_app = client.post(f"/api/admin/branches/{branch_id}/approve", json={"review_notes": "All documents verified"}, headers=admin_headers)
    assert r_app.status_code == 200
    assert r_app.json()["status"] == "approved"

    # Now public map MUST include this approved branch
    r_map2 = client.get("/api/branches")
    assert r_map2.status_code == 200
    map_ids2 = [b["id"] for b in r_map2.json().get("branches", [])]
    assert branch_id in map_ids2

    # Admin suspends branch
    r_susp = client.post(f"/api/admin/branches/{branch_id}/suspend", json={"review_notes": "Temporary audit"}, headers=admin_headers)
    assert r_susp.status_code == 200
    assert r_susp.json()["status"] == "suspended"

    # Public map should NO LONGER return the suspended branch
    r_map3 = client.get("/api/branches")
    map_ids3 = [b["id"] for b in r_map3.json().get("branches", [])]
    assert branch_id not in map_ids3

    # Re-approve for downstream tests
    client.post(f"/api/admin/branches/{branch_id}/approve", headers=admin_headers)


# ============================================================================
# 3. Facility Claims & Claimed Facility Operational Editing
# ============================================================================

def test_facility_claim_lifecycle(client, org_headers, admin_headers):
    """Test submitting facility claim, duplicate prevention, and admin approval."""
    # Submit claim for fac-test-1
    claim_payload = {
        "facility_id": "fac-test-1",
        "authority_proof": "Official hospital administration agreement with Sindh Health Dept.",
        "official_phone": "021-99201300",
        "official_email": "admin@jpmc.gov.pk",
        "document_urls": ["https://alkhidmat.org/docs/mou_jpmc.pdf"]
    }
    r = client.post("/api/org/claims", json=claim_payload, headers=org_headers)
    assert r.status_code == 200, r.text
    claim = r.json()
    assert claim["status"] == "pending"
    assert claim["facility_id"] == "fac-test-1"
    claim_id = claim["id"]

    # Duplicate prevention: submit second claim for the same facility while pending
    r_dup = client.post("/api/org/claims", json=claim_payload, headers=org_headers)
    assert r_dup.status_code == 400
    assert "already have an active" in r_dup.json()["detail"].lower()

    # List claims in NGO portal
    r_list = client.get("/api/org/claims", headers=org_headers)
    assert r_list.status_code == 200
    assert any(c["id"] == claim_id for c in r_list.json().get("claims", []))

    # Admin reviews and approves claim
    r_app = client.post(f"/api/admin/claims/{claim_id}/approve", json={"review_notes": "MOU verified with Health Dept."}, headers=admin_headers)
    assert r_app.status_code == 200
    assert r_app.json()["status"] == "approved"

    # Verify facility claimed status in database
    fac = db.get_facility_by_id("fac-test-1")
    assert fac is not None
    assert fac["is_claimed"] == 1
    assert fac["claimed_by_org_id"] == "org-test-1"


def test_claimed_facility_operational_update(client, org_headers, org2_headers):
    """Test authorized NGO updating operational details on claimed facility, and unauthorized rejection."""
    # Org A (authorized owner) updates operational fields
    update_data = {
        "phone": "021-99201399",
        "address": "Rafiqui Shaheed Road, Cantt, Karachi",
        "zone": "District South",
        "opening_hours": "24 Hours Emergency",
        "website": "https://jpmc.gov.pk"
    }
    r = client.put("/api/org/facilities/fac-test-1", json=update_data, headers=org_headers)
    assert r.status_code == 200
    assert r.json()["phone"] == "021-99201399"
    assert r.json()["zone"] == "District South"

    # Org B (not owner) tries to edit this facility -> rejected with 403
    r_unauth = client.put("/api/org/facilities/fac-test-1", json=update_data, headers=org2_headers)
    assert r_unauth.status_code == 403


# ============================================================================
# 4. Route Directions & Navigation Endpoint Tests
# ============================================================================

def test_routing_directions_endpoint(client):
    """Test route calculation with valid coordinates and error handling."""
    # Routing between two points in Karachi
    r = client.get("/api/routing/directions?origin_lat=24.8607&origin_lon=67.0011&dest_lat=24.8715&dest_lon=67.0222")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["code"] == "Ok"
    assert "distance_km" in d and d["distance_km"] > 0
    assert "duration_min" in d and d["duration_min"] > 0
    assert "polyline" in d and len(d["polyline"]) >= 2
    assert "mode" in d
    assert isinstance(d["polyline"][0], list) and len(d["polyline"][0]) == 2

    # Test coordinate validation: invalid latitude > 90
    r_inv = client.get("/api/routing/directions?origin_lat=95.0&origin_lon=67.0011&dest_lat=24.8715&dest_lon=67.0222")
    assert r_inv.status_code == 400
    assert "Invalid latitude" in r_inv.json()["detail"]


# ============================================================================
# 5. Database Integrity & Existing Data Preservation Tests
# ============================================================================

def test_live_database_integrity():
    """Verify that the primary khidmatai.db has all existing records intact."""
    live_db_path = BACKEND_DIR.parent / "khidmatai.db"
    assert live_db_path.exists(), "Primary khidmatai.db must exist"

    conn = sqlite3.connect(str(live_db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Programs count
    cursor.execute("SELECT COUNT(*) as cnt FROM programs")
    programs_count = cursor.fetchone()["cnt"]
    assert programs_count == 42, f"Expected 42 programs, found {programs_count}"

    # Organizations count
    cursor.execute("SELECT COUNT(*) as cnt FROM organizations")
    orgs_count = cursor.fetchone()["cnt"]
    assert orgs_count >= 1, f"Expected at least 1 organization, found {orgs_count}"

    # Facilities count (must include pre-existing universities and hospitals)
    cursor.execute("SELECT COUNT(*) as cnt FROM facilities")
    facilities_count = cursor.fetchone()["cnt"]
    assert facilities_count >= 6, f"Expected at least 6 facilities, found {facilities_count}"

    # Verify tables exist: branches, facility_claims, org_sessions
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('branches', 'facility_claims', 'org_sessions')")
    found_tables = {row["name"] for row in cursor.fetchall()}
    assert found_tables == {"branches", "facility_claims", "org_sessions"}, f"Missing tables: {found_tables}"

    conn.close()
