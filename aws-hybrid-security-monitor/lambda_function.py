import json
import urllib3
import os
import boto3
import time
import re
import ipaddress
from datetime import datetime, timedelta

http = urllib3.PoolManager()
logs_client = boto3.client('logs')

def convert_to_wib(utc_time_str):
    # Mengubah format AWS ke Jam WIB (Tanpa Tanggal biar hemat tempat)
    try:
        clean_time = utc_time_str.split('.')[0]
        dt_utc = datetime.strptime(clean_time, "%Y-%m-%d %H:%M:%S")
        dt_wib = dt_utc + timedelta(hours=7)
        return dt_wib.strftime("%H:%M:%S") 
    except:
        return utc_time_str[11:19]

def get_geolocation(ip):
    # Mengambil Negara & Kota + Link Google Maps
    try:
        try:
            if ipaddress.ip_address(ip).is_private: return "🏠 LAN (Local)"
        except: pass
        
        url = f"http://ip-api.com/json/{ip}?fields=countryCode,city,isp"
        resp = http.request('GET', url, timeout=1.0)
        if resp.status == 200:
            data = json.loads(resp.data.decode('utf-8'))
            city = data.get('city', '-')
            country = data.get('countryCode', '-')
            isp = data.get('isp', '-')
            # Format: Jakarta, ID (Biznet)
            return f"{city}, {country} ({isp})"
        return "Unknown"
    except: return "Error"

def lambda_handler(event, context):
    print("--- START PREMIUM NOTIFICATION ---")
    
    BOT_TOKEN = os.environ.get('BOT_TOKEN')
    CHAT_ID = os.environ.get('CHAT_ID')
    LOG_GROUP_NAME = "Hybrid-Server-Logs" 
    
    # 1. Parsing Status Alarm
    try:
        sns_msg = event['Records'][0]['Sns']['Message']
        alarm = json.loads(sns_msg)
        new_state = alarm.get('NewStateValue', 'ALARM')
        old_state = alarm.get('OldStateValue', 'OK')
        reason = alarm.get('NewStateReason', 'Threshold Crossed')
    except:
        new_state = "ALARM"
        old_state = "OK"
        reason = "Manual Trigger"

    # 2. Logic Tampilan Header (Warna Warni)
    if new_state == "ALARM":
        header_icon = "🚨"
        status_text = "🔴 **CRITICAL ALERT**"
        footer_msg = "Segera lakukan investigasi pada server."
    elif new_state == "OK":
        header_icon = "✅"
        status_text = "🟢 **RECOVERY (SAFE)**"
        footer_msg = "Ancaman telah mereda."
    else:
        header_icon = "⚠️"
        status_text = f"🟡 **{new_state}**"
        footer_msg = "Status tidak diketahui."

    attacker_details = "⏳ _Sedang mengambil data log..._"

    # 3. Query Log (Hanya jika ALARM)
    if new_state == "ALARM":
        try:
            # Query 5 log terakhir
            query = "fields @timestamp, @message | filter @message like /Failed password/ | sort @timestamp desc | limit 5"
            
            start_query = logs_client.start_query(
                logGroupName=LOG_GROUP_NAME,
                startTime=int((datetime.now() - timedelta(minutes=15)).timestamp()),
                endTime=int(datetime.now().timestamp()),
                queryString=query
            )
            query_id = start_query['queryId']
            
            # Polling
            results = []
            for _ in range(5):
                time.sleep(1)
                resp = logs_client.get_query_results(queryId=query_id)
                if resp['status'] == 'Complete':
                    results = resp['results']
                    break
            
            if results:
                details_list = []
                for i, res in enumerate(results):
                    msg = next((item['value'] for item in res if item['field'] == '@message'), '')
                    ts = next((item['value'] for item in res if item['field'] == '@timestamp'), '')
                    
                    wib = convert_to_wib(ts)
                    
                    # Regex
                    match = re.search(r"from (\d+\.\d+\.\d+\.\d+)", msg)
                    ip = match.group(1) if match else "Unknown"
                    user_match = re.search(r"user (\S+)", msg)
                    user = user_match.group(1) if user_match else "?"
                    
                    loc = get_geolocation(ip)
                    
                    # LINK CHECKER (Biar bisa diklik)
                    ip_link = f"[{ip}](https://whatismyipaddress.com/ip/{ip})"
                    
                    # FORMAT BARU YANG RAPI
                    # Contoh:
                    # 1️⃣ root
                    #    └ 🏴 10.2.1.1 (LAN) 🕒 14:00
                    entry = (
                        f"{i+1}. 👤 **{user}**\n"
                        f"    └ 🌐 {ip_link} — {loc}\n"
                        f"    └ 🕒 `{wib} WIB`"
                    )
                    details_list.append(entry)
                
                attacker_details = "\n\n".join(details_list)
            else:
                attacker_details = "📭 Log kosong (Data belum masuk ke CloudWatch)"

        except Exception as e:
            attacker_details = f"⚠️ Error fetching logs: {str(e)[:50]}"

    # 4. Susun Pesan Akhir
    final_message = (
        f"{header_icon} {status_text} {header_icon}\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"🖥️ **Host:** On-Premise VM\n"
        f"📉 **Threshold:** > 3 Fails / 1 Min\n"
        f"➖➖➖➖➖➖➖➖➖➖\n\n"
        f"🕵️ **Top 5 Attackers (Realtime):**\n"
        f"{attacker_details}\n\n"
        f"📜 **Note:**\n_{footer_msg}_"
    )

    # 5. Kirim
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        # Matikan web page preview biar tidak penuh gambar link
        payload = {"chat_id": CHAT_ID, "text": final_message, "parse_mode": "Markdown", "disable_web_page_preview": True}
        http.request('POST', url, body=json.dumps(payload).encode('utf-8'), headers={'Content-Type': 'application/json'})
        return "Sent"
    except Exception as e:
        print(e)
        raise e