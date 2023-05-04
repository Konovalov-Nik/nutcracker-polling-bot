import os
import json

import requests
from bs4 import BeautifulSoup

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

APP = None
SUBS = []
SEARCH_STRINGS = ["nutcracker", "shchelkunchik", "shelkuncik", "selkuncik", "louskáček", "louskacek", "louskachek"]

FOUND_LINKS = set([])
BASE_LINK = "https://www.narodni-divadlo.cz" 
POLLING_LINK = f"{BASE_LINK}/en/programme"

POLLING_INTERVAL = 60 * 5 # 5 min
POLLING_JOB = None


def poll() -> None:
    print("Polling...")
    
    page = requests.get(POLLING_LINK)
    soup = BeautifulSoup(page.content, 'html.parser')
    all_links = soup.find_all("a")
    
    found = False
    for link in all_links:
        for string in SEARCH_STRINGS:
            href = link.get("href").lower()
            if string in href:
                if "?t=" not in href:
                    #skip links with no date
                    continue
                
                global FOUND_LINKS
                FOUND_LINKS.add(f"{BASE_LINK}{href}")
                
                found = True
                print(f"Found {href}")
    
    if not found:
        print("Nothing found")


async def notify_loop(context: ContextTypes.DEFAULT_TYPE) -> None:
    global APP
    poll()
    if len(FOUND_LINKS) > 0:
        for chat_id in SUBS:
            all_links = "\n".join(FOUND_LINKS)
            await APP.bot.send_message(chat_id, f"Found tickets!\nGo to {all_links}")
        disable_polling()


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id in SUBS:
        await update.message.reply_text("You are already subscribed")
    else:
        SUBS.append(update.message.chat_id)
        save_subs()
        await check_command(update, context)
        await update.message.reply_text("You are subscribed for notifications")


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.chat_id in SUBS:
        SUBS.remove(update.message.chat_id)
        save_subs()
        await update.message.reply_text("You are unsubscribed from notifications")
    else:
        await update.message.reply_text("You are not subscribed")


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(FOUND_LINKS) > 0:
        all_links = "\n".join(FOUND_LINKS)
        await update.message.reply_text(f"Found tickets!\nGo to {all_links}")
    else:
        await update.message.reply_text("No tickets found :(")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Use\n/hochu to subscribe for notifications\n/nuchotam to check the most recent status\n/nehochu to unsubscribe")


def save_subs():
    with open("subs.json", "w") as file:
        json.dump(SUBS, file)


def load_subs():
    with open("subs.json", "r") as file:
        global SUBS
        SUBS = json.load(file)


def disable_polling():
    global POLLING_JOB
    POLLING_JOB.schedule_removal()


if __name__ == '__main__':
    token = os.environ.get("TOKEN")
    if not token:
        raise ValueError("TOKEN environment variable is not set")
    
    load_subs()
    
    APP = ApplicationBuilder().token(token).build()

    APP.add_handler(CommandHandler("start", help_command))
    APP.add_handler(CommandHandler("help", help_command))
    APP.add_handler(CommandHandler("hochu", subscribe_command))
    APP.add_handler(CommandHandler("nehochu", unsubscribe_command))
    APP.add_handler(CommandHandler("nuchotam", check_command))
    POLLING_JOB = APP.job_queue.run_repeating(notify_loop, interval=POLLING_INTERVAL, first=0)

    APP.run_polling()