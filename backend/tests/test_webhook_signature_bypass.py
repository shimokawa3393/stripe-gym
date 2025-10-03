"""
Webhook署名バイパステスト：テスト環境での署名検証をスキップする設定
"""
import pytest
import json
import os
from tests.conftest import load_test_data_string


@pytest.mark.webhook
def test_webhook_with_signature_bypass_on(client):
    """Webhook署名バイパス設定がONの場合のテスト"""
    
    # テスト環境では署名バイパス設定をONにする
    original_bypass = os.environ.get('STRIPE_WEBHOOK_BYPASS_SIGNATURE', 'false')
    os.environ['STRIPE_WEBHOOK_BYPASS_SIGNATURE'] = 'true'
    
    try:
        # Webhookテストデータを読み込み
        webhook_data = json.loads(load_test_data_string('checkout_completed.json'))
        
        # 署名バイパス設定により、署名なしでも受け入れられる
        headers = {
            'Content-Type': 'application/json'
            # Stripe-Signatureヘッダーは省略（バイパス設定でOK）
        }
        
        response = client.post('/webhook', 
                              headers=headers,
                              json=webhook_data)
        
        # 署名バイパスにより200エラーを期待
        assert response.status_code == 200, f"署名バイパス設定でWebhook処理に失敗: {response.data}"
        
        print(f"✅ 署名バイパステスト成功: {response.status_code}")
        
    finally:
        # 環境変数を元に戻す
        os.environ['STRIPE_WEBHOOK_BYPASS_SIGNATURE'] = original_bypass


@pytest.mark.webhook
def test_webhook_with_signature_bypass_off(client):
    """Webhook署名バイパス設定がOFFの場合のテスト"""
    
    # 本番環境では署名バイパス設定をOFFにする
    original_bypass = os.environ.get('STRIPE_WEBHOOK_BYPASS_SIGNATURE', 'false')
    os.environ['STRIPE_WEBHOOK_BYPASS_SIGNATURE'] = 'false'
    
    try:
        # Webhookテストデータを読み込み
        webhook_data = json.loads(load_test_data_string('checkout_completed.json'))
        
        # 無効な署名でリクエスト
        headers = {
            'Content-Type': 'application/json',
            'Stripe-Signature': 'invalid_signature'  # 無効な署名
        }
        
        response = client.post('/webhook', 
                              headers=headers,
                              json=webhook_data)
        
        # 署名検証により400または401エラーを期待
        assert response.status_code in [400, 401], f"署名検証が予期しない結果: {response.status_code}"
        
        if response.json:
            error_data = response.json
            assert 'error' in error_data
            assert 'signature' in str(error_data['error']).lower() or 'signature' in str(error_data).lower()
        
        print(f"✅ 署名検証テスト成功: {response.status_code}")
        
    finally:
        # 環境変数を元に戻す
        os.environ['STRIPE_WEBHOOK_BYPASS_SIGNATURE'] = original_bypass


@pytest.mark.webhook
def test_multiple_webhook_types_with_bypass(client):
    """複数のWebhookタイプでのバイパステスト"""
    
    original_bypass = os.environ.get('STRIPE_WEBHOOK_BYPASS_SIGNATURE', 'false')
    os.environ['STRIPE_WEBHOOK_BYPASS_SIGNATURE'] = 'true'
    
    try:
        # 複数のWebhookイベントタイプをテスト
        webhook_types = [
            'checkout_completed.json',
            'subscription_created.json', 
            'subscription_updated.json',
            'subscription_deleted.json',
            'invoice_paid.json',
            'invoice_payment_failed.json'
        ]
        
        headers = {'Content-Type': 'application/json'}
        
        for webhook_file in webhook_types:
            webhook_data = json.loads(load_test_data_string(webhook_file))
            
            response = client.post('/webhook',
                                  headers=headers,
                                  json=webhook_data)
            
            # 署名バイパス設定により200エラーを期待
            assert response.status_code == 200, f"Webhook {webhook_file} が失敗: {response.status_code}"
            
            print(f"✅ {webhook_file}: {response.status_code}")
            
    finally:
        os.environ['STRIPE_WEBHOOK_BYPASS_SIGNATURE'] = original_bypass


@pytest.mark.webhook  
def test_webhook_idempotency_with_bypass(client):
    """署名バイパス下での重複Webhook防止テスト"""
    
    original_bypass = os.environ.get('STRIPE_WEBHOOK_BYPASS_SIGNATURE', 'false')
    os.environ['STRIPE_WEBHOOK_BYPASS_SIGNATURE'] = 'true'
    
    try:
        # 同じWebhookイベントを2回送信
        webhook_data = json.loads(load_test_data_string('checkout_completed.json'))
        headers = {'Content-Type': 'application/json'}
        
        # 1回目の送信
        response1 = client.post('/webhook',
                               headers=headers,
                               json=webhook_data)
        
        # 2回目の送信
        response2 = client.post('/webhook',
                               headers=headers,
                               json=webhook_data)
        
        # 両方とも200を期待
        assert response1.status_code == 200, f"1回目のWebhookが失敗: {response1.status_code}"
        assert response2.status_code == 200, f"2回目のWebhookが失敗: {response2.status_code}"
        
        print(f"✅ 重複Webhookテスト成功: 1回目={response1.status_code}, 2回目={response2.status_code}")
        
    finally:
        os.environ['STRIPE_WEBHOOK_BYPASS_SIGNATURE'] = original_bypass


@pytest.mark.webhook
def test_webhook_endpoint_validation_with_bypass(client):
    """署名バイパス下でのWebhookエンドポイント検証"""
    
    original_bypass = os.environ.get('STRIPE_WEBHOOK_BYPASS_SIGNATURE', 'false')
    os.environ['STRIPE_WEBHOOK_BYPASS_SIGNATURE'] = 'true'
    
    try:
        headers = {'Content-Type': 'application/json'}
        
        # 1. 未知のイベントタイプのテスト
        unknown_event = {
            'id': 'evt_unknown_123',
            'object': 'event',
            'type': 'unknown.event.type',
            'data': {
                'object': {'id': 'obj_unknown_123'}
            }
        }
        
        response = client.post('/webhook',
                              headers=headers,
                              json=unknown_event)
        
        assert response.status_code == 200, f"未知のイベントタイプでエラーが発生: {response.status_code}"
        
        # 2. 空のpayloadのテスト
        empty_payload = {}
        
        response = client.post('/webhook',
                              headers=headers,
                              json=empty_payload)
        
        # 空のpayloadでも400エラーは発生しない（署名バイパスしているため）
        assert response.status_code in [200, 400], f"空のpayloadで予期しない結果: {response.status_code}"
        
        print(f"✅ エンドポイント検証テスト成功")
        
    finally:
        os.environ['STRIPE_WEBHOOK_BYPASS_SIGNATURE'] = original_bypass
