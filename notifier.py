import requests
import json
import config

def send_slack_notification(message: str):
    """Slackへ通知を送信する（文字数制限の回避付き）"""
    if not config.SLACK_WEBHOOK_URL or config.SLACK_WEBHOOK_URL == "YOUR_SLACK_WEBHOOK_URL":
        print(f"[Slack Notification Suppressed] {message[:100]}...")
        return

    # SlackのWebhookの文字数上限を考慮して分割 (約3000文字)
    chunk_size = 3000
    for i in range(0, len(message), chunk_size):
        chunk = message[i:i + chunk_size]
        payload = {"text": chunk}
        try:
            response = requests.post(
                config.SLACK_WEBHOOK_URL,
                data=json.dumps(payload),
                headers={'Content-Type': 'application/json'}
            )
            if response.status_code != 200:
                print(f"Failed to send Slack message. Status: {response.status_code}, Response: {response.text}")
        except Exception as e:
            print(f"Error sending Slack message: {e}")
