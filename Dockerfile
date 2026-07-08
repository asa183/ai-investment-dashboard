# Dockerfile for Trading Bot
FROM python:3.10-slim

# OSレベルの依存関係インストール
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# タイムゾーンを東京に設定（cronやスケジューラが正確に動くように）
ENV TZ=Asia/Tokyo

# 作業ディレクトリの作成
WORKDIR /app

# 依存関係のコピーとインストール
COPY requirements.txt .
# SQLAlchemyとpsycopg2（PostgreSQLドライバ）、scheduleを追加インストール
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir SQLAlchemy psycopg2-binary schedule

# アプリケーションコードのコピー
COPY . .

# 環境変数のデフォルト設定
ENV PYTHONUNBUFFERED=1

# 起動コマンド（デーモンとして実行）
CMD ["python", "daemon.py"]
