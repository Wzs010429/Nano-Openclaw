"""
1. 添加内置工具 Read 和 Write，允许Claude直接读取和写入文件系统中的文件，适用于需要处理文件的场景。
2. 添加MCP工具 并且执行
"""

import os
from pathlib import Path
from dotenv import load_dotenv


load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
ANTHROPIC_BASE_URL = os.environ["ANTHROPIC_BASE_URL"]

# 工作目录 Agent在这里面操作文件
BASE_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = BASE_DIR / "workspace"

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes


from claude_agent_sdk import (
    AssistantMessage,  # Claude 回复的消息
    ClaudeAgentOptions,  # 启动claude code的配置项
    ResultMessage,  # 最终执行结果
    TextBlock,  # 文本块的内容
    query,  # 核心函数发送给Claude
    create_sdk_mcp_server,  # 创建MCP服务器的函数
    tool,  # 定义工具的装饰器
)

from typing import Any


def create_mcp_server_tools(bot, chat_id: int) -> list:
    
    @tool("send_message", "向Telegram用户发送消息", {"text": str})
    async def send_message(args) -> dict[str, Any]:
        # 主动给用户发消息
        text = args["text"]
        await bot.send_message(chat_id=chat_id, text=text)
        # 返回值是：告诉Agent发送消息的结果
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"消息已发送给用户：{text}",
                }
            ]
        }
    return [send_message]
        



async def ask_claude(prompt: str, bot, chat_id: int) -> str:
    env = {
        "ANTHROPIC_API_KEY": ANTHROPIC_API_KEY,
        "ANTHROPIC_BASE_URL": ANTHROPIC_BASE_URL,
    }


    WORKSPACE_DIR.mkdir(exist_ok=True)
    mcp_tools = create_mcp_server_tools(bot=bot, chat_id=chat_id)

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
        # 新建路径
        cwd = str(WORKSPACE_DIR),
        # 可用的 Claude Code 内置工具
        tools=[
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
        ],
        # 自动允许执行的工具
        allowed_tools=[
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "mcp__assistant__send_message",
        ],  # 允许Claude使用的工具列表，工具需要在Agent中预先定义好
        # agents={

        # }
        # bypassPermission 接受所有的权限请求，适用于完全信任Claude的场景 仅仅隔离docker和虚拟机
        permission_mode="acceptEdits",
        env=env,
        mcp_servers={
            "assistant": create_sdk_mcp_server(
                name="assistant",
                tools=mcp_tools,
            ),
        },
    )


    # 构造一个异步生成器prompt， 解决SDK使用MCP工具时，无法实时获取Claude回复的问题
    async def _make_prompt(text: str):
        yield {
            "type": "user",
            "message": {
                "role": "user",
                "content": text,
            },
            "parent_tool_use_id": None,
            "session_id": "default",
        }

    
    response_parts: list[str] = []
    async for message in query(prompt=_make_prompt(prompt), options=options):
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
    
    response = await ask_claude(
        update.message.text,
        bot=context.bot,
        chat_id=update.message.chat_id,
    )
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

