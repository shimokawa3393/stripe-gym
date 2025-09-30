// ============================================
// UI補助関数
// ============================================

// ホーム画面: アクティブサブスクリプションをチェック
document.addEventListener('DOMContentLoaded', function() {
    console.log('[ui-helpers] DOMContentLoaded - pathname:', window.location.pathname);
    // ホーム画面の判定: "/" または "home.html" を含む
    const isHomePage = window.location.pathname === '/' || 
                       window.location.pathname.includes('home.html') ||
                       window.location.pathname === '/home.html';
    
    if (isHomePage) {
        console.log('[ui-helpers] ホーム画面を検出、checkActiveSubscriptions()を実行');
        checkActiveSubscriptions();
    } else {
        console.log('[ui-helpers] ホーム画面ではないため、checkActiveSubscriptions()をスキップ');
    }
});

// アクティブサブスクリプションをチェックしてUIを更新
function checkActiveSubscriptions() {
    const sessionToken = localStorage.getItem('session_token');
    
    console.log('[ui-helpers] checkActiveSubscriptions() 開始 - sessionToken:', !!sessionToken);
    
    if (!sessionToken) {
        console.log('[ui-helpers] セッショントークンなし、処理を中断');
        return; // 未ログインの場合は何もしない
    }

    // ローディング状態を表示
    showPlanLoadingState();

    // セッション検証
    fetch(window.AppConfig.api.baseUrl + '/api/verify-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_token: sessionToken })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // アクティブサブスクリプションを取得
            fetch(window.AppConfig.api.baseUrl + '/api/user-active-subscriptions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_id: data.user_id })
            })
            .then(response => response.json())
            .then(subData => {
                console.log('[ui-helpers] アクティブサブスクリプション取得成功:', subData);
                if (subData.success) {
                    updatePlanButtons(subData);
                } else {
                    console.error('[ui-helpers] サブスクリプション取得失敗:', subData);
                }
                hidePlanLoadingState();
            })
            .catch(error => {
                console.error('[ui-helpers] アクティブサブスクリプション取得エラー:', error);
                hidePlanLoadingState();
            });
        } else {
            hidePlanLoadingState();
        }
    })
    .catch(error => {
        console.error('セッション確認エラー:', error);
        hidePlanLoadingState();
    });
}

// ローディング状態を表示
function showPlanLoadingState() {
    const standardButton = document.getElementById('standard-subscription-button');
    const premiumButton = document.getElementById('subscription-button');
    
    if (standardButton) {
        standardButton.disabled = true;
        standardButton.textContent = '読み込み中...';
    }
    if (premiumButton) {
        premiumButton.disabled = true;
        premiumButton.textContent = '読み込み中...';
    }
}

// ローディング状態を解除
function hidePlanLoadingState() {
    const standardButton = document.getElementById('standard-subscription-button');
    const premiumButton = document.getElementById('subscription-button');
    
    // ボタンのテキストをリセット（updatePlanButtonsで上書きされない場合のみ）
    if (standardButton && standardButton.textContent === '読み込み中...') {
        standardButton.disabled = false;
        standardButton.textContent = '今すぐ始める';
    }
    if (premiumButton && premiumButton.textContent === '読み込み中...') {
        premiumButton.disabled = false;
        premiumButton.textContent = '今すぐ始める';
    }
}

// プランボタンの状態を更新
function updatePlanButtons(subscriptionData) {
    const standardButton = document.getElementById('standard-subscription-button');
    const premiumButton = document.getElementById('subscription-button');
    const scheduleChangeToStandardButton = document.getElementById('schedule-change-to-standard-button');
    const scheduleChangeToPremiumButton = document.getElementById('schedule-change-to-premium-button');

    if (!standardButton || !premiumButton) return;

    // アクティブなサブスクリプションのスケジュール情報をチェック
    const activeSubscription = subscriptionData.subscriptions ? subscriptionData.subscriptions[0] : null;
    const hasScheduledChange = activeSubscription && activeSubscription.scheduled_change;

    // スタンダードプランがアクティブな場合
    if (subscriptionData.has_standard) {
        // スタンダードのボタンを「利用中」表示
        standardButton.textContent = '利用中（アクティブ）';
        standardButton.disabled = true;
        standardButton.classList.add('active-plan-button');
        standardButton.style.display = 'block';
        
        // プレミアムの「今すぐ始める」ボタンを非表示
        premiumButton.style.display = 'none';
        
        // プラン変更予約の状態に応じてボタンを表示
        if (scheduleChangeToPremiumButton) {
            if (hasScheduledChange && activeSubscription.scheduled_change.next_plan_name === 'プレミアムプラン') {
                // 既にプレミアムへの変更予約がある場合
                scheduleChangeToPremiumButton.textContent = '✓ プレミアムプランへ変更予約済み';
                scheduleChangeToPremiumButton.disabled = true;
                scheduleChangeToPremiumButton.classList.add('scheduled-plan-button');
                scheduleChangeToPremiumButton.style.display = 'block';
            } else {
                // まだ変更予約がない場合
                scheduleChangeToPremiumButton.style.display = 'block';
            }
        }
    }

    // プレミアムプランがアクティブな場合
    if (subscriptionData.has_premium) {
        // プレミアムのボタンを「利用中」表示
        premiumButton.textContent = '利用中（アクティブ）';
        premiumButton.disabled = true;
        premiumButton.classList.add('active-plan-button');
        premiumButton.style.display = 'block';
        
        // スタンダードの「今すぐ始める」ボタンを非表示
        standardButton.style.display = 'none';
        
        // プラン変更予約の状態に応じてボタンを表示
        if (scheduleChangeToStandardButton) {
            if (hasScheduledChange && activeSubscription.scheduled_change.next_plan_name === 'スタンダードプラン') {
                // 既にスタンダードへの変更予約がある場合
                scheduleChangeToStandardButton.textContent = '✓ スタンダードプランへ変更予約済み';
                scheduleChangeToStandardButton.disabled = true;
                scheduleChangeToStandardButton.classList.add('scheduled-plan-button');
                scheduleChangeToStandardButton.style.display = 'block';
            } else {
                // まだ変更予約がない場合
                scheduleChangeToStandardButton.style.display = 'block';
            }
        }
    }
}
