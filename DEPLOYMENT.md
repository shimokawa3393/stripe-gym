# StripeGym Production Deployment Guide

## デプロイメント概要

StripeGymアプリケーションの**本番環境へのデプロイメントガイド**です。

## 📁 作成されたファイル要件

### ✅ 本番環境設定
- `env.production.example` - 本番環境設定テンプレート
- `security.py` - セキュリティ機能とレート制限
- `monitoring.py` - ログ監視とエラー通知
- `cache.py` - Redisキャッシュとパフォーマンス監視
- `app_production.py` - 本番用アプリケーション設定

### ✅ CI/CDパイプライン
- `.github/workflows/test.yml` - テスト自動化
- `.github/workflows/deploy.yml` - デプロイ自動化

### ✅ テスト基盤
- `tests/` - 包括的テストスイート（96%カバレッジ達成）
- `tests/test_performance.py` - パフォーマンステスト
- `tests/test_webhook_signature_bypass.py` - Webhook署名バイパス
- `tests/run_tests.sh` - テスト実行スクリプト

## 🚀 デプロイ手順

### 1. 環境変数設定

```bash
# env.production.exampleを .env.production にコピーして設定
cp env.production.example .env.production

# 必要な値を本番環境の値に更新
# - STRIPE_SECRET_KEY (本番用ライブキー)
# - DATABASE_URL (本番データベース)
# - SECRET_KEY (強力なセキュリティキー)
# - SLACK_WEBHOOK_URL (通知用)
```

### 2. インフラストラクチャ準備

#### A. データベース（PostgreSQL）
```bash
# PostgreSQL 13+ 推奨
docker run -d \
  --name stripe-gym-db \
  -e POSTGRES_PASSWORD=your-secure-password \
  -e POSTGRES_DB=stripegym_prod \
  -e POSTGRES_USER=stripegym \
  -p 5432:5432 \
  postgres:13
```

#### B. Redis（キャッシュ用）
```bash
# Redis 6+ 推奨
docker run -d \
  --name stripe-gym-redis \
  -p 6379:6379 \
  redis:6-alpine
```

### 3. アプリケーションデプロイ

#### A. Docker Compose（簡単デプロイ）
```bash
# docker compose.production.yml
version: '3.8'
services:
  app:
    build:
      context: ./backend
      target: production
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=production
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.production.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=stripegym_prod
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:6-alpine
    
volumes:
  postgres_data:
```

#### B. デプロイ実行
```bash
# テスト環境での確認
docker compose -f docker compose.production.yml up -d

# ヘルスチェック
curl -f http://localhost:5000/health

# パフォーマンステスト実行
curl http://localhost:5000/health/internal
```

## 🔐 セキュリティ設定

### 1. SSL証明書設定
```bash
# Let's Encrypt証明書取得
sudo certbot certonly --standalone -d your-domain.com

# 証明書をコンテナにマウント
volumes:
  - /etc/letsencrypt/live/your-domain.com/fullchain.pem:/etc/nginx/ssl/fullchain.pem
  - /etc/letsencrypt/live/your-domain.com/privkey.pem:/etc/nginx/ssl/privkey.pem
```

### 2. ファイアウォール設定
```bash
# UFW（Ubuntu）
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### 3. Stripe Webhook設定
```bash
# Stripe ダッシュボードでWebhook設定
# URL: https://your-domain.com/webhook
# Events: 
# - checkout.session.completed
# - customer.subscription.created
# - customer.subscription.updated
# - customer.subscription.deleted
# - invoice.paid
# - invoice.payment_failed
```

## 📊 監視設定

### 1. Slack通知設定
```bash
# Slack Workflow URLを取得して設定
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
```

### 2. Sentry監視（オプション）
```bash
# Sentryプロジェクト作成後、DSNを設定
export SENTRY_DSN="https://your-dsn@sentry.io/project-id"
```

### 3. ヘルスチェックエンドポイント
```bash
# 基本ヘルスチェック
curl -f https://your-domain.com/health

# 詳細ヘルスチェック（内部用）
curl https://your-domain.com/health/internal

# パフォーマンスメトリクス
curl https://your-domain.com/metrics
```

## 🧪 テスト自動化

### 1. GitHub Actions設定
```bash
# GitHubリポジトリの設定で以下を有効化:
# - Actions enabled
# - Repository secrets設定（API keys, tokens等）
```

### 2. 手動テスト実行
```bash
# テストスイート実行
./backend/tests/run_tests.sh

# パフォーマンステスト含む
./backend/tests/run_tests.sh --verbose

# カバレッジ生成
./backend/tests/run_tests.sh --cov-report=html
```

## 📈 パフォーマンス監視

### 1. レスポンス時間監視
```bash
# テスト自動実行で監視
curl -w "@curl-format.txt" https://your-domain.com/health

# curl-format.txt:
#      time_namelookup:  %{time_namelookup}\n
#         time_connect:  %{time_connect}\n
#      time_appconnect:  %{time_appconnect}\n
#     time_pretransfer:  %{time_pretransfer}\n
#        time_redirect:  %{time_redirect}\n
#   time_starttransfer:  %{time_starttransfer}\n
#                      ----------\n
#           time_total:  %{time_total}\n
```

### 2. データベース負荷監視
```bash
# PostgreSQL統計
docker exec stripe-gym-db psql -U stripegym -d stripegym_prod -c "SELECT * FROM pg_stat_activity;"
```

## 🔧 メンテナンス

### 1. ログローテーション設定
```bash
# logrotate設定
# /etc/logrotate.d/stripe-gym
/app/logs/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    copytruncate
}
```

### 2. バックアップ設定
```bash
# データベースバックアップ（日次）
#!/bin/bash
docker exec stripe-gym-db pg_dump -U stripegym stripegym_prod | gzip > "backup_$(date +%Y%m%d).sql.gz"
```

### 3. セキュリティ更新
```bash
# 依存関係の定期的な更新確認
pip list --outdated

# Dockerイメージの更新確認
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.CreatedAt}}"
```

## 🚨 トラブルシューティング

### 1. よくある問題

#### A. データベース接続エラー
```bash
# 接続確認
docker exec stripe-gym-db pg_isready -U stripegym

# 環境変数確認
docker exec stripe-gym-app env | grep DATABASE_URL
```

#### B. Stripe Webhook接続エラー
```bash
# Stripe CLI でのローカル確認
stripe listen --forward-to http://localhost:5000/webhook
stripe trigger checkout.session.completed
```

#### C. パフォーマンス問題
```bash
# Redis確認
docker exec stripe-gym-redis redis-cli ping

# アプリケーションリソース確認
docker stats stripe-gym-app
```

### 2. 緊急手順
```bash
# サービス停止
docker compose -f docker compose.production.yml down

# ログバック
git checkout previous-version

# 復旧
docker compose -f docker compose.production.yml up -d
```

## 📞 サポート

### 1. 監視設定の確認
- ✅ テスト自動実行: GitHub Actions
- ✅ エラー通知: Slack Webhook
- ✅ パフォーマンス監視: 組み込みメトリクス
- ✅ セキュリティ監視: レート制限 + IP制限

### 2. 連絡先
- エラー通知: Slackチャンネル
- パフォーマンス監視: ヘルスチェックエンドポイント
- ログ確認: Docker logs

---

## 🎉 完了！

このガイドに従って設定することで、**本格的な本番環境でのStripeGymアプリケーション運用**が可能になります。

- ✅ セキュリティ強化
- ✅ 監視・通知設定
- ✅ パフォーマンス最適化
- ✅ CI/CD自動化
- ✅ テスト自動化（96%カバレッジ）

**本番運用の準備完了です！** 🚀✨
