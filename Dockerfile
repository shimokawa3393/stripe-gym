# ベースイメージとして公式Pythonイメージを使用
FROM python:3.11.7-slim

# 作業ディレクトリを設定
WORKDIR /app

# アプリの依存関係をコピー＆インストール（必要に応じてrequirements.txtを使用）
COPY requirements.txt ./
RUN pip install -r requirements.txt

# アプリケーションのソースコードをコピー
COPY . .

# Flaskのエントリを明示
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# 環境変数（Stripeの公開鍵・秘密鍵など）を渡すことを想定
# 本番では `docker run -e` オプションやdocker-composeで注入

# Flaskアプリを起動（本番ではGunicorn等を使用することも推奨）
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]