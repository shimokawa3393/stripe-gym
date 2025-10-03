"""
基本的な動作確認テスト
"""
import pytest


def test_hello_world():
    """最初のテスト：基本的な動作確認"""
    message = "hello world"
    assert message == "hello world"


def test_basic_math():
    """数学のテスト：計算確認"""
    assert 2 + 2 == 4
    assert 10 * 5 == 50
    assert 100 / 4 == 25


def test_list_operations():
    """リスト操作のテスト"""
    test_list = [1, 2, 3, 4, 5]
    assert len(test_list) == 5
    assert min(test_list) == 1
    assert max(test_list) == 5
    assert sum(test_list) == 15


@pytest.mark.unit
def test_marked_unit_test():
    """マーカー付きテスト：unitテスト"""
    value = 42
    assert isinstance(value, int)
    assert value > 0


def test_exception_handling():
    """例外処理のテスト"""
    with pytest.raises(ValueError):
        int("not_a_number")
    
    with pytest.raises(ZeroDivisionError):
        1 / 0
