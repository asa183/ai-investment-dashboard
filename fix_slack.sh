#!/bin/bash
# Slack URL修正スクリプト (引数で受け取る版)
if [ -z "$1" ]; then
  echo "Error: Please provide the Slack webhook secret part!"
  exit 1
fi
SECRET=$1
FULL_URL="https://hooks.slack.com/services/$SECRET"
echo "Fixing Slack Webhook URL in .env file..."
sed -i "s|^SLACK_WEBHOOK_URL=.*|SLACK_WEBHOOK_URL=$FULL_URL|" .env
echo "Restarting Trading Bot to apply new settings..."
docker compose up -d
echo "Sending test notification to Slack..."
docker exec -it ai_trading_bot python main_bot.py --summary
echo "Done! Check your Slack!"
