# GigaCat Telegram bot

Community flow: member sends a cat photo in Telegram → bot replies with the GigaCat.

## 1. Create the bot (2 minutes)

1. Open Telegram → [@BotFather](https://t.me/BotFather)
2. `/newbot`
3. Name: `GigaCat`
4. Username: something like `GigaCatStudioBot` (must end in `bot`)
5. Copy the token
6. `/setdescription` → `Send a photo of your cat. Get a GigaCat.`
7. `/setuserpic` → upload the official mascot flex image
8. Optional Mini App later: `/newapp` + your hosted studio URL

## 2. Put the token on your machine

```bash
cd gigacat-telegram
cp .env.example .env
```

Edit `.env`:

```
BOT_TOKEN=the_token_from_BotFather
REPLICATE_API_TOKEN=your_replicate_key
```

Without `REPLICATE_API_TOKEN` the bot still runs, accepts photos, and explains it is in demo mode. With the key it returns a real transform.

Replicate account: https://replicate.com (pay-as-you-go image edits). Flux Kontext (or any image-to-image model) is the default.

## 3. Run it

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```

Leave the terminal open. Open your bot in Telegram, tap Start, send a cat photo.

## 4. Share with the community

Pin in the group:

> Send your cat to @YourBotUsername
> Photo in → GigaCat out
> Forward the flex back here with #gigacat

Add the bot to the group if you want people to use it in-chat. For less spam, tell them to DM the bot and only post results.

## 5. Keep it online

Polling (`python bot.py`) only works while your computer is on.

For 24/7:

- Railway / Render / Fly.io
- Set the same env vars
- Start command: `python bot.py`

## Official mascot

The face to match is the white-and-ginger street cat (orange patches on the head and flanks, pale eyes, serious look). Every GigaCat should keep that identity when that photo is the source — and keep *each member’s* markings when they send their own cat.
