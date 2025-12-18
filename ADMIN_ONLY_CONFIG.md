# 🔒 ADMIN-ONLY BOT CONFIGURATION

**💫 MADE BY DARK SHADOW 💫**

---

## ✅ What Changed?

Bot is now **completely admin-only**. Only users in `admin_ids` can use it.

### 🛡️ Security Features:

1. **Command Protection** - All commands blocked for non-admins:
   - `/start` - Shows "Admin Only Bot" message
   - `/help` - Admin only
   - `/stats` - Admin only
   - `/search` - Admin only
   - `/panel` - Admin only

2. **Callback Protection** - All button interactions blocked:
   - ✅ Upload File
   - ✅ My Files
   - ✅ Favorites
   - ✅ Search
   - ✅ Statistics
   - ✅ Web Panel
   - ✅ Speed Test
   - ✅ Help
   - ✅ All Features
   - ✅ Premium
   - ✅ File Operations (run, delete, extract, info)

3. **File Upload Protection** - Only admins can upload files

4. **Logging** - Unauthorized access attempts are logged with:
   ```
   WARNING: Unauthorized access attempt by user 123456 (@username)
   ```

---

## 🔧 How to Add Admins

### Owner (from .env):
```env
OWNER_ID=your_telegram_id
```

### Additional Admins:
Use `/addadmin` command as owner:
```
/addadmin 123456789
```

---

## 👥 Current Admin System

### Roles:

**Owner** (from .env):
- Full access
- Can add/remove admins
- Never expires
- 999 file limit

**Admin** (added via /addadmin):
- Full bot features
- 24-hour hosting sessions
- 999 file limit
- Cannot add other admins (owner only)

**Regular Users**:
- ❌ Blocked completely
- See message: "🔒 ADMIN ONLY BOT"
- Redirected to @DARK22v

---

## 📋 Non-Admin Experience

When a regular user tries to use the bot:

```
🔒 ADMIN ONLY BOT

⚠️ This bot is restricted to authorized administrators only.

👑 Owner: @DARK22v
📢 Channel: https://t.me/DARK22v

💫 MADE BY DARK SHADOW 💫
```

---

## 🎯 Setup Instructions

### 1. Configure .env:
```env
BOT_TOKEN=your_bot_token
OWNER_ID=your_telegram_id
ADMIN_ID=your_telegram_id
YOUR_USERNAME=@DARK22v
UPDATE_CHANNEL=https://t.me/DARK22v
```

### 2. Run Bot:
```bash
python bot_launcher.py
```

### 3. Test Access:
- Message bot with owner account ✅
- Message bot with other account ❌ (blocked)

---

## 🔐 Security Implementation

### Authorization Function:
```python
async def is_admin_user(user_id: int, callback_query=None) -> bool:
    if user_id not in admin_ids:
        if callback_query:
            await callback_query.answer("🔒 Admin Only Bot!", show_alert=True)
        return False
    return True
```

### Used In:
- ✅ All 11 commands
- ✅ All 36+ callback handlers
- ✅ File upload handler
- ✅ Document handler

---

## 📊 Benefits

1. **Complete Privacy** - Only you can use the bot
2. **No Spam** - Random users can't flood your bot
3. **Resource Control** - Only authorized file uploads
4. **Professional** - Shows clear "Admin Only" message
5. **Scalable** - Easy to add trusted admins

---

## 🆘 FAQ

**Q: How do I allow someone else to use the bot?**  
A: Use `/addadmin their_telegram_id` as owner

**Q: Can I make it public again?**  
A: Yes, remove the `if not await is_admin_user(...)` checks

**Q: What if I forget my owner ID?**  
A: Message @userinfobot on Telegram to get your ID

**Q: Can admins add other admins?**  
A: No, only the owner can add/remove admins

---

**💫 MADE BY DARK SHADOW 💫**
