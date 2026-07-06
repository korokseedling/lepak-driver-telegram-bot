# Claptrap Chore Bot - Telegram Bot

A Telegram bot that helps you track recurring household chores, with the personality of Claptrap (Borderlands) — zany, self-aggrandizing, and addressing you as "minion."

## Features

### 🧹 Chore Tracking
- Check outstanding chores (due or overdue)
- Set up new recurring chores with an interval and grace period
- Mark chores complete, optionally logging a remark
- Update an existing chore's interval or grace period

### 🔔 Proactive Notifications
- Daily background job scans every user's chores and pushes a Telegram message when a chore has gone overdue (past its grace period)

### 💬 Natural Language Support
- Conversational, in-persona responses (zany but factually accurate about chore status)
- Conversation history maintained per day

## Setup Instructions

### 1. Prerequisites
- Python 3.8+
- Telegram Bot Token (from @BotFather)
- OpenAI API Key

### 2. Installation

```bash
# Clone or copy the files to your directory
cd claptrap-chore-bot

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your actual API keys
```

### 3. Configuration

Create a `.env` file with:
```
TELEGRAM_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
```

### 4. Run the Bot

```bash
python bot.py
```

## Usage Examples

### Chore Queries
- "What chores do I still need to do?"
- "Add a chore: water the plants, every 3 days"
- "I just did the dishes"
- "Mark laundry as done, used the delicates cycle"
- "Change watering plants to every 5 days"

### Commands
- `/start` - Welcome message and introduction
- `/help` - Show usage examples
- `/clear` - Reset conversation history

## Technical Details

- **Model**: OpenAI GPT-4o-mini with function calling
- **Chore Storage**: One JSON file per user, stored locally
- **Conversation**: Daily conversation history with 20-message limit
- **Error Handling**: Comprehensive error handling with user-friendly messages

## File Structure

```
claptrap-chore-bot/
├── bot.py                    # Main bot application, incl. daily overdue-notification job
├── chore_manager.py          # Chore persistence and business logic
├── chore_functions.py        # OpenAI tool functions for chore tracking
├── model_config.json         # Model and API configuration
├── system_prompt.md          # System prompt for the bot (Claptrap persona)
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── chores/                   # Per-user chore data (created on run)
└── conversations/            # Per-user conversation history (created on run)
```

## Deployment Options

### Local Development
Run directly with `python bot.py`

### Production (Heroku/Railway)
1. Add a `Procfile`:
   ```
   worker: python bot.py
   ```

2. Set environment variables in your platform's dashboard

3. Deploy and scale to 1 worker

## Troubleshooting

1. **Bot not responding**: Check your `.env` file has all required tokens
2. **Chores not saving**: Ensure the process has write access to create the `chores/` directory
3. **Tool calls failing**: Check `model_config.json` matches the functions registered in `chore_functions.py`

## Support

Check the logs in `claptrap_bot.log` for detailed error information.
