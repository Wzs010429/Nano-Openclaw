"""
Telegram 部署验证

"""

import os
from dotenv import load_dotenv


load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理/start命令"""
    # print("============================================")
    # print(update)
    await update.message.reply_text("👋你好！我是jkwzs_bot。\n\n给我发任何消息，我都会原样返回给你！")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """回显用户发送的消息"""
    await update.message.reply_text(update.message.text)


def main():
    """启动Telegram Bot"""
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # 添加命令处理器和消息处理器
    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, echo)
    ) # 处理所有文本消息，排除命令

    print("Bot已启动，等待消息...")
    app.run_polling()  # 启动轮询，监听消息

if __name__ == "__main__":
    main()

