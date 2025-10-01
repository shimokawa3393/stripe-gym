// ============================================
// サブスクリプション管理
// ============================================

// プラン変更予約ボタン
document.addEventListener('DOMContentLoaded', function() {
    const scheduleChangeToStandardButton = document.getElementById('schedule-change-to-standard-button');
    if (scheduleChangeToStandardButton) {
        scheduleChangeToStandardButton.addEventListener('click', async () => {
            await handleScheduledPlanChange('standard', 'スタンダードプラン');
        });
    }
    
    const scheduleChangeToPremiumButton = document.getElementById('schedule-change-to-premium-button');
    if (scheduleChangeToPremiumButton) {
        scheduleChangeToPremiumButton.addEventListener('click', async () => {
            await handleScheduledPlanChange('premium', 'プレミアムプラン');
        });
    }
});

// プラン変更予約処理関数
async function handleScheduledPlanChange(newPlanType, newPlanName) {
    const sessionToken = localStorage.getItem('session_token');
    if (!sessionToken) {
        window.location.href = 'login.html';
        return;
    }
    
    const confirmMessage = `次回更新時に${newPlanName}に変更予約します。\n\n現在のプランは期間終了まで利用でき、次回更新時に自動的に${newPlanName}に切り替わります。\n\nよろしいですか？`;
    if (!confirm(confirmMessage)) {
        return;
    }
    
    try {
        const response = await fetch(window.AppConfig.api.baseUrl + '/api/schedule-plan-change', {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${sessionToken}`
            },
            body: JSON.stringify({ 
                new_plan_type: newPlanType
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            alert(data.message || 'プラン変更を予約しました');
            location.reload();
        } else {
            alert(data.error || 'プラン変更予約に失敗しました');
        }
    } catch (err) {
        console.error('エラー:', err);
        alert('プラン変更予約中にエラーが発生しました: ' + err.message);
    }
}

// サブスクリプション履歴を一括取得
function loadSubscriptions(userId) {
    fetch(window.AppConfig.api.baseUrl + '/api/user-subscription-history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.subscriptions) {
            displayActiveSubscription(data.subscriptions);
            displaySubscriptionHistory(data.subscriptions);
        } else {
            displayActiveSubscription([]);
            displaySubscriptionHistory([]);
        }
    })
    .catch(error => {
        console.error('サブスクリプション取得エラー:', error);
        displayActiveSubscription([]);
        displaySubscriptionHistory([]);
    });
}

// アクティブサブスクリプションを表示
function displayActiveSubscription(subscriptions) {
    const activeContainer = document.getElementById('active-subscription');
    const billingPortalSection = document.getElementById('billing-portal-section');
    
    if (!activeContainer) return;
    
    if (subscriptions && subscriptions.length > 0) {
        const activeSubscriptions = subscriptions.filter(sub => sub.status === 'active');
        
        if (activeSubscriptions.length > 0) {
            // アクティブなサブスクリプションがある場合、支払い管理ボタンを表示
            if (billingPortalSection) {
                billingPortalSection.style.display = 'block';
            }
            const html = activeSubscriptions.map(activeSubscription => {
                const periodEnd = activeSubscription.current_period_end 
                    ? new Date(activeSubscription.current_period_end * 1000).toLocaleDateString('ja-JP')
                    : '不明';
                
                const isCancelScheduled = activeSubscription.cancel_at_period_end || false;
                const hasScheduledChange = activeSubscription.scheduled_change !== null && activeSubscription.scheduled_change !== undefined;
                
                let statusBadge = '';
                let statusInfo = '';
                let actionButton = '';
                
                if (isCancelScheduled) {
                    statusBadge = '<div class="history-item-status status-cancelled">解約予定</div>';
                    statusInfo = `<div class="history-item-date" style="color: #e74c3c; font-weight: 600;">⚠️ ${periodEnd} に解約されます</div>`;
                    actionButton = `<button class="reactivate-subscription-button" onclick="reactivateSubscription('${activeSubscription.id}')">解約を取り消す</button>`;
                } else if (hasScheduledChange) {
                    const changeDate = new Date(activeSubscription.scheduled_change.change_date * 1000).toLocaleDateString('ja-JP');
                    statusBadge = '<div class="history-item-status status-active">アクティブ</div>';
                    statusInfo = `
                        <div class="history-item-date" style="color: #667eea; font-weight: 600;">次回更新日: ${periodEnd}</div>
                        <div class="history-item-date" style="color: #FF9800; font-weight: 600;">🔄 ${changeDate} に ${activeSubscription.scheduled_change.next_plan_name} へ変更予定</div>
                    `;
                    actionButton = `
                        <button class="cancel-subscription-button" onclick="cancelSubscription('${activeSubscription.id}')">解約する</button>
                        <button class="reactivate-subscription-button" onclick="cancelScheduledChange('${activeSubscription.scheduled_change.schedule_id}')" style="margin-top: 5px;">変更予約をキャンセル</button>
                    `;
                } else {
                    statusBadge = '<div class="history-item-status status-active">アクティブ</div>';
                    statusInfo = `<div class="history-item-date" style="color: #667eea; font-weight: 600;">次回更新日: ${periodEnd}</div>`;
                    actionButton = `<button class="cancel-subscription-button" onclick="cancelSubscription('${activeSubscription.id}')">解約する</button>`;
                }
                
                return `
                    <div class="history-item">
                        <div class="history-item-info">
                            <div class="history-item-details">
                                <div class="history-item-title">${activeSubscription.plan_name || activeSubscription.price_id || 'サブスクリプション'}</div>
                                <div class="history-item-date">契約日: ${new Date(activeSubscription.created_at).toLocaleDateString('ja-JP')}</div>
                                ${statusInfo}
                            </div>
                            ${statusBadge}
                        </div>
                        <div class="history-item-actions">
                            ${actionButton}
                        </div>
                    </div>
                `;
            }).join('');
            
            activeContainer.innerHTML = html;
        } else {
            activeContainer.innerHTML = '<div class="no-data">現在アクティブなサブスクリプションはありません</div>';
            // アクティブなサブスクリプションがない場合、支払い管理ボタンを非表示
            if (billingPortalSection) {
                billingPortalSection.style.display = 'none';
            }
        }
    } else {
        activeContainer.innerHTML = '<div class="no-data">現在アクティブなサブスクリプションはありません</div>';
        // サブスクリプションがない場合、支払い管理ボタンを非表示
        if (billingPortalSection) {
            billingPortalSection.style.display = 'none';
        }
    }
}

// サブスクリプション履歴を表示（過去の契約のみ）
function displaySubscriptionHistory(subscriptions) {
    const historyContainer = document.getElementById('subscription-history');
    if (!historyContainer) return;
    
    const pastSubscriptions = subscriptions ? subscriptions.filter(sub => sub.status !== 'active') : [];
    
    if (pastSubscriptions.length > 0) {
        historyContainer.innerHTML = pastSubscriptions.map(subscription => `
            <div class="history-item">
                <div class="history-item-info">
                    <div class="history-item-details">
                        <div class="history-item-title">${subscription.plan_name || subscription.price_id || 'サブスクリプション'}</div>
                        <div class="history-item-date">契約日: ${new Date(subscription.created_at).toLocaleDateString('ja-JP')}</div>
                    </div>
                    <div class="history-item-status status-cancelled">
                        ${subscription.status === 'canceled' ? 'キャンセル済み' : 
                          subscription.status === 'cancelled' ? 'キャンセル済み' : 
                          subscription.status || '不明'}
                    </div>
                </div>
            </div>
        `).join('');
    } else {
        historyContainer.innerHTML = '<div class="no-data">過去のサブスクリプション履歴はありません</div>';
    }
}

// プラン変更予約キャンセル処理
function cancelScheduledChange(scheduleId) {
    if (!confirm('プラン変更予約をキャンセルしますか？\n現在のプランがそのまま継続されます。')) {
        return;
    }

    const sessionToken = localStorage.getItem('session_token');
    
    if (!sessionToken) {
        alert('ログインが必要です');
        window.location.href = 'login.html';
        return;
    }

    fetch(window.AppConfig.api.baseUrl + '/api/cancel-scheduled-change', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ schedule_id: scheduleId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message || 'プラン変更予約をキャンセルしました');
            location.reload();
        } else {
            alert(data.error || '予約キャンセル処理中にエラーが発生しました');
        }
    })
    .catch(error => {
        console.error('予約キャンセルエラー:', error);
        alert('予約キャンセル処理中にエラーが発生しました');
    });
}

// サブスクリプション解約取り消し処理
function reactivateSubscription(subscriptionId) {
    if (!confirm('サブスクリプションの解約を取り消しますか？\n引き続きご利用いただけます。')) {
        return;
    }

    const sessionToken = localStorage.getItem('session_token');
    
    if (!sessionToken) {
        alert('ログインが必要です');
        window.location.href = 'login.html';
        return;
    }

    fetch(window.AppConfig.api.baseUrl + '/api/reactivate-subscription', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ subscription_id: subscriptionId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message || 'サブスクリプションの解約を取り消しました');
            location.reload();
        } else {
            alert(data.error || '解約取り消し処理中にエラーが発生しました');
        }
    })
    .catch(error => {
        console.error('解約取り消しエラー:', error);
        alert('解約取り消し処理中にエラーが発生しました');
    });
}

// サブスクリプション解約処理
function cancelSubscription(subscriptionId) {
    if (!confirm('サブスクリプションを解約しますか？\n現在の期間終了時にキャンセルされます。')) {
        return;
    }

    const sessionToken = localStorage.getItem('session_token');
    
    if (!sessionToken) {
        alert('ログインが必要です');
        window.location.href = 'login.html';
        return;
    }

    const cancelButton = event.target;
    const originalText = cancelButton.textContent;
    cancelButton.disabled = true;
    cancelButton.textContent = '処理中...';

    fetch(window.AppConfig.api.baseUrl + '/api/cancel-subscription', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ subscription_id: subscriptionId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(data.message || 'サブスクリプションの解約が完了しました');
            location.reload();
        } else {
            alert(data.error || '解約処理中にエラーが発生しました');
            cancelButton.disabled = false;
            cancelButton.textContent = originalText;
        }
    })
    .catch(error => {
        console.error('解約エラー:', error);
        alert('解約処理中にエラーが発生しました');
        cancelButton.disabled = false;
        cancelButton.textContent = originalText;
    });
}

// Stripe Customer Portal開始処理
function startBillingPortal() {
    const sessionToken = localStorage.getItem('session_token');
    const userId = localStorage.getItem('user_id');
    
    if (!sessionToken || !userId) {
        alert('ログインが必要です');
        window.location.href = 'login.html';
        return;
    }
    
    const button = document.getElementById('billing-portal-button');
    if (button) {
        button.disabled = true;
        button.textContent = '処理中...';
    }
    
    fetch(window.AppConfig.api.baseUrl + '/api/billing-portal/start', {
        method: 'POST',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${sessionToken}`
        },
        body: JSON.stringify({ user_id: parseInt(userId) })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.url) {
            // Stripe Customer Portalにリダイレクト
            window.location.href = data.url;
        } else {
            alert(data.error || '支払い管理画面の起動に失敗しました');
            if (button) {
                button.disabled = false;
                button.textContent = '💳 支払い管理（Stripe）';
            }
        }
    })
    .catch(error => {
        console.error('支払い管理画面起動エラー:', error);
        alert('支払い管理画面の起動中にエラーが発生しました');
        if (button) {
            button.disabled = false;
            button.textContent = '💳 支払い管理（Stripe）';
        }
    });
}
