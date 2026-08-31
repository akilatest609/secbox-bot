import logging
import random
import string
from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8951474107:AAF24BjaGYSa24Qyc1-q_vd53olRocgpkJM"
ADMIN_CHAT_ID = 8536087082  # Your personal Telegram ID

# In-memory mappings (use Redis or a database for production persistence)
active_sessions = {}  # userId -> alias
message_mapping = {}  # adminMessageId -> userId


def generate_alias(user_id: int) -> str:
    if user_id in active_sessions:
        return active_sessions[user_id]
    
    # Generate a random 4-character alphanumeric string
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    alias = f"User_{suffix}"
    active_sessions[user_id] = alias
    return alias


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.from_user:
        return

    user_id = message.from_user.id
    chat_type = message.chat.type

    # Ignore non-private chats unless it's a message in the admin chat
    if chat_type != "private" and message.chat.id != ADMIN_CHAT_ID:
        return

    # Check if you (the admin) are replying to a message
    if message.chat.id == ADMIN_CHAT_ID and message.reply_to_message:
        target_user_id = message_mapping.get(message.reply_to_message.message_id)
        if target_user_id:
            # Forward your reply back to the user
            await context.bot.copy_message(
                chat_id=target_user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
        return

    # If it's a regular user message in a private chat
    if chat_type == "private" and user_id != ADMIN_CHAT_ID:
        alias = generate_alias(user_id)

        # Notify you about the sender's alias
        info_text = f"Message from *{alias}* (ID: `{user_id}`):"
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=info_text, parse_mode="Markdown")

        # Copy the user's message/media to your chat
        forwarded = await context.bot.copy_message(
            chat_id=ADMIN_CHAT_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )

        # Map your forwarded message ID back to the user's ID
        message_mapping[forwarded.message_id] = user_id

        # Acknowledge receipt to the user
        await message.reply_text("Your message has been forwarded anonymously to the team.")


def main() -> None:
    application = Application.builder().token(TOKEN).build()

    # Handle all message types (text, photo, document, voice, etc.)
    application.add_handler(MessageHandler(filters.ALL, handle_message))

    print("Python anonymous relay bot running...")
    application.run_polling()


if __name__ == "__main__":
    main()