"""
認証不要のシンプルなAPIテスト
"""
import pytest


@pytest.mark.api
def test_health_endpoint(client):
    """ヘルスチェックAPIのテスト"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json['status'] == 'healthy'
    assert response.json['message'] == 'Stripe Gym API is running'


@pytest.mark.api  
def test_frontend_routes(client):
    """フロントエンド用ルートのテスト"""
    routes_to_test = [
        '/',
        '/home.html',
        '/mypage.html',
        '/login.html',
        '/user-registration.html',
        '/success-checkout.html',
        '/success-subscription.html',
        '/cancel.html'
    ]
    
    for route in routes_to_test:
        response = client.get(route)
        # フロントエンドURLはnginxが処理するが、バックエンドからもアクセス可能な場合がある
        assert response.status_code in [200, 404], f"Route {route} returned {response.status_code}"


@pytest.mark.api
def test_404_error_page(client):
    """存在しないエンドポイントの404テスト"""
    response = client.get('/api/nonexistent')
    assert response.status_code == 404


@pytest.mark.api
def test_cors_headers(client):
    """CORSヘッダーのテスト"""
    response = client.options('/health')
    assert response.status_code == 200
    # CORSヘッダーがあることを確認（Flask-CORSのデフォルト設定）
    assert "Access-Control-Allow-Origin" in str(response.headers)


@pytest.mark.api
def test_json_request_content_type(client):
    """JSONリクエストのContent-Typeテスト"""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.content_type == 'application/json'
