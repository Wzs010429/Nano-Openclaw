"""
本节本质上是接一个Claude Code Agent的query()函数，改造成Telegram Bot的消息处理函数，来实现一个简单的回显机器人。
这里使用的是Deepseeek API的Anthropic接口，来调用Claude模型。你也可以根据需要替换成其他API接口，只要保证query()函数能够正确调用即可。
"""

import os
from dotenv import load_dotenv


load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ANTHROPIC_BASE_URL = os.environ["ANTHROPIC_BASE_URL"]

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes


from claude_agent_sdk import (
    AssistantMessage,  # Claude 回复的消息
    ClaudeAgentOptions,  # 启动claude code的配置项
    ResultMessage,  # 最终执行结果
    TextBlock,  # 文本块的内容
    query,  # 核心函数发送给Claude
)

async def ask_claude(prompt: str) -> str:
    env = {
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "ANTHROPIC_BASE_URL": ANTHROPIC_BASE_URL,
    }


    """ 
    Claude Agent的权限模式，决定了Claude在执行过程中如何处理权限请求：
    PermissionMode = Literal[
        "default",  # Standard permission behavior
        "acceptEdits",  # Auto-accept file edits
        "plan",  # Planning mode - explore without editing
        "dontAsk",  # Deny anything not pre-approved instead of prompting
        "bypassPermissions",  # Bypass permission checks; explicit ask rules still prompt (use with caution)
    ] 
    """
    options = ClaudeAgentOptions(
        # bypassPermission 接受所有的权限请求，适用于完全信任Claude的场景 仅仅隔离docker和虚拟机
        permission_mode="acceptEdits",
        env=env,
    )
    
    response_parts: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    print("Claude回复了消息：", block.text)
                    response_parts.append(block.text)           
        elif isinstance(message, ResultMessage):
            if message.result:
                print("Claude执行完成，结果是：", message.result)
                response_parts.append(message.result)

    return "\n".join(response_parts) or "Claude没有回复任何内容。"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理用户发送的消息，调用Claude并回复结果"""
    if not update.message or not update.message.text:
        return
    
    response = await ask_claude(update.message.text)
    max_length = 4096  # Telegram消息的最大长度
    for i in range(0, len(response), max_length):
        await update.message.reply_text(response[i:i+max_length])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """处理/start命令"""
    # print("============================================")
    # print(update)
    await update.message.reply_text("👋你好！我是jkwzs_bot。\n\n给我发任何消息，我都会原样返回给你！")


# 改造当前函数 Claude Code Agent 的query()流式输出
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """回显用户发送的消息"""
    await update.message.reply_text(update.message.text)


def main():
    """启动Telegram Bot"""
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # 添加命令处理器和消息处理器
    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    ) # 处理所有文本消息，排除命令

    print("Bot已启动，等待消息...")
    app.run_polling()  # 启动轮询，监听消息

if __name__ == "__main__":
    main()

