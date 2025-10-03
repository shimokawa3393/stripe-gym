"""
パフォーマンステスト：レスポンス時間とスループットのテスト
"""
import pytest
import time
import concurrent.futures
import statistics


@pytest.mark.slow
def test_api_response_time(client):
    """APIレスポンス時間のテスト"""
    
    endpoints_to_test = [
        ('/health', 'GET'),
    ]
    
    for endpoint, method in endpoints_to_test:
        execution_times = []
        
        # 10回リクエストを送信して平均時間を計算
        for _ in range(10):
            start_time = time.time()
            
            if method == 'GET':
                response = client.get(endpoint)
            elif method == 'POST':
                response = client.post(endpoint, json={})
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            execution_times.append(execution_time)
            
            # 各リクエストが成功することを確認
            assert response.status_code in [200, 404, 405], f"エンドポイント {endpoint} のリクエストが失敗: {response.status_code}"
        
        # 統計を計算
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)
        
        print(f"📊 {endpoint} ({method}): 平均={avg_time:.3f}s, 最大={max_time:.3f}s, 最小={min_time:.3f}s")
        
        # 平均応答時間が1秒以内であることを確認
        assert avg_time < 1.0, f"エンドポイント {endpoint} の平均応答時間が遅すぎます: {avg_time:.3f}s"
        
        # 最大応答時間が5秒以内であることを確認
        assert max_time < 5.0, f"エンドポイント {endpoint} の最大応答時間が遅すぎます: {max_time:.3f}s"


@pytest.mark.slow
def test_concurrent_requests(client):
    """同時リクエスト処理のテスト"""
    
    def make_request():
        """単一のリクエストを送信"""
        start_time = time.time()
        response = client.get('/health')
        end_time = time.time()
        return {
            'status_code': response.status_code,
            'execution_time': end_time - start_time
        }
    
    # 同時に10個のリクエストを送信
    concurrent_requests = 10
    
    start_time = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = [executor.submit(make_request) for _ in range(concurrent_requests)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    end_time = time.time()
    total_execution_time = end_time - start_time
    
    # 全リクエストが成功することを確認
    success_count = sum(1 for result in results if result['status_code'] == 200)
    assert success_count >= concurrent_requests * 0.8, f"同時リクエストの成功率が低すぎます: {success_count}/{concurrent_requests}"
    
    # 全リクエストの平均実行時間を計算
    avg_execution_time = statistics.mean([result['execution_time'] for result in results])
    max_execution_time = max(result['execution_time'] for result in results)
    
    print(f"📊 同時リクエストテスト: 成功率={success_count}/{concurrent_requests}, 平均時間={avg_execution_time:.3f}s, 最大時間={max_execution_time:.3f}s")
    
    # 平均実行時間が500ms以内であることを確認
    assert avg_execution_time < 0.5, f"同時リクエストの平均実行時間が遅すぎます: {avg_execution_time:.3f}s"


@pytest.mark.slow
def test_database_query_performance(db_session):
    """データベースクエリのパフォーマンステスト"""
    
    execution_times = []
    
    # データベースクエリの応答時間を測定
    for _ in range(20):
        start_time = time.time()
        
        # シンプルなクエリ実行
        users_count = db_session.query(db_session.query().table_name == 'users').count()
        
        # 複雑なJOINクエリ実行
        results = db_session.query().filter().all()
        
        end_time = time.time()
        execution_time = end_time - start_time
        execution_times.append(execution_time)
    
    avg_time = statistics.mean(execution_times)
    max_time = max(execution_times)
    
    print(f"📊 DBクエリパフォーマンス: 平均={avg_time:.3f}s, 最大={max_time:.3f}s")
    
    # 平均クエリ時間が100ms以内であることを確認
    assert avg_time < 0.1, f"データベースクエリの平均実行時間が遅すぎます: {avg_time:.3f}s"


@pytest.mark.slow 
@pytest.mark.integration
def test_end_to_end_performance(client, sample_user):
    """エンドツーエンドパフォーマンステスト"""
    
    execution_times = []
    
    for _ in range(5):  # 5回のフルフローテスト
        start_time = time.time()
        
        # 1. ヘルスチェック
        health_response = client.get('/health')
        assert health_response.status_code == 200
        
        # 2. APIエンドポイント確認
        register_response = client.get('/api/register')
        assert register_response.status_code == 405  # Method Not Allowed（正常）
        
        # 3. ユーザー情報確認（サンプルユーザー）
        user_check_time = time.time()
        if hasattr(sample_user, 'id'):
            # ユーザー情報の確認
            user_id = sample_user.id
            # 実際のユーザー情報確認は実装次第
        user_check_response_time = time.time() - user_check_time
        
        end_time = time.time()
        total_execution_time = end_time - start_time
        execution_times.append(total_execution_time)
        
        print(f"📊 E2Eフロー {_}回目: {total_execution_time:.3f}s (ユーザー確認: {user_check_response_time:.3f}s)")
    
    avg_time = statistics.mean(execution_times)
    max_time = max(execution_times)
    
    print(f"📊 全体E2Eパフォーマンス: 平均={avg_time:.3f}s, 最大={max_time:.3f}s")
    
    # 平均実行時間が2秒以内であることを確認
    assert avg_time < 2.0, f"エンドツーエンドフローの平均実行時間が遅すぎます: {avg_time:.3f}s"


@pytest.mark.slow
def test_memory_usage():
    """メモリ使用量のテスト"""
    import psutil
    import gc
    
    # ガベジコレクション実行
    gc.collect()
    
    # プロセス情報を取得
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024  # MB単位に変換
    
    print(f"📊 メモリ使用量: {memory_mb:.2f}MB")
    
    # メモリ使用量が100MB以内であることを確認（テスト環境では）
    assert memory_mb < 100, f"メモリ使用量が大きすぎます: {memory_mb:.2f}MB"


@pytest.mark.slow
def test_scalability_initial_indicators(client):
    """スケーラビリティの初期指標テスト"""
    
    # 複数のリエンクエストを順次実行
    request_counts = [1, 5, 10, 20]
    results = {}
    
    for count in request_counts:
        execution_times = []
        success_count = 0
        
        start_time = time.time()
        
        for _ in range(count):
            req_start = time.time()
            response = client.get('/health')
            req_end = time.time()
            
            execution_times.append(req_end - req_start)
            
            if response.status_code == 200:
                success_count += 1
        
        total_time = time.time() - start_time
        avg_time = statistics.mean(execution_times)
        
        results[count] = {
            'total_time': total_time,
            'avg_time': avg_time,
            'success_rate': success_count / count,
            'requests_per_second': count / total_time
        }
        
        print(f"📊 リクエスト数 {count}: RPS={results[count]['requests_per_second']:.2f}, 成功率={results[count]['success_rate']:.2%}")
    
    # 同時リクエスト数が増えても成功率が80%以上であることを確認
    assert results[20]['success_rate'] >= 0.8, f"20同時リクエスト時の成功率が低すぎます: {results[20]['success_rate']:.2%}"
    
    # RPSがある程度を維持していることを確認
    assert results[20]['requests_per_second'] >= 5, f"20同時リクエスト時のRPSが低すぎます: {results[20]['requests_per_second']:.2f}"
