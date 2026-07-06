# Deploy Claptrap Chore Bot to Railway

This guide walks you through deploying your Claptrap Chore Bot Telegram bot to Railway for production use.

## Prerequisites

1. **Accounts needed:**
   - Railway account (free tier available)
   - GitHub account
   - Telegram Bot Token (from @BotFather)
   - OpenAI API Key

2. **Local setup complete:**
   - Bot tested locally with `python test_setup.py`
   - All files in `claptrap-chore-bot` folder

## Step 1: Prepare Your Repository

### 1.1 Create GitHub Repository
```bash
# Navigate to your bot directory
cd claptrap-chore-bot

# Initialize git repository
git init

# Add all files
git add .

# Make initial commit
git commit -m "Initial commit: Claptrap Chore Bot"

# Create GitHub repository and push
# (Replace with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/claptrap-chore-bot.git
git branch -M main
git push -u origin main
```

### 1.2 Verify Required Files
Make sure these files are in your repository:
- ✅ `bot.py` (main application)
- ✅ `Procfile` (contains: `worker: python bot.py`)
- ✅ `requirements.txt` (Python dependencies)
- ✅ `model_config.json` (configuration)
- ✅ `system_prompt.md` (Claptrap persona and formatting rules)
- ✅ `chore_manager.py` and `chore_functions.py` (chore-tracking logic)

## Step 2: Deploy to Railway

### 2.1 Create Railway Account
1. Go to [railway.app](https://railway.app)
2. Sign up with your GitHub account
3. Verify your email if required

### 2.2 Create New Project
1. Click **"New Project"**
2. Select **"Deploy from GitHub repo"**
3. Choose your `claptrap-chore-bot` repository
4. Click **"Deploy Now"**

### 2.3 Configure Environment Variables
1. In your Railway dashboard, go to your project
2. Click on the **"Variables"** tab
3. Add the following environment variables:

```
TELEGRAM_TOKEN=your_telegram_bot_token_here
OPENROUTER_API_KEY=your_openrouter_api_key_here
```

**To add each variable:**
- Click **"New Variable"**
- Enter the variable name (e.g., `TELEGRAM_TOKEN`)
- Enter the value
- Click **"Add"**

Or via the Railway CLI:
```bash
railway variables --set TELEGRAM_TOKEN="your_telegram_bot_token_here"
railway variables --set OPENROUTER_API_KEY="your_openrouter_api_key_here"
```

### 2.4 Configure Service Settings
1. Go to **"Settings"** tab
2. Under **"Service"**, set:
   - **Start Command**: `python bot.py` (should auto-detect from Procfile)
   - **Port**: Leave empty (not needed for Telegram bot)

### 2.5 Deploy
1. Railway should automatically start deploying
2. Monitor the **"Logs"** tab for deployment progress
3. Look for messages like:
   ```
   🤖 Starting Claptrap Chore Bot...
   ✅ Bot initialized successfully!
   🔄 Starting polling for messages...
   ```

## Step 3: Verify Deployment

### 3.1 Check Logs
In Railway dashboard:
1. Go to **"Logs"** tab
2. Look for successful startup messages
3. Watch for any error messages

### 3.2 Test Your Bot
1. Open Telegram
2. Search for your bot by username
3. Send `/start` command
4. Try a test query: "add a chore: water the plants, every 3 days"
5. Verify the bot responds correctly, in Claptrap's voice

## Step 4: Monitoring and Maintenance

### 4.1 Monitor Usage
- Check Railway dashboard for resource usage
- Monitor logs for errors or performance issues
- Watch OpenAI API usage/limits

### 4.2 Update Bot
To update your bot after code changes:

```bash
# Make changes to your code
git add .
git commit -m "Update bot functionality"
git push origin main
```

Railway will automatically redeploy when you push to GitHub.

### 4.3 Check Resource Limits
Railway free tier includes:
- 500 execution hours/month
- Shared CPU and RAM
- Automatic sleep after inactivity

For production use, consider upgrading to a paid plan.

## Troubleshooting

### Common Issues

**Bot not starting:**
```
❌ Check logs in Railway dashboard
❌ Verify all environment variables are set
❌ Ensure Procfile contains: worker: python bot.py
```

**Import errors:**
```
❌ Check requirements.txt includes all dependencies
❌ Verify all Python files are in repository
❌ Check for syntax errors in code
```

**API errors:**
```
❌ Verify API keys are correct and active
❌ Check OpenAI account has credits
```

**Bot responds slowly:**
```
❌ Check if Railway service is sleeping (free tier)
❌ Monitor OpenAI API response times
```

### Debug Commands

Add debug logging to see what's happening:

```python
# Add to bot.py for more detailed logging
logging.getLogger().setLevel(logging.DEBUG)
```

### Railway CLI (Optional)

Install Railway CLI for easier management:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# View logs locally
railway logs

# Set environment variables
railway variables --set TELEGRAM_TOKEN="your_token_here"
```

## Security Best Practices

1. **Never commit API keys to Git**
   - Use environment variables only
   - Add `.env` to `.gitignore`

2. **Rotate API keys periodically**
   - Update keys in Railway dashboard
   - Redeploy after key changes

3. **Monitor bot usage**
   - Check for unusual activity
   - Set up API usage alerts

## Scaling Considerations

### For Higher Traffic:
1. **Upgrade Railway plan** for more resources
2. **Optimize API calls** with caching
3. **Monitor response times** and error rates
4. **Consider webhook mode** instead of polling (advanced)

### Production Checklist:
- ✅ All environment variables configured
- ✅ Bot responding to test commands
- ✅ Logs showing successful startup
- ✅ API keys working (OpenAI, Telegram)
- ✅ Error handling tested
- ✅ Resource usage monitored

## Support and Updates

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Bot Logs**: Check Railway dashboard > Logs tab (also written to `claptrap_bot.log`)
- **API Status**: Monitor OpenAI API status page
- **Updates**: Push to GitHub for automatic redeployment

Your Claptrap Chore Bot is now live and ready to boss around minions about their chores! 🤖
