# script/WelcomeFarewell/main.py

import time
import logging
import os
import sys
import asyncio
import json
import sqlite3
import re

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

# 数据库路径
DB_PATH = os.path.join(DATA_DIR, "welcome_farewell.db")


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
def load_status(group_id, feature):
    return load_switch(group_id, feature)


# 保存功能开关状态
def save_status(group_id, feature, status):
    save_switch(group_id, feature, status)


# 保存自定义消息
def save_custom_message(group_id, feature, message):
    with open(
        os.path.join(DATA_DIR, f"{group_id}_{feature}.txt"), "w", encoding="utf-8"
    ) as file:
        file.write(message)


# 加载自定义消息
def load_custom_message(group_id, feature):
    try:
        with open(
            os.path.join(DATA_DIR, f"{group_id}_{feature}.txt"), "r", encoding="utf-8"
        ) as file:
            return file.read()
    except FileNotFoundError:
        return None


# 保存入群时间到数据库
def save_join_time(group_id, user_id, join_time):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO join_times (group_id, user_id, join_time)
            VALUES (?, ?, ?)
        """,
            (group_id, user_id, join_time),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logging.error(f"记录{group_id}入群时间失败: {e}")
        return None


# 读取入群时间
def load_join_time(group_id, user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT join_time FROM join_times
            WHERE group_id = ? AND user_id = ?
        """,
            (group_id, user_id),
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
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

    # 菜单
    if raw_message == "welcomefarewell":
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:reply,id={message_id}]WelcomeFarewell 总菜单\n\n"
            "1. 功能开关命令\n"
            "   wfon: 开启入群欢迎\n"
            "   wfoff: 关闭入群欢迎\n"
            "   ffon: 开启退群欢送\n"
            "   ffoff: 关闭退群欢送\n\n"
            "2. 自定义消息设置\n"
            "   welcomeset <自定义欢迎词>: 设置自定义入群欢迎词\n"
            "   farewellset <自定义欢送词>: 设置自定义退群欢送词\n\n"
            "3. 功能描述\n"
            "   入群欢迎: 当新成员加入群聊时，发送欢迎消息\n"
            "   退群欢送: 当成员离开群聊时，发送欢送消息\n\n"
            "4. 注意事项\n"
            "   只有管理员或群主可以使用以上命令\n"
            "   自定义消息中可以包含 CQ 码\n"
            "   系统会自动记录成员的入群时间和退群时间\n\n"
            "5. 其他功能\n"
            "   黑名单检测: 当入群时，如果用户在黑名单中，则不发送欢迎词，并且直接踢出",
        )

    if is_authorized(role, user_id):
        if raw_message == "wfon":
            if load_status(group_id, "欢迎"):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]入群欢迎已经开启了，无需重复开启。",
                )
            else:
                save_status(group_id, "欢迎", True)
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]已开启入群欢迎。",
                )
        elif raw_message == "wfoff":
            if not load_status(group_id, "欢迎"):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]入群欢迎已经关闭了，无需重复关闭。",
                )
            else:
                save_status(group_id, "欢迎", False)
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]已关闭入群欢迎。",
                )
        elif raw_message == "ffon":
            if load_status(group_id, "欢送"):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]退群欢送已经开启了，无需重复开启。",
                )
            else:
                save_status(group_id, "欢送", True)
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]已开启退群欢送。",
                )
        elif raw_message == "ffoff":
            if not load_status(group_id, "欢送"):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]退群欢送已经关闭了，无需重复关闭。",
                )
            else:
                save_status(group_id, "欢送", False)
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]已关闭退群欢送。",
                )
        elif raw_message.startswith("welcomeset"):
            custom_message = raw_message[len("welcomeset") :].strip()
            save_custom_message(group_id, "welcome", custom_message)
            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]已设置自定义欢迎词\n欢迎词为：{custom_message}",
            )
        elif raw_message.startswith("farewellset"):
            custom_message = raw_message[len("farewellset") :].strip()
            save_custom_message(group_id, "farewell", custom_message)
            await send_group_msg(
                websocket,
                group_id,
                f"[CQ:reply,id={message_id}]已设置自定义欢送词\n欢送词为：{custom_message}",
            )


# 初始化数据库
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS join_times (
            group_id TEXT,
            user_id TEXT,
            join_time TEXT,
            PRIMARY KEY (group_id, user_id)
        )
    """
    )
    conn.commit()
    conn.close()


# 群通知处理函数
async def handle_WelcomeFarewell_group_notice(websocket, msg):
    try:
        # 确保数据目录存在
        os.makedirs(DATA_DIR, exist_ok=True)

        init_db()

        user_id = str(msg.get("user_id"))
        group_id = str(msg.get("group_id"))
        sub_type = str(msg.get("sub_type"))
        notice_type = str(msg.get("notice_type"))

        # 限定范围，只处理入群和退群事件
        if notice_type != "group_increase" and notice_type != "group_decrease":
            return

        # 检查是否在黑名单，如果在黑名单，则不发送欢迎词
        if is_blacklisted(group_id, user_id):
            return

        if load_status(group_id, "欢迎") and notice_type == "group_increase":

            join_time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            save_join_time(group_id, user_id, join_time_str)

            custom_welcome_message = load_custom_message(group_id, "welcome")
            if custom_welcome_message:
                welcome_message = f"欢迎[CQ:at,qq={user_id}]入群\n{custom_welcome_message}\n入群时间：{join_time_str}"
            else:
                welcome_message = (
                    f"欢迎[CQ:at,qq={user_id}]入群\n入群时间：{join_time_str}"
                )
            welcome_message = re.sub(r"&#91;", "[", welcome_message)
            welcome_message = re.sub(r"&#93;", "]", welcome_message)
            await send_group_msg(websocket, group_id, welcome_message)

        elif load_status(group_id, "欢送") and notice_type == "group_decrease":
            join_time_str = load_join_time(group_id, user_id)

            if sub_type == "kick":
                farewell_message = f"{user_id} 已被踢出群聊🎉🎉🎉"
                if farewell_message:
                    await send_group_msg(websocket, group_id, farewell_message)

            elif sub_type == "leave":
                custom_farewell_message = load_custom_message(group_id, "farewell")
                if custom_farewell_message:
                    farewell_message = f"{user_id} 离开了这个群\n{custom_farewell_message}\n入群时间{join_time_str}\n退群时间{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
                else:
                    farewell_message = f"{user_id} 离开了这个群\n入群时间{join_time_str}\n退群时间{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
                if farewell_message:
                    farewell_message = re.sub(r"&#91;", "[", farewell_message)
                    farewell_message = re.sub(r"&#93;", "]", farewell_message)
                    await send_group_msg(websocket, group_id, farewell_message)

    except Exception as e:
        logging.error(f"处理WelcomeFarewell群通知失败: {e}")
        return


# 统一事件处理入口
async def handle_events(websocket, msg):
    """统一事件处理入口"""
    try:
        # 处理回调事件
        if msg.get("status") == "ok":
            return

        post_type = msg.get("post_type")

        # 处理元事件
        if post_type == "meta_event":
            return

        # 处理消息事件
        elif post_type == "message":
            message_type = msg.get("message_type")
            if message_type == "group":
                group_id = str(msg.get("group_id", ""))
                message_id = str(msg.get("message_id", ""))
                raw_message = str(msg.get("raw_message", ""))
                user_id = str(msg.get("user_id", ""))
                role = str(msg.get("sender", {}).get("role", ""))

                # 处理欢迎词相关命令
                if raw_message.startswith("welcome") or raw_message.startswith("欢迎"):
                    # TODO: 实现欢迎词相关命令处理
                    pass
            elif message_type == "private":
                return

        # 处理通知事件
        elif post_type == "notice":
            if msg.get("notice_type") == "group":
                user_id = str(msg.get("user_id"))
                group_id = str(msg.get("group_id"))
                sub_type = str(msg.get("sub_type"))
                notice_type = str(msg.get("notice_type"))

                # 限定范围，只处理入群和退群事件
                if notice_type == "group_increase" or notice_type == "group_decrease":
                    # 检查是否在黑名单，如果在黑名单，则不发送欢迎词
                    if not is_blacklisted(group_id, user_id):
                        if (
                            load_status(group_id, "欢迎")
                            and notice_type == "group_increase"
                        ):
                            join_time_str = time.strftime(
                                "%Y-%m-%d %H:%M:%S", time.localtime()
                            )
                            save_join_time(group_id, user_id, join_time_str)

                            custom_welcome_message = load_custom_message(
                                group_id, "welcome"
                            )
                            if custom_welcome_message:
                                welcome_message = f"欢迎[CQ:at,qq={user_id}]入群\n{custom_welcome_message}\n入群时间：{join_time_str}"
                            else:
                                welcome_message = f"欢迎[CQ:at,qq={user_id}]入群\n入群时间：{join_time_str}"
                            welcome_message = re.sub(r"&#91;", "[", welcome_message)
                            welcome_message = re.sub(r"&#93;", "]", welcome_message)
                            await send_group_msg(websocket, group_id, welcome_message)

                        elif (
                            load_status(group_id, "欢送")
                            and notice_type == "group_decrease"
                        ):
                            join_time_str = load_join_time(group_id, user_id)

                            if sub_type == "kick":
                                farewell_message = f"{user_id} 已被踢出群聊🎉🎉🎉"
                                if farewell_message:
                                    await send_group_msg(
                                        websocket, group_id, farewell_message
                                    )

                            elif sub_type == "leave":
                                custom_farewell_message = load_custom_message(
                                    group_id, "farewell"
                                )
                                if custom_farewell_message:
                                    farewell_message = f"{user_id} 离开了这个群\n{custom_farewell_message}\n入群时间{join_time_str}\n退群时间{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
                                else:
                                    farewell_message = f"{user_id} 离开了这个群\n入群时间{join_time_str}\n退群时间{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}"
                                if farewell_message:
                                    farewell_message = re.sub(
                                        r"&#91;", "[", farewell_message
                                    )
                                    farewell_message = re.sub(
                                        r"&#93;", "]", farewell_message
                                    )
                                    await send_group_msg(
                                        websocket, group_id, farewell_message
                                    )

    except Exception as e:
        error_type = {
            "message": "消息",
            "notice": "通知",
            "request": "请求",
            "meta_event": "元事件",
        }.get(post_type, "未知")

        logging.error(f"处理WelcomeFarewell{error_type}事件失败: {e}")

        # 发送错误提示
        if post_type == "message":
            message_type = msg.get("message_type")
            if message_type == "group":
                await send_group_msg(
                    websocket,
                    msg.get("group_id"),
                    f"处理WelcomeFarewell{error_type}事件失败，错误信息：{str(e)}",
                )
            elif message_type == "private":
                await send_private_msg(
                    websocket,
                    msg.get("user_id"),
                    f"处理WelcomeFarewell{error_type}事件失败，错误信息：{str(e)}",
                )
