#!/bin/bash
# Slack URL修正スクリプト
echo "Fixing Slack Webhook URL in .env file..."
sed -i 's|^SLACK_WEBHOOK_URL=.*|SLACK_WEBHOOK_URL=https://hooks.slack.com/services/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|' .env
echo "Restarting Trading Bot..."
docker compose restart trading-bot
echo "Sending test notification to Slack..."
docker exec -it ai_trading_bot python main_bot.py --summary
echo "Done! Check your Slack!"
