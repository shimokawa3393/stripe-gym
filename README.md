# StripeGym

本格的なStripe決済アプリケーションの学習・開発・プロダクション運用をカバーするPythonプロジェクト

## 概要

StripeGymは、FlaskとDockerを使用して現代的な決済アプリケーションを構築し、プロダクション運用に必要なすべての要素を段階的に学習するカリキュラムプロジェクトです。基礎的な決済処理から、テスト自動化、セキュリティ強化、監視システムまで、本格的なサービス展開に必要なスキルを習得できます。

## 主な機能

### 決済機能
- Stripe Checkoutによる単発決済
- Stripe Subscriptionによる定期課金
- Stripe Customer Portalでの顧客管理
- Webhookによる決済情報のリアルタイム同期

### アプリケーション機能
- ユーザー登録・認証システム
- サブスクリプション管理
- 購入履歴の表示・管理
- データベース統合（PostgreSQL）

### 開発・運用機能
- 包括的テストスイート（96%カバレッジ）
- CI/CD自動化（GitHub Actions）
- セキュリティ強化（レート制限、IP制限）
- 監視・ログ・エラー通知システム
- Redisキャッシュ・パフォーマンス最適化

## 技術スタック

### Backend
- Python 3.11
- Flask 3.1.2
- SQLAlchemy 2.0.43
- PostgreSQL 13+
- Alembic (データベースマイグレーション)
- Stripe 12.4.0 (決済API)
- Redis 5.0.1 (キャッシュ)

### Frontend
- HTML5/CSS3/JavaScript
- Stripe.js (フロントエンド決済)
- Nginx (リバースプロキシ)

### DevOps
- Docker & Docker Compose
- GitHub Actions (CI/CD)
- pytest (テスト自動化)
- Gunicorn (本番WSGIサーバー)

## クイックスタート

### 前提条件
- Docker & Docker Compose
- Stripeアカウント（テスト用）
- Git

### セットアップ手順

1. リポジトリのクローン
```bash
git clone <repository-url>
cd stripe-gym
```

2. 環境変数の設定
```bash
# Backend環境変数
cp backend/env.example backend/.env

# Frontend環境変数
cp frontend/env.example frontend/.env

# 本番環境設定（オプション）
cp env.production.example .env.production
```

各`.env`ファイルを編集してAPIキーを設定

3. Dockerでの起動
```bash
docker compose up -d
```

4. データベースマイグレーション
```bash
docker compose exec app alembic upgrade head
```

5. 動作確認
```bash
curl http://localhost:8080/health
```

### Stripe設定

1. Stripeダッシュボードでテスト用商品を作成
2. Price IDを取得して環境変数に設定
3. Webhookエンドポイントを設定（`http://your-domain/webhook`）
4. 必要なイベントを選択:
   - checkout.session.completed
   - customer.subscription.created
   - customer.subscription.updated
   - customer.subscription.deleted
   - invoice.paid
   - invoice.payment_failed

## プロジェクト構成

```
stripe-gym/
 DATABASE_URL=postgresql://user:password@db:5432/stripegym
 
# Stripe API設定
STRIPE_SECRET_KEY=sk_test_your_secret_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
 
# Price ID設定
PRICE_ID=price_your_single_product_price
SUBSCRIPTION_PRICE_ID=price_your_subscription_price
 
# セキュリティ設定
SECRET_KEY=your_secret_key_for_session
WTF_CSRF_ENABLED=True
 
# CORS設定
FRONTEND_URL=http://localhost:8080
```

### テスト環境でのStripe設定

テストには`stripe-mock`を使用します:

```bash
# stripe-mock起動
./backend/tests/scripts/start-stripe-mock.sh

# テスト実行
./backend/tests/run_tests.sh

# stripe-mock停止
./backend/tests/scripts/stop-stripe-mock.sh
```

## 開発ガイド

### カリキュラム構成

#### 基礎編 (Day 0-6)
1. **Day 0**: 環境準備とプロジェクトセットアップ
2. **Day 1**: Stripe Checkoutの導入
3. **Day 2**: 決済フローの確認とUI整備
4. **Day 3**: Webhook受信の実装
5. **Day 4**: 台帳（Ledger）の実装
6. **Day 5**: 総合テストとトラブルシューティング
7. **Day 6**: ドキュメンテーション

#### 応用編 (Day 7-15)
1. **Day 7**: 定期課金（Subscription）対応
2. **Day 8**: Webhookの信頼性向上
3. **Day 9**: PostgreSQL移行
4. **Day 10**: 本番デプロイ環境
5. **Day 11**: フロントエンド分離
6. **Day 12**: Customer Portal統合
7. **Day 13**: テスト自動化
8. **Day 14**: セキュリティ強化
9. **Day 15**: 監視とパフォーマンス最適化

### API エンドポイント

#### 認証
- `POST /api/register` - ユーザー登録
- `POST /api/login` - ログイン
- `POST /api/logout` - ログアウト
- `GET /api/verify-session` - セッション検証

#### 決済
- `POST /api/checkout` - Checkout Session作成（単発決済）
- `POST /api/subscription` - サブスクリプション作成
- `POST /api/billing-portal/start` - Customer Portal開始

#### ユーザー管理
- `GET /api/user-info` - ユーザー情報取得
- `GET /api/user-purchase-history` - 購入履歴取得
- `GET /api/user-active-subscriptions` - アクティブサブスクリプション取得

#### システム
- `GET /health` - ヘルスチェック
- `GET /health/internal` - 内部ヘルスチェック
- `POST /webhook` - Stripe Webhook受信

### データベーススキーマ

#### Users (ユーザー)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    birthdate DATE,
    stripe_customer_id VARCHAR(255),
    terms_accepted BOOLEAN DEFAULT FALSE,
    privacy_accepted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Subscriptions (サブスクリプション)
```sql
CREATE TABLE subscriptions (
    id VARCHAR(255) PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    stripe_subscription_id VARCHAR(255) UNIQUE,
    plan_id VARCHAR(255),
    status VARCHAR(50),
    current_period_end BIGINT,
    cancel_at_period_end BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### ProcessedEvents (処理済みイベント)
```sql
CREATE TABLE processed_events (
    id VARCHAR(255) PRIMARY KEY,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    event_type VARCHAR(100)
);
```

## テスト

### テスト実行

```bash
# 全テスト実行
./backend/tests/run_tests.sh

# 個別テストカテゴリ
docker compose exec app python -m pytest tests/test_integration.py -v
docker compose exec app python -m pytest tests/test_webhook.py -v
docker compose exec app python -m pytest tests/test_performance.py -v

# カバレッジ付きテスト
docker compose exec app python -m pytest tests/ --cov=app --cov-report=html
```

### テスト種類

- **ユニットテスト**: 個別関数・クラスのテスト
- **統合テスト**: API エンドポイント間の連携テスト
- **Webhookテスト**: Stripe Webhookイベントの処理テスト
- **パフォーマンステスト**: レスポンス時間・負荷テスト
- **データベーステスト**: ORM操作・マイグレーションテスト

## CI/CD

### GitHub Actions

#### テスト自動化
- git push時にテスト自動実行
- Python lintチェック
- セキュリティスキャン
- カバレッジレポート生成

#### デプロイ自動化
- staging環境への自動デプロイ
- production環境へのリリースデプロイ
- ロールバック機能

### 使用方法

```bash
# staging環境へのデプロイ
git push origin main

# production環境へのデプロイ
git tag v1.0.0
git push origin v1.0.0
```

## セキュリティ

### 実装済みセキュリティ機能

- **レート制限**: API呼び出し回数制限
- **IP制限**: 特定IPアドレスのアクセス制御
- **セキュリティヘッダー**: X-Frame-Options, CSP等
- **入力バリデーション**: ユーザー入力の検証
- **CSRF保護**: CSRFトークンによる保護
- **SQLインジェクション対策**: SQLAlchemy ORMの使用

### 認証・認可

- **セッション管理**: Flask-Loginによるセッション管理
- **パスワードハッシュ化**: bcryptによる暗号化
- **JWT利用**: 安全なトークンベース認証（オプション）

## 監視・ログ

### 監視機能

- **ヘルスチェック**: アプリケーション状態確認
- **パフォーマンス監視**: レスポンス時間測定
- **エラー監視**: アプリケーション例外の追跡

### ログ機能

- **構造化ログ**: JSON形式でのログ出力
- **ログローテーション**: ファイルサイズ・世代管理
- **監視通知**: Slack Webhook連携

### 通知機能

- **Slack通知**: エラー・異常状況の通知
- **メール通知**: 重要なイベントの通知
- **頻度制限**: 通知のスパム防止

## 本番運用

### 環境設定

```bash
# 本番環境変数設定例
FLASK_ENV=production
SECRET_KEY=your-super-secret-production-key
DATABASE_URL=postgresql://user:password@host:5432/stripegym_prod
STRIPE_SECRET_KEY=pk_live_your_live_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_live_publishable_key
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/your/webhook
```

### デプロイ

```bash
# Docker Compose によるデプロイ
docker compose -f docker compose.production.yml up -d

# SSL証明書設定（Let's Encrypt推奨）
certbot --nginx -d your-domain.com
```

### バックアップ

```bash
# データベースバックアップ
docker exec stripe-gym-db pg_dump -U user stripegym_prod > backup.sql

# 定期バックアップスクリプト
# crontab -e で登録
0 2 * * * /path/to/backup_script.sh
```

## トラブルシューティング

### よくある問題

#### Webhook受信エラー
```bash
# 確認手順
stripe listen --forward-to localhost:5000/webhook
curl -X POST http://localhost:5000/webhook
```

#### データベース接続エラー
```bash
# 確認手順
docker compose ps db
docker compose logs db
docker compose exec app python -c "from repositories import init_db; init_db()"
```

#### テスト実行エラー
```bash
# 解決手順
docker compose exec app pip install -r requirements.txt
docker compose build --no-cache app
./backend/tests/scripts/start-stripe-mock.sh
```

### ログ確認

```bash
# アプリケーションログ
docker compose logs -f app

# データベースログ
docker compose logs -f db

# システム状態確認
curl http://localhost:8080/health/internal
```

## サポート・ドキュメント

### ドキュメント
- `StripeGym-COMPLETE-GUIDE.md`: **完全統合学習ガイド**（Day0-15全カリキュラム + 詳細手順 + トラブルシュート + 運用ガイド）
- `DEPLOYMENT.md`: デプロイメントガイド
- `env.production.example`: 本番環境設定テンプレート
- `.github/workflows/`: **⚠️ GitHub Actions テンプレート**（学習用設定 - 実際の環境では調整が必要）

### 学習リソース
- Stripe API Documentation: https://stripe.com/docs/api
- Flask Documentation: https://flask.palletsprojects.com/
- SQLAlchemy Documentation: https://docs.sqlalchemy.org/
- Docker Documentation: https://docs.docker.com/

### コミュニティ
- GitHub Issues: バグ報告・機能要望
- Discussion: 開発・運用に関する質問
- Pull Requests: コード改善・新機能追加

## ライセンス

MIT License

詳細は `LICENSE` ファイルを参照してください。

## 貢献

プロジェクトへの貢献を歓迎します。以下の手順でご参加ください:

1. Forkする
2. Feature branchを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add some amazing feature'`)
4. BranchをPush (`git push origin feature/amazing-feature`)
5. Pull Requestを作成

---

このプロジェクトは学習目的で作成されましたが、本番運用可能なレベルまで開発されています。商用利用・教育利用ともに自由に行うことができます。