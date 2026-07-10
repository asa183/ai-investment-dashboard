#!/bin/bash
# VPS自動デプロイスクリプト (Macから実行)
VPS_IP="160.251.198.130"

echo "🚀 VPSへの全自動デプロイを開始します！"
echo "※パスワードを聞かれたら、ConoHaのパスワードを入力してください。"

# 1. 必要なファイルをVPSに転送
echo "📂 設定ファイル(.env)とソースコードをVPSに送信中..."
scp -r .env setup_vps.sh root@${VPS_IP}:/root/

# 2. VPS側でセットアップを実行
echo "⚙️ VPS上で自動構築スクリプトを実行中..."
ssh root@${VPS_IP} "bash /root/setup_vps.sh && git clone https://github.com/asa183/ai-investment-dashboard.git /app/ai-investment-dashboard 2>/dev/null || true && cp /root/.env /app/ai-investment-dashboard/ && cd /app/ai-investment-dashboard && docker-compose up -d"

echo "✨ 構築がすべて完了しました！"
