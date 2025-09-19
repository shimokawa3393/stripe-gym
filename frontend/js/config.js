// 設定ファイル - 環境変数とデフォルト値を管理
const config = {
    // Stripe設定
    stripe: {
        publishableKey: "pk_test_51RylygRls3IscnFUjyhdwRMWOlkIlmQb7snT2Zknflind45BHSO4BF2SV5hiCXgmtebxMftvNaxaHNybGUd0nQ3D00gNW6BDX3",
        priceId: "price_1S6SCHRls3IscnFU4b8BOqIe"
    },
    
    // API設定
    api: {
        checkoutEndpoint: "http://localhost:5001/api/subscription"
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
