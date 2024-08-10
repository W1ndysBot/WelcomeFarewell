# script/WelcomeFarewell/main.py
# 示例脚本
# 本脚本写好了基本的函数，直接在函数中编写逻辑即可，必要的时候可以修改函数名
# 注意：WelcomeFarewell 是具体功能，请根据实际情况一键替换即可
# 注意：WelcomeFarewell 是函数名称，请根据实际情况一键替换即可

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
    return load_switch(group_id, "WelcomeFarewell")


# 保存功能开关状态
def save_WelcomeFarewell_status(group_id, status):
    save_switch(group_id, "WelcomeFarewell", status)


# 入群欢迎退群欢送管理函数
async def WelcomeFarewell_manage(websocket, msg):
    user_id = msg.get("user_id")
    group_id = msg.get("group_id")
    raw_message = msg.get("raw_message")
    message_id = msg.get("message_id")
    role = msg.get("role")

    # 开启入群欢迎
    if is_authorized(role, user_id):  # 修复 is_authorized 调用
        if raw_message == "WF -on":
            if load_switch(group_id, "WelcomeFarewell"):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]入群欢迎和退群欢送已经开启了，无需重复开启。",
                )
            else:
                save_switch(group_id, "WelcomeFarewell", True)
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]已开启入群欢迎和退群欢送。",
                )
        elif raw_message == "WF -off":
            if not load_switch(group_id, "WelcomeFarewell"):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]入群欢迎和退群欢送已经关闭了，无需重复关闭。",
                )
            else:
                save_switch(group_id, "WelcomeFarewell", False)
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]已关闭入群欢迎和退群欢送。",
                )


# 群通知处理函数
async def handle_WelcomeFarewell_group_notice(websocket, msg):
    try:
        user_id = msg.get("user_id")
        group_id = msg.get("group_id")
        sub_type = msg.get("sub_type")
        if load_WelcomeFarewell_status(group_id):
            if sub_type == "approve" or sub_type == "invite":

                welcome_message = f"欢迎[CQ:at,qq={user_id}]入群"
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


async def WelcomeFarewell_main(websocket, msg):

    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)

    # 根据消息类型执行不同的函数，一般按照消息类型写不同的功能，这里一般只需要一个函数，删除多余即可
    # 如果需要多个函数，请使用asyncio.gather并发执行
    await handle_WelcomeFarewell_group_notice(websocket, msg)
