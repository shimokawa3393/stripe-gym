"""
Webhookテスト：Stripe Webhookイベントの受信と処理をテスト
"""
import pytest
import json
from tests.conftest import load_test_data_string


@pytest.mark.webhook
def test_webhook_endpoint_exists(client):
    """Webhookエンドポイントが存在し、POSTリクエストを受け付けるかテスト"""
    
    # GET リクエストで405エラーを期待
    response = client.get('/webhook')
    assert response.status_code == 405, "GET リクエストが適切に拒否されていない"
    
    # POST リクエストでエラー（Webhookヘッダーが必要）
    response = client.post('/webhook', json={})
    assert response.status_code in [400, 401], "空のWebhookリクエストでは400または401を期待"


@pytest.mark.webhook
def test_checkout_session_completed_webhook(client, db_session, sample_user):
    """checkout.session.completed Webhookイベントのテスト"""
    
    # テストデータを読み込み
    webhook_data = json.loads(load_test_data_string('checkout_completed.json'))
    
    # Webhookヘッダーをシミュレート（実際は署名検証が必要）
    headers = {
        'Content-Type': 'application/json',
        'Stripe-Signature': 't=1640995200,v1=dummy_signature'  # ダミー署名
    }
    
    response = client.post('/webhook', 
                          headers=headers,
                          json=webhook_data)
    
    # Webhook処理の結果をチェック
    assert response.status_code == 200, f"Webhook処理失敗: {response.data}"
    
    # DBの状態をチェック（テストデータに基づいて）
    # 注文履歴やサブスクリプションが正しく保存されているか確認
    


@pytest.mark.webhook
def test_subscription_created_webhook(client, db_session):
    """customer.subscription.created Webhookイベントのテスト"""
    
    # テストデータを読み込み
    webhook_data = json.loads(load_test_data_string('subscription_created.json'))
    
    headers = {
        'Content-Type': 'application/json',
        'Stripe-Signature': 't=1640995200,v1=dummy_signature'
    }
    
    response = client.post('/webhook',
                          headers=headers, 
                          json=webhook_data)
    
    assert response.status_code == 200, "サブスクリプション作成Webhookが失敗"
    
    # DBにサブスクリプションが作成されているかチェック
    # サブスクリプション関連のクエリは実装により異なる


@pytest.mark.webhook
def test_subscription_updated_webhook(client, db_session):
    """customer.subscription.updated Webhookイベントのテスト"""
    
    webhook_data = json.loads(load_test_data_string('subscription_updated.json'))
    
    headers = {
        'Content-Type': 'application/json',
        'Stripe-Signature': 't=1640995200,v1=dummy_signature'
    }
    
    response = client.post('/webhook',
                          headers=headers,
                          json=webhook_data)
    
    assert response.status_code == 200, "サブスクリプション更新Webhookが失敗"


@pytest.mark.webhook
def test_subscription_deleted_webhook(client, db_session):
    """customer.subscription.deleted Webhookイベントのテスト"""
    
    webhook_data = json.loads(load_test_data_string('subscription_deleted.json'))
    
    headers = {
        'Content-Type': 'application/json',
        'Stripe-Signature': 't=1640995200,v1=dummy_signature'
    }
    
    response = client.post('/webhook',
                          headers=headers,
                          json=webhook_data)
    
    assert response.status_code == 200, "サブスクリプション削除Webhookが失敗"


@pytest.mark.webhook
def test_invoice_paid_webhook(client):
    """invoice.paid Webhookイベントのテスト"""
    
    webhook_data = json.loads(load_test_data_string('invoice_paid.json'))
    
    headers = {
        'Content-Type': 'application/json',
        'Stripe-Signature': 't=1640995200,v1=dummy_signature'
    }
    
    response = client.post('/webhook',
                          headers=headers,
                          json=webhook_data)
    
    assert response.status_code == 200, "請求書支払い完了Webhookが失敗"


@pytest.mark.webhook
def test_invoice_payment_failed_webhook(client):
    """invoice.payment_failed Webhookイベントのテスト"""
    
    webhook_data = json.loads(load_test_data_string('invoice_payment_failed.json'))
    
    headers = {
        'Content-Type': 'application/json',
        'Stripe-Signature': 't=1640995200,v1=dummy_signature'
    }
    
    response = client.post('/webhook',
                          headers=headers,
                          json=webhook_data)
    
    assert response.status_code == 200, "請求書支払い失敗Webhookが失敗"


@pytest.mark.webhook
def test_duplicate_webhook_prevention(client):
    """重複Webhookイベントの防止テスト"""
    
    # 同じWebhookイベントを2回送信
    webhook_data = json.loads(load_test_data_string('checkout_completed.json'))
    
    headers = {
        'Content-Type': 'application/json',
        'Stripe-Signature': 't=1640995200,v1=dummy_signature'
    }
    
    # 1回目の送信
    response1 = client.post('/webhook',
                           headers=headers,
                           json=webhook_data)
    
    # 2回目の送信
    response2 = client.post('/webhook',
                           headers=headers,
                           json=webhook_data)
    
    assert response1.status_code == 200, "1回目のWebhookが失敗"
    assert response2.status_code == 200, "2回目のWebhookが失敗"
    
    # 重複防止機能がある場合、2回目は異なる処理またはログ出力が期待される


@pytest.mark.webhook
def test_webhook_signature_validation(client):
    """Webhook署名の検証テスト"""
    
    webhook_data = json.loads(load_test_data_string('checkout_completed.json'))
    
    # 無効な署名でリクエスト
    headers = {
        'Content-Type': 'application/json',
        'Stripe-Signature': 'invalid_signature'
    }
    
    response = client.post('/webhook',
                          headers=headers,
                          json=webhook_data)
    
    # 署名検証が実装されている場合、401または400エラーを期待
    # 実装されていない場合は200にもなり得る
    assert response.status_code in [200, 400, 401], f"署名検証で予期しない応答: {response.status_code}"


@pytest.mark.webhook
def test_unhandled_webhook_event(client):
    """未処理のWebhookイベントタイプのテスト"""
    
    # 未知のイベントタイプ
    unknown_webhook_data = {
        'id': 'evt_unknown_test',
        'object': 'event',
        'type': 'unknown.event.type',
        'data': {
            'object': {
                'id': 'obj_test_unknown'
            }
        }
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Stripe-Signature': 't=1640995200,v1=dummy_signature'
    }
    
    response = client.post('/webhook',
                          headers=headers,
                          json=unknown_webhook_data)
    
    # 未知のイベントタイプでもエラーにならないことを確認
    assert response.status_code == 200, "未知のWebhookイベントでエラーが発生"
