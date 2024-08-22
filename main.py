# script/WelcomeFarewell/main.py

import time
import logging
import os
import sys
import asyncio
import json

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.config import owner_id
from app.api import *
from app.switch import load_switch, save_switch
from app.scripts.BlacklistSystem.main import is_blacklisted

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


def save_join_time(group_id, user_id, join_time):
    file_path = os.path.join(DATA_DIR, f"{group_id}.json")
    try:
        # 确保文件存在
        if not os.path.exists(file_path):
            data = {}
        else:
            # 读取现有数据
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)

        # 更新数据
        data[user_id] = join_time

        # 保存数据
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file)
    except Exception as e:
        logging.error(f"记录{group_id}入群时间失败: {e}")
        return None


# 读取入群时间
def load_join_time(group_id, user_id):
    file_path = os.path.join(DATA_DIR, f"{group_id}.json")
    try:
        # 如果文件不存在,创建一个空的JSON文件
        if not os.path.exists(file_path):
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump({}, file)

        # 读取文件内容
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get(str(user_id), None)
    except Exception as e:
        logging.error(f"读取{group_id}入群时间失败: {e}")
        return None


# 入群欢迎退群欢送管理函数
async def WelcomeFarewell_manage(websocket, msg):
    user_id = str(msg.get("user_id"))
    group_id = str(msg.get("group_id"))
    raw_message = str(msg.get("raw_message"))
    message_id = msg.get("message_id")
    role = str(msg.get("sender", {}).get("role"))

    # 开启入群欢迎
    if is_authorized(role, user_id):
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

        user_id = str(msg.get("user_id"))
        group_id = str(msg.get("group_id"))
        sub_type = str(msg.get("sub_type"))

        # 检查是否在黑名单，如果在黑名单，则不发送欢迎词
        if is_blacklisted(group_id, user_id):
            return

        if load_WelcomeFarewell_status(group_id):
            if sub_type == "approve" or sub_type == "invite":
                join_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                save_join_time(group_id, user_id, join_time_str)
                welcome_message = f"欢迎[CQ:at,qq={user_id}]入群\n{load_custom_welcome_message(group_id)}\n入群时间：{join_time_str}"
                welcome_message = welcome_message.replace("&#91;", f"[")
                welcome_message = welcome_message.replace("&#93;", f"]")
                await send_group_msg(websocket, group_id, welcome_message)
            else:
                stranger_info = await get_stranger_info(websocket, user_id)
                nickname = stranger_info.get("data", {}).get("nick", None)
                if sub_type == "kick":
                    farewell_message = f"<{nickname}>{user_id} 已被踢出群聊🎉🎉🎉"
                    if farewell_message:
                        await send_group_msg(websocket, group_id, f"{farewell_message}")

                elif sub_type == "leave":
                    farewell_message = f"<{nickname}>{user_id} 离开了这个群\n入群时间{load_join_time(group_id, user_id)}\n退群时间{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
                    if farewell_message:
                        await send_group_msg(websocket, group_id, f"{farewell_message}")

    except Exception as e:
        logging.error(f"处理WelcomeFarewell群通知失败: {e}")
        return
