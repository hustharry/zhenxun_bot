import os
import random
import re

import ujson as json
from nonebot_plugin_alconna import UniMessage, UniMsg

from zhenxun.configs.config import BotConfig, Config
from zhenxun.configs.path_config import DATA_PATH, IMAGE_PATH
from zhenxun.services.log import logger
from zhenxun.utils.http_utils import AsyncHttpx
from zhenxun.utils.message import MessageUtils

from .utils import ai_message_manager

anime_data = json.load(open(DATA_PATH / "anime.json", "r", encoding="utf8"))

check_url = "https://v2.alapi.cn/api/censor/text"

pattern = re.compile("|".join(map(re.escape, anime_data.keys())))

async def get_chat_result(
    message: str, user_id: str, nickname: str
) -> UniMessage | None:
    """获取 AI 返回值，顺序： 特殊回复 -> OpenAI

    参数:
        text: 问题
        img_url: 图片链接
        user_id: 用户id
        nickname: 用户昵称

    返回
        str: 回答
    """
    text = message
    ai_message_manager.add_message(user_id, text)
    rst = None
    special_rst = await ai_message_manager.get_result(user_id, nickname)
    if special_rst:
        ai_message_manager.add_result(user_id, special_rst)
        return MessageUtils.build_message(special_rst)
    if len(text) < 7 and random.random() < 0.6:
        match = pattern.search(text)
        if match:
            key = match.group()
            logger.info(f"current key is {key} the text is {text}")
            rst = random.choice(anime_data[key]).replace("你", nickname)
            return rst
    if not rst:
        return None
    ai_message_manager.add_result(user_id, rst)
    return MessageUtils.build_message(rst)

def hello() -> UniMessage:
    """一些打招呼的内容"""
    result = random.choice(
        (
            "哦豁？！",
            "你好！Ov<",
            f"库库库，呼唤{BotConfig.self_nickname}做什么呢",
            "我在呢！",
            "呼呼，叫俺干嘛",
        )
    )
    img = random.choice(os.listdir(IMAGE_PATH / "zai"))
    return MessageUtils.build_message([IMAGE_PATH / "zai" / img, result])


def no_result() -> UniMessage:
    """
    没有回答时的回复
    """
    return MessageUtils.build_message(
        [
            random.choice(
                [
                    "你在说啥子？",
                    f"纯洁的{BotConfig.self_nickname}没听懂",
                    "下次再告诉你(下次一定)",
                    "你觉得我听懂了吗？嗯？",
                    "我！不！知！道！",
                ]
            ),
            IMAGE_PATH
            / "noresult"
            / random.choice(os.listdir(IMAGE_PATH / "noresult")),
        ]
    )

async def check_text(text: str) -> str:
    """ALAPI文本检测，主要针对青云客API，检测为恶俗文本改为无回复的回答

    参数:
        text: 回复

    返回:
        str: 检测文本
    """
    if not Config.get_config("alapi", "ALAPI_TOKEN"):
        return text
    params = {"token": Config.get_config("alapi", "ALAPI_TOKEN"), "text": text}
    try:
        data = (await AsyncHttpx.get(check_url, timeout=2, params=params)).json()
        if data["code"] == 200:
            if data["data"]["conclusion_type"] == 2:
                return ""
    except Exception as e:
        logger.error(f"检测违规文本错误...", e=e)
    return text
