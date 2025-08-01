from aiogram.dispatcher.middlewares import BaseMiddleware

class MessageLoggerMiddleware(BaseMiddleware):
    async def on_post_process_message(self, message, results, data):
        if message:
            user_id = message.from_user.id
            chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(message.message_id)

    async def on_post_process_callback_query(self, callback, results, data):
        if callback and callback.message:
            user_id = callback.from_user.id
            chat_links.setdefault(user_id, {}).setdefault("msgs", []).append(callback.message.message_id)
