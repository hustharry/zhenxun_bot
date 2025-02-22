import contextlib
from typing import Annotated
from nonebot.adapters import Message
from nonebot.exception import ActionFailed
from nonebot.params import CommandArg, EventMessage
from nonebot.internal.matcher import current_event
from nonebot.plugin.on import on_message
from nonebot.rule import command, to_me

from zhenxun.plugins.nonebot_plugin_sparkapi.API.SparkApi import request_chat
from zhenxun.plugins.nonebot_plugin_sparkapi.config import conf
from zhenxun.plugins.nonebot_plugin_sparkapi.funcs import SessionID, solve_at

from typing import List
import re
import ujson as json
from nonebot import on_message
from nonebot_plugin_alconna import UniMsg
from nonebot_plugin_session import EventSession
from nonebot_plugin_userinfo import EventUserInfo, UserInfo
from zhenxun.configs.config import BotConfig, Config
from zhenxun.configs.path_config import DATA_PATH, IMAGE_PATH
from zhenxun.configs.utils import PluginExtraData, RegisterConfig
from zhenxun.models.friend_user import FriendUser
from zhenxun.models.group_member_info import GroupInfoUser
from zhenxun.services.log import logger
from zhenxun.utils.depends import UserName
from zhenxun.utils.message import MessageUtils

from ..data_source import get_chat_result, hello, no_result


command_chat = conf.sparkapi_command_chat
priority = conf.sparkapi_priority + 2
max_length = conf.sparkpai_model_maxlength
fl_notice = conf.sparkapi_fl_notice

rule = (to_me() & command(command_chat)) if command_chat else to_me()
matcher_chat = on_message(rule=rule, priority=priority, block=True)
Arg = Annotated[Message, CommandArg() if command_chat else EventMessage()]


@matcher_chat.handle()
async def _(session_id: SessionID, arg: Arg, uname: str = UserName()):
    question = arg.extract_plain_text().strip()
    event = current_event.get()
    user_id = event.get_user_id()
    if not question or question in [
        "你好啊",
        "你好",
        "在吗",
        "在不在",
        "您好",
        "您好啊",
        "在",
        "喂喂喂"
    ]:
        await hello().finish()
    if not user_id:
        await MessageUtils.build_message("用户id不存在...").finish()

    result = await get_chat_result(question, user_id, uname)
    logger.info(f"问题：{question} ---- 回答：{result}", "ai", session=user_id)
    if result:
        result = str(result)
        await MessageUtils.build_message(result).finish()
    else: 
        receipt = await solve_at("正在思考中...").send() if fl_notice else None
        try:
            answer = await request_chat(session_id, question)
        except Exception as e:
            answer = f"好像出错了捏！敲敲叶子。\n错误信息：{type(e)}: {e}"

        if receipt is not None and receipt.recallable:
            with contextlib.suppress(ActionFailed):
                await receipt.recall()
        await solve_at(answer).finish()

        if answer is None:
            await no_result().finish()
