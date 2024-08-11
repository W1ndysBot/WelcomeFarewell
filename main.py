# script/WelcomeFarewell/main.py

import logging
import os
import sys
import asyncio

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.config import owner_id
from app.api import *
from app.scripts.GroupSwitch.main import *

# 数据存储路径，实际开发时，请将WelcomeFarewell替换为具体的数据存放路径
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "WelcomeFarewell",
)


# 是否是群主
def is_group_owner(role):
    return role == "owner"


# 是否是管理员
def is_group_admin(role):
    return role == "admin"


# 是否是管理员或群主或root管理员
def is_authorized(role, user_id):
    is_admin = is_group_admin(role)
    is_owner = is_group_owner(role)
    return (is_admin or is_owner) or (user_id in owner_id)


# 查看功能开关状态
def load_WelcomeFarewell_status(group_id):
    return load_switch(group_id, "欢迎欢送")


# 保存功能开关状态
def save_WelcomeFarewell_status(group_id, status):
    save_switch(group_id, "欢迎欢送", status)


# 保存自定义欢迎词
def save_custom_welcome_message(group_id, message):
    with open(os.path.join(DATA_DIR, f"{group_id}.txt"), "w", encoding="utf-8") as file:
        file.write(message)


# 加载自定义欢迎词
def load_custom_welcome_message(group_id):
    try:
        with open(
            os.path.join(DATA_DIR, f"{group_id}.txt"), "r", encoding="utf-8"
        ) as file:
            return file.read()
    except FileNotFoundError:
        return None


# 入群欢迎退群欢送管理函数
async def WelcomeFarewell_manage(websocket, msg):
    user_id = msg.get("user_id")
    group_id = msg.get("group_id")
    raw_message = msg.get("raw_message")
    message_id = msg.get("message_id")
    role = msg.get("role")

    # 开启入群欢迎
    if is_authorized(role, user_id):  # 修复 is_authorized 调用
        if raw_message == "wf-on":
            if load_switch(group_id, "欢迎欢送"):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]入群欢迎和退群欢送已经开启了，无需重复开启。",
                )
            else:
                save_switch(group_id, "欢迎欢送", True)
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]已开启入群欢迎和退群欢送。",
                )
        elif raw_message == "wf-off":
            if not load_switch(group_id, "欢迎欢送"):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]入群欢迎和退群欢送已经关闭了，无需重复关闭。",
                )
            else:
                save_switch(group_id, "欢迎欢送", False)
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]已关闭入群欢迎和退群欢送。",
                )
        elif raw_message.startswith("wf-set "):  # 检测设置欢迎词命令
            custom_message = raw_message[len("wf-set ") :]
            save_custom_welcome_message(group_id, custom_message)
            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]已设置自定义欢迎词\n欢迎词为：{custom_message}",
            )


# 群通知处理函数
async def handle_WelcomeFarewell_group_notice(websocket, msg):
    try:
        # 确保数据目录存在
        os.makedirs(DATA_DIR, exist_ok=True)

        user_id = msg.get("user_id")
        group_id = msg.get("group_id")
        sub_type = msg.get("sub_type")
        if load_WelcomeFarewell_status(group_id):
            if sub_type == "approve" or sub_type == "invite":
                custom_welcome = f"欢迎[CQ:at,qq={user_id}]入群\n{load_custom_welcome_message(group_id)}"
                welcome_message = (
                    custom_welcome
                    if custom_welcome
                    else f"欢迎[CQ:at,qq={user_id}]入群"
                )
                await send_group_msg(websocket, group_id, f"{welcome_message}")

            elif sub_type == "kick":
                farewell_message = f"{user_id} 已被踢出群聊🎉🎉🎉"
                if farewell_message:
                    await send_group_msg(websocket, group_id, f"{farewell_message}")

            elif sub_type == "leave":
                farewell_message = f"{user_id} 退群了😭😭😭"
                if farewell_message:
                    await send_group_msg(websocket, group_id, f"{farewell_message}")

    except Exception as e:
        logging.error(f"处理WelcomeFarewell群通知失败: {e}")
        return
