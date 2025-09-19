// 設定からStripeの公開可能キーを取得
const stripe = Stripe(window.AppConfig.stripe.publishableKey);

document.getElementById('subscription-button').addEventListener('click', async () => {
    const button = document.getElementById('subscription-button');
    const loading = document.getElementById('loading');
    const error = document.getElementById('error');
    
    // UI状態を更新
    button.disabled = true;
    button.textContent = '処理中...';
    loading.style.display = 'block';
    error.style.display = 'none';
    
    try {
        const response = await fetch(window.AppConfig.api.checkoutEndpoint, {
            method: "POST",
            headers: { 
                "Content-Type": "application/json" 
            },
            body: JSON.stringify({ 
                price_id: window.AppConfig.stripe.priceId // 設定から価格IDを取得
            })
        });
        console.log(response);
        const data = await response.json();
        console.log(data);
        
        if (data.id) {
            // Stripeのチェックアウトページにリダイレクト
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
        
        // UI状態をリセット
        button.disabled = false;
        button.textContent = '今すぐ始める';
        loading.style.display = 'none';
    }
});
