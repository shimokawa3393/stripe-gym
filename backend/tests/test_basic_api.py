"""
認証が必要なAPIテスト（改良版）
"""
import pytest
import json
# from auth import create_session_token  # 認証ヘルパーのインポートが必要


@pytest.mark.api  
def test_auth_endpoints_exist(client):
    """認証関連エンドポイントが存在するかテスト"""
    # GET リクエストで405を期待（POSTが必要なエンドポイントの確認）
    auth_routes = ['/api/register', '/api/login']
    
    for route in auth_routes:
        response = client.get(route)
        assert response.status_code == 405, f"Route {route} should return 405 (Method Not Allowed), got {response.status_code}"


@pytest.mark.api
def test_user_registration_api_structure(client):
    """ユーザー登録APIの構造テスト"""
    user_data = {
        'email': 'test@example.com',
        'password': 'password123',
        'name': 'テストユーザー',
        'terms': True,
        'privacy': True
    }
    
    response = client.post('/api/register', json=user_data)
    # APIが存在し、適切な形式でレスポンスを返すことを確認
    assert response.status_code != 404, "API endpoint not found"
    
    if response.status_code == 200:
        data = response.json
        assert 'success' in data or 'message' in data


@pytest.mark.api
def test_payment_endpoints_exist(client):
    """支払い関連エンドポイントが存在するかテスト"""
    # GET リクエストで405を期待（POSTが必要）
    response = client.get('/api/checkout')
    assert response.status_code in [405, 401], f"Should return 405 or 401 for GET request, got {response.status_code}"


@pytest.mark.api
def test_webhook_endpoint_exists(client):
    """Webhookエンドポイントが存在するかテスト"""
    # GET リクエストで405を期待（POSTが必要）
    response = client.get('/webhook')
    assert response.status_code == 405, f"Should return 405 for GET request, got {response.status_code}"

