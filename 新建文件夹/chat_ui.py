"""Gradio 对话页：接入 Agent（意图 + Cpp 检索 + LLM）与 Memory 短时/长时记忆。

启动示例::

    python -m view.chat_ui --host 127.0.0.1 --port 8088
"""

from __future__ import annotations

import argparse
import logging
import uuid

import gradio as gr

from agents.pipeline import run_chat_turn
from memory.manager import MemoryManager

logger = logging.getLogger(__name__)

_memory = MemoryManager()


def _on_send(message: str, history: list[dict[str, str]] | None, user_id: str):
    """调用 Agent 流水线生成回复，并写入 MemoryManager。"""
    message = (message or "").strip()
    history = history or []
    uid = (user_id or "").strip()
    if not uid:
        uid = uuid.uuid4().hex

    if not message:
        return history, "", uid

    history.append({"role": "user", "content": message})
    try:
        reply = run_chat_turn(uid, message, _memory)
    except Exception as e:
        logger.exception("run_chat_turn 失败：%s", e)
        reply = f"处理请求时出错：{e!s}"

    history.append({"role": "assistant", "content": reply or ""})
    return history, "", uid


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="Enterprise AI Assistant") as demo:
        gr.Markdown("## Enterprise AI Assistant")
        user_id_state = gr.State(value="")
        chatbot = gr.Chatbot(
            label="对话框",
            type="messages",
            height=480,
        )
        with gr.Row():
            input_box = gr.Textbox(
                label="输入框",
                placeholder="请输入你的问题...",
                lines=3,
                scale=8,
            )
            send_btn = gr.Button("发送", variant="primary", scale=1)

        send_btn.click(
            fn=_on_send,
            inputs=[input_box, chatbot, user_id_state],
            outputs=[chatbot, input_box, user_id_state],
        )
        input_box.submit(
            fn=_on_send,
            inputs=[input_box, chatbot, user_id_state],
            outputs=[chatbot, input_box, user_id_state],
        )
    return demo


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="启动 Gradio 对话页面")
    parser.add_argument("--host", default="127.0.0.1", help="绑定地址，默认 127.0.0.1")
    parser.add_argument("--port", type=int, default=7860, help="监听端口，默认 7860")
    return parser


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = _build_arg_parser().parse_args()
    demo = build_demo()
    demo.launch(server_name=args.host, server_port=args.port)


if __name__ == "__main__":
    main()
