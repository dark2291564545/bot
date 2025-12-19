# Render Deployment Guide for Live Panel

## Issue: /live returns 404

### Cause:
Routes not properly registered on Render deployment

### Solution:

1. **Check bot logs on Render:**
```
Dashboard → Logs

Look for:
🚀 Live Panel: https://your-app.onrender.com/live
```

2. **Verify routes are registered:**
```python
# Should see in logs:
✅ Route registered: GET /live
✅ Route registered: POST /api/run-code
✅ Route registered: GET /api/view-logs
```

3. **If routes not showing, restart deployment:**
```bash
# In Render dashboard:
Manual Deploy → Clear build cache → Deploy
```

4. **Test endpoints:**
```bash
# Health check (should work):
curl https://dark-shadow-uc6c.onrender.com/health

# Live panel (should return HTML):
curl https://dark-shadow-uc6c.onrender.com/live

# View logs (should return JSON):
curl https://dark-shadow-uc6c.onrender.com/api/view-logs
```

## Quick Fix:

Add this to main.py after line 2730:

```python
# Debug: Print all routes
logger.info("📋 Registered Routes:")
for route in main_app.router.routes():
    logger.info(f"  {route.method:6} {route.resource.canonical}")
```

Then check Render logs to see if /live is listed.

## Alternative: Use /panel instead

If /live not working, use existing panel:
```
/panel command → Get token → Open URL
```

## Test Locally First:

```bash
# Run test server:
python test_live_panel.py

# Open browser:
http://localhost:8080/live

# If works locally but not on Render:
# - Check Render environment variables
# - Check Render build logs
# - Ensure all files uploaded to Render
```

## Render Configuration:

Make sure `render.yaml` or settings have:

```yaml
services:
  - type: web
    name: telegram-bot
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python bot_launcher.py
    envVars:
      - key: BOT_TOKEN
        sync: false
      - key: OWNER_ID
        sync: false
      - key: ADMIN_ID
        sync: false
```

## Checklist:

- [ ] All files committed to Git
- [ ] web_panel_live.py uploaded
- [ ] main.py has WebPanel import
- [ ] Routes registered in main.py
- [ ] Bot restarted on Render
- [ ] Logs show "Live Panel" URL
- [ ] /health endpoint works
- [ ] /live endpoint accessible

## Emergency Workaround:

If /live still doesn't work, access via:

```
1. /start in Telegram
2. Click "Upload File"
3. Upload your code
4. Click "My Files"
5. Click file → "Run"
6. Output shows in Telegram
```

Or use web panel:
```
/panel → Get URL → Upload/Run from there
```
