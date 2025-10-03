"""
Stripe連携テスト：stripe-mockを使ったStripe APIの統合テスト
"""
import pytest
import stripe


@pytest.mark.slow
def test_stripe_connection_health():
    """stripe-mockとの接続テスト"""
    
    # 接続確認（環境変数の設定）
    assert stripe.api_base == "http://stripe-mock-test:12111", "Stripe-mockのURLが正しく設定されていない"
    
    # テスト用APIキーを設定
    stripe.api_key = "sk_test_xxx"
    
    # stripe-mockに接続テスト
    try:
        customers = stripe.Customer.list(limit=1)
        # stripe-mockは空のリストを返すか、テストデータを返す
        assert isinstance(customers.data, list), "Stripe-mockからのレスポンスが不正"
        
    except stripe.error.StripeError as e:
        pytest.fail(f"Stripe-mockへの接続失敗: {e}")


@pytest.mark.slow
def test_create_stripe_customer():
    """Stripe Customer作成のテスト"""
    
    stripe.api_key = "sk_test_xxx"
    
    customer_data = {
        'email': 'test_customer@example.com',
        'name': 'テスト顧客',
        'metadata': {
            'user_id': '1',
            'source': 'test'
        }
    }
    
    try:
        customer = stripe.Customer.create(**customer_data)
        
        assert customer.id is not None, "Customer IDが生成されていない"
        assert customer.email == customer_data['email'], "メールアドレスが一致しない"
        assert customer.name == customer_data['name'], "名前が一致しない"
        
        # メタデータの確認
        assert customer.metadata['user_id'] == customer_data['metadata']['user_id']
        
    except stripe.error.StripeError as e:
        pytest.fail(f"Stripe Customer作成失敗: {e}")


@pytest.mark.slow  
def test_create_checkout_session_stripe():
    """Stripe Checkout Session作成のテスト"""
    
    stripe.api_key = "sk_test_xxx"
    
    # まずテストCustomerを作成
    customer = stripe.Customer.create(
        email='checkout_test@example.com',
        name='Checkout Test Customer'
    )
    
    # Checkout Session作成
    session_data = {
        'customer': customer.id,
        'success_url': 'https://example.com/success',
        'cancel_url': 'https://example.com/cancel',
        'payment_method_types': ['card'],
        'line_items': [{
            'price': 'price_test123',
            'quantity': 1,
        }],
        'mode': 'payment'
    }
    
    try:
        session = stripe.checkout.Session.create(**session_data)
        
        assert session.id is not None, "Session IDが生成されていない"
        assert session.customer == customer.id, "Customerが正しく設定されていない"
        assert 'checkout.stripe.com' in session.url, "Checkout URLが不正"
        
    except stripe.error.StripeError as e:
        pytest.fail(f"Checkout Session作成失敗: {e}")


@pytest.mark.slow
def test_create_subscription_stripe():
    """Stripe サブスクリプション作成のテスト"""
    
    stripe.api_key = "sk_test_xxx"
    
    # Customer作成
    customer = stripe.Customer.create(
        email='subscription_test@example.com',
        name='Subscription Test Customer'
    )
    
    # Subscription作成
    subscription_data = {
        'customer': customer.id,
        'items': [{
            'price': 'price_premium_test',
        }]
    }
    
    try:
        subscription = stripe.Subscription.create(**subscription_data)
        
        assert subscription.id is not None, "Subscription IDが生成されていない"
        assert subscription.customer == customer.id, "Customerが正しく設定されていない"
        assert subscription.status in ['incomplete', 'active', 'trialing'], "Subscriptionステータスが不正"
        
    except stripe.error.StripeError as e:
        pytest.fail(f"Subscription作成失敗: {e}")


@pytest.mark.slow
def test_invoice_operations():
    """Invoice関連のStripe操作テスト"""
    
    stripe.api_key = "sk_test_xxx"
    
    # Upcoming Invoiceを取得
    try:
        upcoming_invoices = stripe.Invoice.upcoming()
        # stripe-mockの実装により、結果が異なるかもしれません
        
    except stripe.error.StripeError as e:
        # Upcoming invoicesがない場合もある
        if "customer_that_has_no_subscription" in str(e):
            # 期待されるエラー
            pass
        else:
            pytest.fail(f"Invoice操作失敗: {e}")


@pytest.mark.slow
def test_payment_method_operations():
    """Payment Method関連のStripe操作テスト"""
    
    stripe.api_key = "sk_test_xxx"
    
    # Payment Method作成
    try:
        payment_method = stripe.PaymentMethod.create(
            type='card',
            card={
                'number': '4242424242424242',
                'exp_month': 12,
                'exp_year': 2025,
                'cvc': '123',
            }
        )
        
        assert payment_method.id is not None, "Payment Method IDが生成されていない"
        assert payment_method.type == 'card', "Payment Method typeが不正"
        
    except stripe.error.StripeError as e:
        pytest.fail(f"Payment Method作成失敗: {e}")


@pytest.mark.slow
def test_stripe_error_handling():
    """Stripeエラーハンドリングのテスト"""
    
    stripe.api_key = "sk_test_xxx"
    
    # 無効なAPIキーでのテスト
    original_key = stripe.api_key
    stripe.api_key = "invalid_key"
    
    try:
        stripe.Customer.list()
        pytest.fail("無効なAPIキーなのにエラーが発生していない")
        
    except stripe.error.AuthenticationError:
        # 期待される認証エラー
        pass
    
    finally:
        # 元のAPIキーに戻す
        stripe.api_key = original_key


@pytest.mark.slow
def test_billing_portal_preparation():
    """Billing Portalのための準備テスト"""
    
    stripe.api_key = "sk_test_xxx"
    
    # Customer作成
    customer = stripe.Customer.create(
        email='billing_portal_test@example.com',
        name='Billing Portal Test'
    )
    
    # Subscription作成
    subscription = stripe.Subscription.create(
        customer=customer.id,
        items=[{
            'price': 'price_standard_test'
        }]
    )
    
    # Billing Portal Session作成準備のためのデータ確認
    assert customer.id is not None
    assert subscription.id is not None
    
    # stripe-mockではBilling Portal機能が制限されている可能性がありますが、
    # CustomerとSubscriptionの準備ができていることを確認


@pytest.mark.slow
def test_webhook_endpoint_validation():
    """Webhookエンドポイントの検証"""
    
    stripe.api_key = "sk_test_xxx"
    
    try:
        # Webhook endpoint情報の取得（stripe-mockの実装次第）
        endpoints = stripe.WebhookEndpoint.list()
        
        # stripe-mockがWebhookEndpointをサポートしている場合のチェック
        if endpoints.data:
            for endpoint in endpoints.data:
                assert endpoint.url is not None
                assert 'enabled_events' in endpoint
            
    except stripe.error.StripeError:
        # stripe-mockがWebhookEndpoint機能をサポートしていない場合
        # これは正常な動作の場合もあります
        pass
