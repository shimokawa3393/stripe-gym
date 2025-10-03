#!/bin/bash
# stripe-mock起動スクリプト

set -e

# 既存のstripe-mockコンテナを停止・削除
echo "既存のstripe-mockコンテナを停止・削除中..."
docker stop stripe-mock-test 2>/dev/null || true
docker rm stripe-mock-test 2>/dev/null || true

# stripe-mockを起動
echo "起動ストripe-mock..."
docker run -d \
  --name stripe-mock-test \
  --network stripe-gym_default \
  -p 12111:12111 \
  stripe/stripe-mock:latest \
  -http-port=12111

# 起動確認
echo "stripe-mockの起動確認中..."
sleep 3

curl -f http://localhost:12111/v1/payment_methods || {
  echo "エラー: stripe-mockの起動に失敗しました"
  docker logs stripe-mock-test
  exit 1
}

echo "✅ stripe-mock started successfully"
echo "API: http://localhost:12111"
echo "Webhooks: http://localhost:12112"
echo ""
echo "テストに使用する環境変数:"
echo "export STRIPE_API_BASE_URL=http://localhost:12111"
