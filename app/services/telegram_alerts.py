import os, requests
def send_telegram_alert(message: str) -> bool:
    token=os.getenv('TELEGRAM_BOT_TOKEN',''); chat_id=os.getenv('TELEGRAM_CHAT_ID','')
    if not token or not chat_id: return False
    url=f'https://api.telegram.org/bot{token}/sendMessage'
    try:
        response=requests.post(url, json={'chat_id':chat_id,'text':message}, timeout=10)
        return response.status_code==200
    except Exception:
        return False
