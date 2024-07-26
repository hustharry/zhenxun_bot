import re
from typing import Any

from nonebot.adapters import Bot, Message
from nonebot.adapters.onebot.v11 import unescape
from nonebot.exception import FinishedException
from nonebot.internal.params import Arg, ArgStr
from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata
from nonebot.typing import T_State
from nonebot_plugin_alconna import AlconnaQuery, Arparma
from nonebot_plugin_alconna import Image as alcImage
from nonebot_plugin_alconna import Match, Query
from nonebot_plugin_alconna import Text as alcText
from nonebot_plugin_alconna import UniMsg
from nonebot_plugin_saa import Image, MessageFactory, Text
from nonebot_plugin_session import EventSession

from zhenxun.configs.config import Config
from zhenxun.configs.utils import PluginExtraData
from zhenxun.services.log import logger

from ._config import scope2int, type2int
from ._data_source import WordBankManage, get_answer, get_img_and_at_list, get_problem
from ._model import WordBank
from .command import _add_matcher, _del_matcher, _show_matcher, _update_matcher

base_config = Config.get("word_bank")


__plugin_meta__ = PluginMetadata(
    name="词库问答",
    description="自定义词条内容随机回复",
    usage="""
    usage：
        对指定问题的随机回答，对相同问题可以设置多个不同回答
        删除词条后每个词条的id可能会变化，请查看后再删除
        更推荐使用id方式删除
        问题回答支持的类型：at, image
        查看词条命令：群聊时为 群词条+全局词条，私聊时为 私聊词条+全局词条
        添加词条正则：添加词条(模糊|正则|图片)?问\s*?(\S*\s?\S*)\s*?答\s?(\S*)
        正则问可以通过$1类推()捕获的组
        指令：
            添加词条 ?[模糊|正则|图片]问...答...：添加问答词条，可重复添加相同问题的不同回答
            删除词条 [问题/下标] ?[下标]：删除指定词条指定或全部回答
            修改词条 [问题/下标] [新问题]：修改词条问题
            查看词条 ?[问题/下标]：查看全部词条或对应词条回答
            示例：添加图片词条问答嗨嗨嗨
                [图片]...
            示例：添加词条@萝莉 我来啦
            示例：添加词条问谁是萝莉答是我
            示例：添加词条正则问那个(.+)是萝莉答没错$1是萝莉
            示例：删除词条 谁是萝莉
            示例：删除词条 谁是萝莉 0
            示例：删除词条 id:0 1
            示例：修改词条 谁是萝莉 是你
            示例：修改词条 id:0 是你
            示例：查看词条
            示例：查看词条 谁是萝莉
            示例：查看词条 id:0    (群/私聊词条)
            示例：查看词条 gid:0   (全局词条)
    """.strip(),
    extra=PluginExtraData(
        author="HibiKier & yajiwa",
        version="0.1",
        superuser_help="""
    在私聊中超级用户额外设置
        指令：
            (全局|私聊)?添加词条\s*?(模糊|正则|图片)?问\s*?(\S*\s?\S*)\s*?答\s?(\S*)：添加问答词条，可重复添加相同问题的不同回答
            全局添加词条
            私聊添加词条
            （私聊情况下）删除词条: 删除私聊词条
            （私聊情况下）删除全局词条
            （私聊情况下）修改词条: 修改私聊词条
            （私聊情况下）修改全局词条
            用法与普通用法相同
        """,
        admin_level=base_config.get("WORD_BANK_LEVEL"),
    ).dict(),
)


@_add_matcher.handle()
async def _(
    bot: Bot,
    session: EventSession,
    state: T_State,
    message: UniMsg,
    reg_group: tuple[Any, ...] = RegexGroup(),
):
    img_list, at_list = get_img_and_at_list(message)
    user_id = session.id1
    group_id = session.id3 or session.id2
    if not group_id and user_id not in bot.config.superusers:
        await Text("权限不足捏...").finish(reply=True)
    word_scope, word_type, problem, answer = reg_group
    if not word_scope and not group_id:
        word_scope = "私聊"
    if (
        word_scope
        and word_scope in ["全局", "私聊"]
        and user_id not in bot.config.superusers
    ):
        await Text("权限不足，无法添加该范围词条...").finish(reply=True)
    if (not problem or not problem.strip()) and word_type != "图片":
        await Text("词条问题不能为空！").finish(reply=True)
    if (not answer or not answer.strip()) and not len(img_list) and not len(at_list):
        await Text("词条回答不能为空！").finish(reply=True)
    if word_type != "图片":
        state["problem_image"] = "YES"
    temp_problem = message.copy()
    # answer = message.copy()
    # 对at问题对额外处理
    # if at_list:
    answer = get_answer(message.copy())
    # text = str(message.pop(0)).split("答", maxsplit=1)[-1].strip()
    # temp_problem.insert(0, alcText(text))
    state["word_scope"] = word_scope
    state["word_type"] = word_type
    state["problem"] = get_problem(temp_problem)
    state["answer"] = answer
    logger.info(
        f"添加词条 范围: {word_scope} 类型: {word_type} 问题: {problem} 回答: {answer}",
        "添加词条",
        session=session,
    )


@_add_matcher.got("problem_image", prompt="请发送该回答设置的问题图片")
async def _(
    bot: Bot,
    session: EventSession,
    message: UniMsg,
    word_scope: str | None = ArgStr("word_scope"),
    word_type: str | None = ArgStr("word_type"),
    problem: str | None = ArgStr("problem"),
    answer: Any = Arg("answer"),
):
    if not session.id1:
        await Text("用户id不存在...").finish()
    user_id = session.id1
    group_id = session.id3 or session.id2
    try:
        if word_type == "图片":
            problem = [m for m in message if isinstance(m, alcImage)][0].url
        elif word_type == "正则" and problem:
            problem = unescape(problem)
            try:
                re.compile(problem)
            except re.error:
                await Text(f"添加词条失败，正则表达式 {problem} 非法！").finish(
                    reply=True
                )
        # if str(event.user_id) in bot.config.superusers and isinstance(event, PrivateMessageEvent):
        #     word_scope = "私聊"
        nickname = None
        if problem and bot.config.nickname:
            nickname = [nk for nk in bot.config.nickname if problem.startswith(nk)]
        if not problem:
            await Text("获取问题失败...").finish(reply=True)
        await WordBank.add_problem_answer(
            user_id,
            (
                group_id
                if group_id and (not word_scope or word_scope == "私聊")
                else "0"
            ),
            scope2int[word_scope] if word_scope else 1,
            type2int[word_type] if word_type else 0,
            problem,
            answer,
            nickname[0] if nickname else None,
            session.platform,
            session.id1,
        )
    except Exception as e:
        if isinstance(e, FinishedException):
            await _add_matcher.finish()
        logger.error(
            f"添加词条 {problem} 错误...",
            "添加词条",
            session=session,
            e=e,
        )
        await Text(
            f"添加词条 {problem if word_type != '图片' else '图片'} 发生错误！"
        ).finish(reply=True)
    if word_type == "图片":
        result = MessageFactory([Text("添加词条 "), Image(problem), Text(" 成功！")])
    else:
        result = Text(f"添加词条 {problem} 成功！")
    await result.send()
    logger.info(
        f"添加词条 {problem} 成功！",
        "添加词条",
        session=session,
    )


@_del_matcher.handle()
async def _(
    bot: Bot,
    session: EventSession,
    problem: Match[str],
    index: Match[int],
    answer_id: Match[int],
    arparma: Arparma,
    all: Query[bool] = AlconnaQuery("all.value", False),
):
    if not problem.available and not index.available:
        await Text("此命令之后需要跟随指定词条或id，通过“显示词条“查看").finish(
            reply=True
        )
    word_scope = 1 if session.id3 or session.id2 else 2
    if all.result:
        word_scope = 0
    if gid := session.id3 or session.id2:
        result, _ = await WordBankManage.delete_word(
            problem.result,
            index.result if index.available else None,
            answer_id.result if answer_id.available else None,
            gid,
            word_scope,
        )
    else:
        if session.id1 not in bot.config.superusers:
            await Text("权限不足捏...").finish(reply=True)
        result, _ = await WordBankManage.delete_word(
            problem.result,
            index.result if index.available else None,
            answer_id.result if answer_id.available else None,
            None,
            word_scope,
        )
    await Text(result).send(reply=True)
    logger.info(f"删除词条: {problem.result}", arparma.header_result, session=session)


@_update_matcher.handle()
async def _(
    bot: Bot,
    session: EventSession,
    replace: str,
    problem: Match[str],
    index: Match[int],
    arparma: Arparma,
    all: Query[bool] = AlconnaQuery("all.value", False),
):
    if not problem.available and not index.available:
        await Text("此命令之后需要跟随指定词条或id，通过“显示词条“查看").finish(
            reply=True
        )
    word_scope = 1 if session.id3 or session.id2 else 2
    if all.result:
        word_scope = 0
    if gid := session.id3 or session.id2:
        result, old_problem = await WordBankManage.update_word(
            replace,
            problem.result if problem.available else "",
            index.result if index.available else None,
            gid,
            word_scope,
        )
    else:
        if session.id1 not in bot.config.superusers:
            await Text("权限不足捏...").finish(reply=True)
        result, old_problem = await WordBankManage.update_word(
            replace,
            problem.result if problem.available else "",
            index.result if index.available else None,
            session.id3 or session.id2,
            word_scope,
        )
    await Text(result).send(reply=True)
    logger.info(
        f"更新词条词条: {old_problem} -> {replace}",
        arparma.header_result,
        session=session,
    )


@_show_matcher.handle()
async def _(
    session: EventSession,
    problem: Match[str],
    index: Match[int],
    gid: Match[str],
    arparma: Arparma,
    all: Query[bool] = AlconnaQuery("all.value", False),
):
    word_scope = 1 if session.id3 or session.id2 else 2
    if all.result:
        word_scope = 0
    group_id = session.id3 or session.id2
    if gid.available:
        group_id = gid.result
    if problem.available:
        if index.available:
            if index.result < 0 or index.result > len(
                await WordBank.get_problem_by_scope(2)
            ):
                await Text("id必须在范围内...").finish(reply=True)
        result = await WordBankManage.show_word(
            problem.result,
            index.result if index.available else None,
            group_id,
            word_scope,
        )
    else:
        result = await WordBankManage.show_word(
            None, index.result if index.available else None, group_id, word_scope
        )
    await result.send()
    logger.info(f"查看词条回答: {problem}", arparma.header_result, session=session)