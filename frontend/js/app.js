// 決済関連

// Stripeライブラリの読み込みを待つ
let stripe;
document.addEventListener('DOMContentLoaded', function() {
    if (typeof Stripe !== 'undefined') {
        stripe = Stripe(window.AppConfig.stripe.publishableKey);
    } else {
        console.error('Stripeライブラリが読み込まれていません');
    }
});

// サブスクリプション購入用のcheckout関数（プレミアムプラン）
document.getElementById('subscription-button').addEventListener('click', async () => {
    await handleSubscription('premium', 'プレミアムプラン');
});

// サブスクリプション購入用のcheckout関数（スタンダードプラン）
document.getElementById('standard-subscription-button').addEventListener('click', async () => {
    await handleSubscription('standard', 'スタンダードプラン');
});

// 共通のサブスクリプション処理関数
async function handleSubscription(planType, planName) {
    // ログインチェック
    const sessionToken = localStorage.getItem('session_token');
    if (!sessionToken) {
        // 未ログインの場合はログイン画面に遷移
        window.location.href = 'login.html';
        return;
    }
    
    const button = document.getElementById(planType === 'standard' ? 'standard-subscription-button' : 'subscription-button');
    const loading = document.getElementById(planType === 'standard' ? 'loading-standard' : 'loading');
    const error = document.getElementById(planType === 'standard' ? 'error-standard' : 'error');
    
    // UI状態を更新
    button.disabled = true;
    button.textContent = '処理中...';
    loading.style.display = 'block';
    error.style.display = 'none';
    
    try {
        // セッショントークンを取得
        const headers = { 
            "Content-Type": "application/json" 
        };
        
        // ログインしている場合はAuthorizationヘッダーを追加
        if (sessionToken) {
            headers["Authorization"] = `Bearer ${sessionToken}`;
        }
        
        const response = await fetch(window.AppConfig.api.baseUrl + window.AppConfig.api.subscriptionEndpoint, {
            method: "POST",
            headers: headers,
            body: JSON.stringify({ 
                plan_name: planName,
                plan_type: planType
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
        } else if (data.already_subscribed) {
            // 既に契約している場合の警告
            alert('⚠️ 注意\n\n' + data.error + '\n\nマイページで現在の契約状況をご確認ください。');
            throw new Error(data.error);
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
}

// プロテイン購入用のcheckout関数
document.getElementById('checkout-button').addEventListener('click', async () => {
    // ログインチェック
    const sessionToken = localStorage.getItem('session_token');
    if (!sessionToken) {
        // 未ログインの場合はログイン画面に遷移
        window.location.href = 'login.html';
        return;
    }
    
    const button = document.getElementById('checkout-button');
    const loading = document.getElementById('loading-product');
    const error = document.getElementById('error-product');
    
    // UI状態を更新
    button.disabled = true;
    button.textContent = '処理中...';
    loading.style.display = 'block';
    error.style.display = 'none';
    
    try {
        // セッショントークンを取得
        const headers = { 
            "Content-Type": "application/json" 
        };
        
        // ログインしている場合はAuthorizationヘッダーを追加
        if (sessionToken) {
            headers["Authorization"] = `Bearer ${sessionToken}`;
        }
        
        const response = await fetch(window.AppConfig.api.baseUrl + window.AppConfig.api.checkoutEndpoint, {
            method: "POST",
            headers: headers,
            body: JSON.stringify({})
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
        button.textContent = '今すぐ購入';
        loading.style.display = 'none';
    }
});



// ユーザー関連

// ページ読み込み時にログイン状態を確認
document.addEventListener('DOMContentLoaded', function() {
    checkLoginStatus();
});

// ログイン状態を確認
function checkLoginStatus() {
    const sessionToken = localStorage.getItem('session_token');
    const userName = localStorage.getItem('user_name');
    
    console.log('ログイン状態確認:', { sessionToken: !!sessionToken, userName });
    
    if (sessionToken && userName) {
        // セッションの有効性を確認
        fetch(window.AppConfig.api.baseUrl + '/api/verify-session', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_token: sessionToken })
        })
        .then(response => response.json())
        .then(data => {
            console.log('セッション確認結果:', data);
            if (data.success) {
                // ログイン状態を表示
                showLoggedInState(userName);
            } else {
                // セッションが無効な場合
                console.log('セッションが無効です');
                showGuestState();
            }
        })
        .catch(error => {
            console.error('セッション確認エラー:', error);
            showGuestState();
        });
    } else {
        // 未ログイン状態を表示
        console.log('セッショントークンまたはユーザー名がありません');
        showGuestState();
    }
}

// ログイン状態を表示
function showLoggedInState(userName) {
    const guestNav = document.getElementById('guest-nav');
    const userNav = document.getElementById('user-nav');
    const userNameElement = document.getElementById('user-name');
    
    console.log('ログイン状態表示:', { guestNav: !!guestNav, userNav: !!userNav, userNameElement: !!userNameElement });
    
    if (guestNav && userNav && userNameElement) {
        guestNav.style.display = 'none';
        userNav.style.display = 'block';
        userNameElement.textContent = `こんにちは、${userName}さん`;
        console.log('ログイン状態に切り替えました');
    } else {
        console.log('ナビゲーション要素が見つかりません（このページにはナビゲーションがない可能性があります）');
    }
}

// 未ログイン状態を表示
function showGuestState() {
    const guestNav = document.getElementById('guest-nav');
    const userNav = document.getElementById('user-nav');
    
    console.log('未ログイン状態表示:', { guestNav: !!guestNav, userNav: !!userNav });
    
    if (guestNav && userNav) {
        guestNav.style.display = 'block';
        userNav.style.display = 'none';
        console.log('未ログイン状態に切り替えました');
    } else {
        console.log('ナビゲーション要素が見つかりません（このページにはナビゲーションがない可能性があります）');
    }
    
    localStorage.removeItem('session_token');
    localStorage.removeItem('user_name');
}

// ログアウト機能
function logout() {
    const sessionToken = localStorage.getItem('session_token');
    
    if (sessionToken) {
        fetch(window.AppConfig.api.baseUrl + '/api/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_token: sessionToken })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                alert('ログアウトしました');
                showGuestState();
                // ホーム画面に遷移
                window.location.href = 'home.html';
            } else {
                alert('ログアウトに失敗しました');
            }
        })
        .catch(error => {
            console.error('ログアウトエラー:', error);
            alert('ログアウト中にエラーが発生しました');
            // エラーが発生してもホーム画面に遷移
            showGuestState();
            window.location.href = 'home.html';
        });
    } else {
        showGuestState();
        // セッショントークンがない場合もホーム画面に遷移
        window.location.href = 'home.html';
    }
}
