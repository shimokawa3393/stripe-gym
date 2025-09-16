FROM python:3.11-slim

WORKDIR /app

# Pythonの依存関係をインストール（psycopg2-binaryを使用してビルド依存関係を回避）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポート5000を公開
EXPOSE 5000

# アプリケーションを起動
CMD ["python", "app.py"]