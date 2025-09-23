// 設定ファイル - 環境変数とデフォルト値を管理
const config = {
    // Stripe設定
    stripe: {
        publishableKey: "pk_test_51RylygRls3IscnFUjyhdwRMWOlkIlmQb7snT2Zknflind45BHSO4BF2SV5hiCXgmtebxMftvNaxaHNybGUd0nQ3D00gNW6BDX3",
        priceId: "price_1SATRTRls3IscnFUle7XPRDq"
    },
    
    // API設定
    api: {
        baseUrl: "http://localhost:5001",
        checkoutEndpoint: "/api/checkout",
        subscriptionEndpoint: "/api/subscription"
    },
    
    // アプリケーション設定
    app: {
        environment: "development",
        debug: false
    }
};

// デバッグモードの場合、設定をコンソールに出力
if (config.app.debug) {
    console.log("App Config:", config);
}

// グローバルに設定を公開
window.AppConfig = config;
