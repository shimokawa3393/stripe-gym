#!/bin/bash
# stripe-mock停止スクリプト

set -e

echo "stopping stripe-mock..."

# stripe-mockコンテナを停止・削除
docker stop stripe-mock-test 2>/dev/null || true
docker rm stripe-mock-test 2>/dev/null || true

echo "✅ stripe-mock stopped successfully"
