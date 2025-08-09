"""
Get your Telegram chat ID after starting a conversation with the bot
"""

import requests
import json

def get_chat_id():
    """Get chat ID from bot updates"""
    
    # Your bot token
    token = '8405614465:AAGl1MFkI4T7dksrk93oHXJOilcBXH36Do0'
    bot_username = '@MonkeyAttack_ProfitHit_Bot'
    
    print("=" * 50)
    print("TELEGRAM CHAT ID FINDER")
    print("=" * 50)
    print(f"\nBot: {bot_username}")
    print("\nChecking for messages...")
    
    # Get updates
    url = f'https://api.telegram.org/bot{token}/getUpdates'
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"Error connecting to Telegram: {response.status_code}")
        return
    
    data = response.json()
    
    if not data['ok']:
        print("Error from Telegram API")
        return
    
    if not data['result']:
        print("\n*** NO MESSAGES FOUND ***")
        print("\nTo get your chat ID:")
        print("1. Open Telegram")
        print(f"2. Search for {bot_username}")
        print("3. Send ANY message (like 'Hello')")
        print("4. Run this script again")
        return
    
    # Find unique chats
    chats = {}
    for update in data['result']:
        if 'message' in update:
            chat = update['message']['chat']
            chat_id = chat['id']
            
            if chat_id not in chats:
                chat_type = chat.get('type', 'private')
                
                if chat_type == 'private':
                    # Private chat with user
                    first_name = chat.get('first_name', '')
                    last_name = chat.get('last_name', '')
                    username = chat.get('username', '')
                    
                    chats[chat_id] = {
                        'type': 'Private Chat',
                        'name': f"{first_name} {last_name}".strip(),
                        'username': username
                    }
                else:
                    # Group chat
                    chats[chat_id] = {
                        'type': 'Group Chat',
                        'name': chat.get('title', 'Unknown'),
                        'username': ''
                    }
    
    if chats:
        print("\n*** FOUND CHATS ***\n")
        
        for chat_id, info in chats.items():
            print(f"Chat Type: {info['type']}")
            print(f"Chat ID: {chat_id}")
            print(f"Name: {info['name']}")
            if info['username']:
                print(f"Username: @{info['username']}")
            print("-" * 30)
        
        print("\n*** NEXT STEPS ***")
        print("\n1. Copy your Chat ID from above")
        print("2. Update your .env file:")
        print(f"   TELEGRAM_CHAT_ID={list(chats.keys())[0]}")
        print("\n3. Test the connection:")
        print("   python test_telegram.py")
        
        # Offer to test immediately
        if len(chats) == 1:
            chat_id = list(chats.keys())[0]
            print(f"\nWant to test sending to chat {chat_id}? (y/n): ", end="")
            
            answer = input().strip().lower()
            if answer == 'y':
                test_message = {
                    'chat_id': chat_id,
                    'text': 'Test successful! Your automation is ready to send trade alerts.',
                    'parse_mode': 'Markdown'
                }
                
                send_url = f'https://api.telegram.org/bot{token}/sendMessage'
                test_response = requests.post(send_url, json=test_message)
                
                if test_response.status_code == 200:
                    print("\nMessage sent successfully! Check your Telegram.")
                else:
                    print(f"\nFailed to send: {test_response.text}")
    else:
        print("\nNo chats found. Please send a message to the bot first.")

if __name__ == "__main__":
    get_chat_id()