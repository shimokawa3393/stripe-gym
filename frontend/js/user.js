// ============================================
// ユーザー関連（認証・セッション管理）
// ============================================

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
                showLoggedInState(userName);
            } else {
                console.log('セッションが無効です');
                showGuestState();
            }
        })
        .catch(error => {
            console.error('セッション確認エラー:', error);
            showGuestState();
        });
    } else {
        console.log('セッショントークンまたはユーザー名がありません');
        showGuestState();
    }
}

// ログイン状態を表示
function showLoggedInState(userName) {
    const navButtons = document.querySelector('.nav-buttons');
    const guestNav = document.getElementById('guest-nav');
    const userNav = document.getElementById('user-nav');
    const userNameElement = document.getElementById('user-name');
    
    console.log('ログイン状態表示:', { guestNav: !!guestNav, userNav: !!userNav, userNameElement: !!userNameElement });
    
    if (guestNav && userNav && userNameElement) {
        guestNav.style.display = 'none';
        userNav.style.display = 'block';
        userNameElement.textContent = `こんにちは、${userName}さん`;
        
        // ナビゲーション全体を表示
        if (navButtons) {
            navButtons.style.visibility = 'visible';
        }
        
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
        
        // ナビゲーション全体を表示
        const navButtons = document.querySelector('.nav-buttons');
        if (navButtons) {
            navButtons.style.visibility = 'visible';
        }
        
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
                window.location.href = 'home.html';
            } else {
                alert('ログアウトに失敗しました');
            }
        })
        .catch(error => {
            console.error('ログアウトエラー:', error);
            alert('ログアウト中にエラーが発生しました');
            showGuestState();
            window.location.href = 'home.html';
        });
    } else {
        showGuestState();
        window.location.href = 'home.html';
    }
}

// ログインフォーム処理
document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const button = document.querySelector('.login-button');
            const loading = document.getElementById('loading');
            const error = document.getElementById('error');
            
            button.disabled = true;
            button.textContent = '処理中...';
            loading.style.display = 'block';
            error.style.display = 'none';
            
            try {
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData);
                
                const response = await fetch(window.AppConfig.api.baseUrl + '/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    localStorage.setItem('session_token', result.session_token);
                    localStorage.setItem('user_id', result.user_id);
                    localStorage.setItem('user_name', result.user_name);
                    localStorage.setItem('user_email', result.user_email);
                    
                    alert('ログインが完了しました！');
                    window.location.href = 'home.html';
                } else {
                    error.textContent = result.error || 'ログインに失敗しました';
                    error.style.display = 'block';
                }
            } catch (err) {
                console.error('エラー:', err);
                error.textContent = 'ログイン処理中にエラーが発生しました';
                error.style.display = 'block';
            } finally {
                button.disabled = false;
                button.textContent = 'ログイン';
                loading.style.display = 'none';
            }
        });
    }
});

// 会員登録フォーム処理
document.addEventListener('DOMContentLoaded', function() {
    const registrationForm = document.getElementById('registration-form');
    if (registrationForm) {
        registrationForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const button = document.querySelector('.registration-button');
            const loading = document.getElementById('loading');
            const error = document.getElementById('error');

            button.disabled = true;
            button.textContent = '処理中...';
            loading.style.display = 'block';
            error.style.display = 'none';

            // パスワード確認
            const password = document.getElementById('password').value;
            const confirmPassword = document.getElementById('confirm-password').value;

            if (password !== confirmPassword) {
                error.textContent = 'パスワードが一致しません';
                error.style.display = 'block';
                button.disabled = false;
                button.textContent = '会員登録';
                loading.style.display = 'none';
                return;
            }

            try {
                const formData = new FormData(e.target);
                const data = Object.fromEntries(formData);

                data.terms = data.terms === 'on';
                data.privacy = data.privacy === 'on';

                const response = await fetch(window.AppConfig.api.baseUrl + '/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    alert('会員登録が完了しました！');
                    window.location.href = 'login.html';
                } else {
                    error.textContent = result.error || '登録に失敗しました';
                    error.style.display = 'block';
                }
            } catch (err) {
                console.error('エラー:', err);
                error.textContent = '登録処理中にエラーが発生しました';
                error.style.display = 'block';
            } finally {
                button.disabled = false;
                button.textContent = '会員登録';
                loading.style.display = 'none';
            }
        });
    }
});

// ユーザー情報を表示
function displayUserInfo(userId) {
    fetch(window.AppConfig.api.baseUrl + '/api/user-info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const user = data.user;
            document.getElementById('user-name').textContent = user.name || '-';
            document.getElementById('user-email').textContent = user.email || '-';
            document.getElementById('user-phone').textContent = user.phone || '-';
            document.getElementById('user-birthdate').textContent = user.birthdate || '-';
            document.getElementById('user-created').textContent = user.created_at ? new Date(user.created_at).toLocaleDateString('ja-JP') : '-';
        } else {
            const userName = localStorage.getItem('user_name');
            const userEmail = localStorage.getItem('user_email');
            
            document.getElementById('user-name').textContent = userName || '-';
            document.getElementById('user-email').textContent = userEmail || '-';
            document.getElementById('user-phone').textContent = '-';
            document.getElementById('user-birthdate').textContent = '-';
            document.getElementById('user-created').textContent = new Date().toLocaleDateString('ja-JP');
        }
    })
    .catch(error => {
        console.error('ユーザー情報取得エラー:', error);
        const userName = localStorage.getItem('user_name');
        const userEmail = localStorage.getItem('user_email');
        
        document.getElementById('user-name').textContent = userName || '-';
        document.getElementById('user-email').textContent = userEmail || '-';
        document.getElementById('user-phone').textContent = '-';
        document.getElementById('user-birthdate').textContent = '-';
        document.getElementById('user-created').textContent = new Date().toLocaleDateString('ja-JP');
    });
}

// マイページデータ読み込み
document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.includes('mypage.html')) {
        loadUserData();
    }
});

function loadUserData() {
    const sessionToken = localStorage.getItem('session_token');
    
    if (!sessionToken) {
        alert('ログインが必要です');
        window.location.href = 'login.html';
        return;
    }

    fetch(window.AppConfig.api.baseUrl + '/api/verify-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_token: sessionToken })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            displayUserInfo(data.user_id);
            loadPurchaseHistory(data.user_id);
            loadSubscriptions(data.user_id);
        } else {
            alert('セッションが無効です');
            window.location.href = 'login.html';
        }
    })
    .catch(error => {
        console.error('セッション確認エラー:', error);
        alert('エラーが発生しました');
        window.location.href = 'login.html';
    });
}

// 購入履歴を読み込み
function loadPurchaseHistory(userId) {
    const historyContainer = document.getElementById('purchase-history');
    if (!historyContainer) return;
    
    fetch(window.AppConfig.api.baseUrl + '/api/user-purchase-history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success && data.purchases && data.purchases.length > 0) {
            historyContainer.innerHTML = data.purchases.map(purchase => `
                <div class="history-item">
                    <div class="history-item-info">
                        <div class="history-item-details">
                            <div class="history-item-title">${purchase.product_name || '商品'}</div>
                            <div class="history-item-date">${new Date(purchase.created_at).toLocaleDateString('ja-JP')}</div>
                        </div>
                        <div class="history-item-status status-completed">完了</div>
                    </div>
                </div>
            `).join('');
        } else {
            historyContainer.innerHTML = '<div class="no-data">購入履歴はありません</div>';
        }
    })
    .catch(error => {
        console.error('購入履歴取得エラー:', error);
        historyContainer.innerHTML = '<div class="no-data">購入履歴の取得に失敗しました</div>';
    });
}
