"""
GigaCat Telegram bot
Send a cat photo → get a muscular GigaCat back.

Setup:
  1. @BotFather → /newbot → paste token into .env as BOT_TOKEN
  2. Add an image API key (REPLICATE_API_TOKEN recommended)
  3. pip install -r requirements.txt
  4. python bot.py
"""

from __future__ import annotations

import io
import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("gigacat")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN", "").strip()
REPLICATE_MODEL = os.getenv(
    "REPLICATE_MODEL",
    "black-forest-labs/flux-kontext-pro",
)
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

GIGA_PROMPT = (
    "Transform this exact same cat into a GigaCat. Keep the identical face, "
    "eye color, nose, ear shape, and every fur marking (white body, orange-ginger "
    "patches on the head and sides). Give it a super muscular bodybuilder physique "
    "standing on hind legs in a double bicep flex pose, shredded abs, huge shoulders "
    "and arms, fur continuing over the muscle, dramatic gold rim lighting, dark gym "
    "background with sparks. Photorealistic. Same cat identity. No text."
)

STEPS = [
    "Scanning fur density…",
    "Mapping bone structure…",
    "Loading creatine protocol…",
    "INITIATING HYPERTROPHY",
]


def require_token() -> str:
    if not BOT_TOKEN:
        raise SystemExit("Missing BOT_TOKEN. Create .env from .env.example")
    return BOT_TOKEN


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("How it works")]],
        resize_keyboard=True,
    )
    await update.message.reply_text(
        "GIGACAT\n\n"
        "Send a photo of your cat.\n"
        "I send back the same cat — shredded, standing, flexing.\n\n"
        "One clear photo, face visible, works best.",
        reply_markup=keyboard,
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    ready = "online" if REPLICATE_API_TOKEN else "demo mode (no image API key yet)"
    await update.message.reply_text(
        "How it works\n"
        "1. Send a cat photo in this chat\n"
        "2. Wait for the ritual\n"
        "3. Get your GigaCat\n\n"
        f"Engine: {ready}\n\n"
        "Community: forward the result to your group with #gigacat"
    )


def upload_tmpfiles(image_bytes: bytes) -> str:
    """Public URL so Replicate can fetch the source photo."""
    r = requests.post(
        "https://tmpfiles.org/api/v1/upload",
        files={"file": ("cat.jpg", image_bytes, "image/jpeg")},
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    page_url = data["data"]["url"]
    return page_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")


def run_replicate(image_url: str) -> bytes:
    headers = {
        "Authorization": f"Bearer {REPLICATE_API_TOKEN}",
        "Content-Type": "application/json",
        "Prefer": "wait",
    }
    payload = {
        "input": {
            "prompt": GIGA_PROMPT,
            "input_image": image_url,
            "output_format": "jpg",
        }
    }
    create = requests.post(
        f"https://api.replicate.com/v1/models/{REPLICATE_MODEL}/predictions",
        headers=headers,
        json=payload,
        timeout=120,
    )
    if create.status_code >= 400:
        raise RuntimeError(f"Replicate error {create.status_code}: {create.text[:400]}")
    pred = create.json()
    if pred.get("output"):
        out = pred["output"]
        url = out[0] if isinstance(out, list) else out
        img = requests.get(url, timeout=120)
        img.raise_for_status()
        return img.content

    get_url = pred.get("urls", {}).get("get")
    if not get_url:
        raise RuntimeError("Replicate did not return an output URL")

    for _ in range(60):
        time.sleep(2)
        poll = requests.get(
            get_url,
            headers={"Authorization": f"Bearer {REPLICATE_API_TOKEN}"},
            timeout=60,
        )
        poll.raise_for_status()
        body = poll.json()
        status = body.get("status")
        if status == "succeeded":
            out = body["output"]
            url = out[0] if isinstance(out, list) else out
            img = requests.get(url, timeout=120)
            img.raise_for_status()
            return img.content
        if status in {"failed", "canceled"}:
            raise RuntimeError(body.get("error") or status)
    raise RuntimeError("Timed out waiting for GigaCat")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    assert update.message
    photos = update.message.photo
    if not photos:
        return
    status = await update.message.reply_text(STEPS[0])
    await update.message.chat.send_action(ChatAction.UPLOAD_PHOTO)

    best = photos[-1]
    file = await best.get_file()
    buf = io.BytesIO()
    await file.download_to_memory(buf)
    raw = buf.getvalue()

    for line in STEPS[1:]:
        await status.edit_text(line)
        await context.application.bot.send_chat_action(
            chat_id=update.effective_chat.id, action=ChatAction.TYPING
        )

    if not REPLICATE_API_TOKEN:
        await status.edit_text(
            "Photo received.\n\n"
            "The bot is in demo mode: no image API key is configured yet.\n"
            "Add REPLICATE_API_TOKEN to .env, restart, and send the photo again.\n\n"
            "Until then, drop the photo in the GigaCat Grok chat for a live transform."
        )
        return

    try:
        src_url = upload_tmpfiles(raw)
        result = run_replicate(src_url)
    except Exception as exc:
        log.exception("transform failed")
        await status.edit_text(
            "Could not finish the lift.\n"
            f"{exc}\n\n"
            "Try another photo with a clear face."
        )
        return

    await status.delete()
    await update.message.reply_photo(
        photo=result,
        caption="GIGACAT ASCENDED\nSame cat. Different league.",
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower()
    if "how" in text:
        await help_cmd(update, context)
        return
    await update.message.reply_text("Send a photo of your cat to begin.")


def start_health_server() -> None:
    """Keep Railway/Render web checks happy if PORT is set."""
    port = os.getenv("PORT")
    if not port:
        return
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading

    class Ok(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"gigacat ok")

        def log_message(self, fmt, *args):
            return

    httpd = HTTPServer(("0.0.0.0", int(port)), Ok)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    log.info("health server on %s", port)


def main() -> None:
    token = require_token()
    start_health_server()
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    log.info("GigaCat bot polling")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
