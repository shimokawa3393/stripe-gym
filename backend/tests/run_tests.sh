#!/bin/bash

# StripeGym テスト実行スクリプト
# 使用方法: ./run_tests.sh [オプション]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "🚀 StripeGym テストスイート実行"
echo "=================================="
echo "プロジェクトルート: $PROJECT_ROOT"
echo ""

# 引数のパース
SKIP_SLOW=false
SKIP_PERFORMANCE=false
VERBOSE=false
COVERAGE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-slow)
            SKIP_SLOW=true
            shift
            ;;
        --skip-performance)
            SKIP_PERFORMANCE=true
            shift
            ;;
        --no-coverage)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "使用法: $0 [オプション]"
            echo ""
            echo "オプション:"
            echo "  --skip-slow        時間のかかるテストをスキップ"
            echo "  --skip-performance パフォーマンステストをスキップ"
            echo "  --no-coverage      カバレッジレポートを生成しない"
            echo "  -v, --verbose      詳細ログを表示"
            echo "  -h, --help         このヘルプを表示"
            exit 0
            ;;
        *)
            echo "不明なオプション: $1"
            exit 1
            ;;
    esac
done

# Docker services起動確認
if ! docker compose ps | grep -q "Up"; then
    echo "📦 Docker services起動中..."
    docker compose up -d db
    sleep 5
fi

# pytestの引数を構築
PYTEST_REQS=""

if [ "$SKIP_SLOW" = true ]; then
    PYTEST_REQS="$PYTEST_REQS -m \"not slow\""
fi

if [ "$SKIP_PERFORMANCE" = true ]; then
    PYTEST_REQS="$PYTEST_REQS -m \"not performance\""
fi

if [ "$VERBOSE" = true ]; then
    PYTEST_REQS="$PYTEST_REQS -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_REQS="$PYTEST_REQS --cov=app --cov-report=term-missing --cov-report=html"
fi

# テスト実行
echo "🎯 テスト実行中..."

# 基本テスト
echo "1️⃣ 基本テスト"
docker compose exec app python -m pytest tests/test_hello.py tests/test_simple_api.py tests/test_basic_api.py $PYTEST_REQS

echo ""
echo "2️⃣ API統合テスト"
docker compose exec app python -m pytest tests/test_integration.py::test_api_endpoints_completeness tests/test_integration.py::test_error_handling_consistency $PYTEST_REQS

echo ""
echo "3️⃣ Webhookテスト"
if [ "$SKIP_PERFORMANCE" = false ]; then
    docker compose exec app python -m pytest tests/test_webhook_signature_bypass.py::test_webhook_with_signature_bypass_on $PYTEST_REQS
fi

echo ""
echo "4️⃣ パフォーマンステスト"
if [ "$SKIP_PERFORMANCE" = false ]; then
    docker compose exec app python -m pytest tests/test_performance.py::test_api_response_time $PYTEST_REQS
fi

echo ""
if [ "$COVERAGE" = true ]; then
    echo "📊 カバレッジレポート生成完了:"
    echo "   - ターミナル: 上記の表示"
    echo "   - HTML: backend/htmlcov/index.html"
fi

echo ""
echo "✅ すべてのテストが完了しました！"
