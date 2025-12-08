import re

import brotli

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register

from .lofter_get import get_post


@register(
    "astrbot_plugin_lofter_parser",
    "SrakhiuMeow",
    "可以解析lofter链接，提取文字和图片内容",
    "1.0",
)
class AstrbotPluginLofterParser(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.lofter_cookie = config.get("lofter_cookie", "")
        self.pattern = re.compile(r"[a-zA-Z0-9-_]+\.lofter\.com/post/[a-zA-Z0-9-_]+")
        logger.info("brotli version: %s", brotli.__version__)

    @filter.event_message_type(filter.EventMessageType.ALL, priority=10)
    async def auto_parse_lofter(self, event: AstrMessageEvent, *args, **kwargs):
        """自动解析 Lofter 链接的消息处理器"""
        if (event is None) or (not hasattr(event, "message_str")):
            return

        message_str = event.message_str
        message_obj_str = str(event.message_obj)

        cookie = self.lofter_cookie if hasattr(self, "lofter_cookie") else ""

        # 检查是否是回复消息，如果是则忽略
        if re.search(r"reply", message_str):
            return

        matches = re.search(self.pattern, message_obj_str) or re.search(self.pattern, message_str)

        if not (matches):
            return

        logger.info("检测到Lofter URL: %s", matches.group(0))
        result = await get_post("https://" + matches.group(0), cookie, timeout=15)
        logger.info("Lofter Parser result: %s", result)
        if result:
            images = result.get("images", [])
            text = result.get("text", "")
            chain = [
                Comp.At(qq=event.get_sender_id()),  # At 消息发送者
                Comp.Plain(text)
                ] + [
                Comp.Image.fromURL(url) for url in images  # 从 URL 发送图片
                ]
            yield event.chain_result(chain)
