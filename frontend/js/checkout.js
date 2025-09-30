// ============================================
// チェックアウト関連（決済処理）
// ============================================

// Stripeライブラリの読み込みを待つ
let stripe;
document.addEventListener('DOMContentLoaded', function() {
    if (typeof Stripe !== 'undefined') {
        stripe = Stripe(window.AppConfig.stripe.publishableKey);
    } else {
        console.error('Stripeライブラリが読み込まれていません');
    }
});

// サブスクリプション購入ボタン（プレミアムプラン）
document.addEventListener('DOMContentLoaded', function() {
    const premiumButton = document.getElementById('subscription-button');
    if (premiumButton) {
        premiumButton.addEventListener('click', async () => {
            await handleSubscription('premium', 'プレミアムプラン');
        });
    }
});

// サブスクリプション購入ボタン（スタンダードプラン）
document.addEventListener('DOMContentLoaded', function() {
    const standardButton = document.getElementById('standard-subscription-button');
    if (standardButton) {
        standardButton.addEventListener('click', async () => {
            await handleSubscription('standard', 'スタンダードプラン');
        });
    }
});

// 共通のサブスクリプション処理関数
async function handleSubscription(planType, planName) {
    const sessionToken = localStorage.getItem('session_token');
    if (!sessionToken) {
        window.location.href = 'login.html';
        return;
    }
    
    const button = document.getElementById(planType === 'standard' ? 'standard-subscription-button' : 'subscription-button');
    const loading = document.getElementById(planType === 'standard' ? 'loading-standard' : 'loading');
    const error = document.getElementById(planType === 'standard' ? 'error-standard' : 'error');
    
    button.disabled = true;
    button.textContent = '処理中...';
    loading.style.display = 'block';
    error.style.display = 'none';
    
    try {
        const headers = { 
            "Content-Type": "application/json",
            "Authorization": `Bearer ${sessionToken}`
        };
        
        const response = await fetch(window.AppConfig.api.baseUrl + window.AppConfig.api.subscriptionEndpoint, {
            method: "POST",
            headers: headers,
            body: JSON.stringify({ 
                plan_name: planName,
                plan_type: planType
            })
        });
        
        const data = await response.json();
        
        if (data.id) {
            const result = await stripe.redirectToCheckout({ 
                sessionId: data.id 
            });
            
            if (result.error) {
                throw new Error(result.error.message);
            }
        } else if (data.already_subscribed) {
            alert('⚠️ 注意\n\n' + data.error + '\n\nマイページで現在の契約状況をご確認ください。');
            throw new Error(data.error);
        } else {
            throw new Error(data.error || 'セッションの作成に失敗しました');
        }
    } catch (err) {
        console.error('エラー:', err);
        error.textContent = err.message || '決済処理中にエラーが発生しました';
        error.style.display = 'block';
        
        button.disabled = false;
        button.textContent = '今すぐ始める';
        loading.style.display = 'none';
    }
}

// プロテイン購入ボタン
document.addEventListener('DOMContentLoaded', function() {
    const checkoutButton = document.getElementById('checkout-button');
    if (checkoutButton) {
        checkoutButton.addEventListener('click', async () => {
            const sessionToken = localStorage.getItem('session_token');
            if (!sessionToken) {
                window.location.href = 'login.html';
                return;
            }
            
            const button = document.getElementById('checkout-button');
            const loading = document.getElementById('loading-product');
            const error = document.getElementById('error-product');
            
            button.disabled = true;
            button.textContent = '処理中...';
            loading.style.display = 'block';
            error.style.display = 'none';
            
            try {
                const headers = { 
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${sessionToken}`
                };
                
                const response = await fetch(window.AppConfig.api.baseUrl + window.AppConfig.api.checkoutEndpoint, {
                    method: "POST",
                    headers: headers,
                    body: JSON.stringify({})
                });
                
                const data = await response.json();
                
                if (data.id) {
                    const result = await stripe.redirectToCheckout({ 
                        sessionId: data.id 
                    });
                    
                    if (result.error) {
                        throw new Error(result.error.message);
                    }
                } else {
                    throw new Error(data.error || 'セッションの作成に失敗しました');
                }
            } catch (err) {
                console.error('エラー:', err);
                error.textContent = err.message || '決済処理中にエラーが発生しました';
                error.style.display = 'block';
                
                button.disabled = false;
                button.textContent = '今すぐ購入';
                loading.style.display = 'none';
            }
        });
    }
});

// チェックアウトセッション情報取得（成功画面用）
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('success-subscription.html') || 
        window.location.pathname.includes('success-checkout.html')) {
        loadCheckoutSessionInfo();
    }
});

function loadCheckoutSessionInfo() {
    const urlParams = new URLSearchParams(window.location.search);
    const sessionId = urlParams.get('session_id');
    
    if (!sessionId) return;
    
    console.log('決済セッションID:', sessionId);
    
    fetch(window.AppConfig.api.baseUrl + '/api/get-checkout-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.session && data.session.product_name) {
            const planNameElement = document.getElementById('plan-name-display');
            const productNameElement = document.getElementById('product-name-display');
            
            if (planNameElement) {
                planNameElement.textContent = data.session.product_name;
                planNameElement.style.color = '#667eea';
                planNameElement.style.fontWeight = 'bold';
            }
            
            if (productNameElement) {
                productNameElement.textContent = data.session.product_name;
                productNameElement.style.color = '#667eea';
                productNameElement.style.fontWeight = 'bold';
            }
        }
    })
    .catch(error => {
        console.error('セッション情報取得エラー:', error);
    });
}
