import time
import re
from pathlib import Path
import ujson as json
from nonebot.plugin import PluginMetadata
from nonebot_plugin_alconna import Alconna, Args, Arparma, on_alconna
from nonebot_plugin_session import EventSession

from zhenxun.configs.utils import PluginExtraData
from zhenxun.services.log import logger
from zhenxun.utils.http_utils import AsyncHttpx
from zhenxun.utils.message import MessageUtils

from zhenxun.configs.path_config import TEMP_PATH

from nonebot import get_bot, get_driver, on_command
from nonebot.adapters import Message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import Arg, CommandArg
from nonebot.typing import T_State
from nonebot_plugin_apscheduler import scheduler
from zhenxun.utils.platform import broadcast_group

__plugin_meta__ = PluginMetadata(
    name="摸鱼日历",
    description="鲁迅说了啥？",
    usage="""
    摸鱼日历
    指令：
        摸鱼/摸鱼日历                          查看今天的摸鱼日历
        摸鱼/摸鱼日历+设置                 以连续对话的形式设置摸鱼日历的推送时间
        摸鱼/摸鱼日历+设置 小时:分钟  设置摸鱼日历的推送时间
        摸鱼/摸鱼日历+状态                 查看本群的摸鱼日历状态
        摸鱼/摸鱼日历+禁用                 查看本群的摸鱼日历状态 
    """.strip(),
    extra=PluginExtraData(
        author="XiaoYeZi",
        version="0.1",
    ).dict(),
)

_matcher = on_alconna(
    Alconna("moyu"),
    aliases={"摸鱼日历"},
    priority=5,
    block=True
)


# subscribe = Path(__file__).parent / "subscribe.json"

# subscribe_list = json.loads(subscribe.read_text("utf-8")) if subscribe.is_file() else {}


# def save_subscribe():
#     subscribe.write_text(json.dumps(subscribe_list), encoding="utf-8")

# driver = get_driver()

url = "https://api.03c3.cn/api/zb"

# async def get_calendar() -> None:
#     path = TEMP_PATH / f"moyu{int(time.time())}.jpeg"
#     await AsyncHttpx.download_file(url, path)
#     logger.info(f"发送摸鱼定时 {receipt}")
    

@_matcher.handle()
async def _(session: EventSession, arparma: Arparma):
    path = TEMP_PATH / f"moyu{int(time.time())}.jpeg"
    try:    
        logger.info("begin mo yu")
        await MessageUtils.build_message("小叶子带大家来摸鱼！").send()
        await AsyncHttpx.download_file(url, path)
        logger.info(f"每日图片下载路径 {path}")
        receipt = await MessageUtils.build_message(path).send()
        logger.info(f"发送摸鱼 {receipt}", arparma.header_result, session=session)
    except Exception as e:
        await MessageUtils.build_message("服务器被玩坏了...").send()
        logger.error(
            f"摸鱼接口错误",
            arparma.header_result,
            session=session,
            e=e,
        )

# 早上好
@scheduler.scheduled_job(
    "cron",
    hour=9,
    minute=1,
)
async def _():
    path = TEMP_PATH / f"moyu{int(time.time())}.jpeg"
    message = MessageUtils.build_message("小叶子带大家早上来摸鱼！")
    await broadcast_group(message, log_cmd="被动每日新闻")
    logger.info("每日摸鱼发送...")
    await AsyncHttpx.download_file(url, path)
    receipt = MessageUtils.build_message(path)
    await broadcast_group(receipt, log_cmd="被动每日新闻")
    logger.info(f"发送摸鱼 {receipt}")

# @driver.on_startup
# async def subscribe_jobs():
#     for group_id, info in subscribe_list.items():
#         scheduler.add_job(
#             get_calendar,
#             "cron",
#             args=[group_id],
#             id=f"moyu_calendar_{group_id}",
#             replace_existing=True,
#             hour=info["hour"],
#             minute=info["minute"],
#         )


# def calendar_subscribe(group_id: str, hour: str, minute: str) -> None:
#     subscribe_list[group_id] = {"hour": hour, "minute": minute}
#     save_subscribe()
#     scheduler.add_job(
#         get_calendar,
#         "cron",
#         args=[group_id],
#         id=f"moyu_calendar_{group_id}",
#         replace_existing=True,
#         hour=hour,
#         minute=minute,
#     )
#     logger.debug(f"群[{group_id}]设置摸鱼日历推送时间为：{hour}:{minute}")


# moyu_matcher = on_command("摸鱼日历设置", aliases={"摸鱼设置"})


# @moyu_matcher.handle()
# async def moyu(
#     event: GroupMessageEvent, matcher: Matcher, args: Message = CommandArg()
# ):
#     if cmdarg := args.extract_plain_text():
#         if "状态" in cmdarg:
#             push_state = scheduler.get_job(f"moyu_calendar_{event.group_id}")
#             moyu_state = "摸鱼日历状态：\n每日推送: " + ("已开启" if push_state else "已关闭")
#             if push_state:
#                 group_id_info = subscribe_list[str(event.group_id)]
#                 moyu_state += (
#                     f"\n推送时间: {group_id_info['hour']}:{group_id_info['minute']}"
#                 )
#             await matcher.finish(moyu_state)
#         elif "设置" in cmdarg or "推送" in cmdarg:
#             if ":" in cmdarg or "：" in cmdarg:
#                 matcher.set_arg("time_arg", args)
#         elif "禁用" in cmdarg or "关闭" in cmdarg:
#             del subscribe_list[str(event.group_id)]
#             save_subscribe()
#             scheduler.remove_job(f"moyu_calendar_{event.group_id}")
#             await matcher.finish("摸鱼日历推送已禁用")
#         else:
#             await matcher.finish("摸鱼日历的参数不正确")


# @moyu_matcher.got("time_arg", prompt="请发送每日定时推送日历的时间，格式为：小时:分钟")
# async def handle_time(
#     event: GroupMessageEvent, state: T_State, time_arg: Message = Arg()
# ):
#     state.setdefault("max_times", 0)
#     time = time_arg.extract_plain_text()
#     if any(cancel in time for cancel in ["取消", "放弃", "退出"]):
#         await moyu_matcher.finish("已退出摸鱼日历推送时间设置")
#     match = re.search(r"(\d*)[:：](\d*)", time)
#     if match and match[1] and match[2]:
#         calendar_subscribe(str(event.group_id), match[1], match[2])
#         await moyu_matcher.finish(f"摸鱼日历的每日推送时间已设置为：{match[1]}:{match[2]}")
#     else:
#         state["max_times"] += 1
#         if state["max_times"] >= 3:
#             await moyu_matcher.finish("你的错误次数过多，已退出摸鱼日历推送时间设置")
#         await moyu_matcher.reject("设置时间失败，请输入正确的格式，格式为：小时:分钟")
