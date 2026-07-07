import requests
import json
import config

def send_slack_notification(message: str):
    """Slackへ通知を送信する"""
    if not config.SLACK_WEBHOOK_URL or config.SLACK_WEBHOOK_URL == "YOUR_SLACK_WEBHOOK_URL":
        print(f"[Slack Notification Suppressed] {message}")
        return

    payload = {"text": message}
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
