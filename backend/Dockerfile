FROM python:3.11-slim

WORKDIR /app

# Pythonの依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# テスト用依存関係をインストール
COPY requirements-test.txt .
RUN pip install --no-cache-dir -r requirements-test.txt

# アプリケーションコードをコピー
COPY . .

# 非rootユーザーを作成
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app
USER appuser

# ポート5000を公開
EXPOSE 5000

# アプリケーションを起動
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]