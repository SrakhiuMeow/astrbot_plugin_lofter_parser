import json
import re

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


    async def initialize(self):
        logger.info("Lofter Parser Plugin is initializing...")
        try:
            import brotli
            logger.info("检测到brotli：", brotli.__version__)
        except ImportError:
            logger.error("Brotli未安装，可能是自动安装失败。请手动安装Brotli后重启Astrbot.")
            return None
        logger.info("Lofter解析插件初始化完成.")


    async def _save_tmp(self, result: dict):
        """将结果保存到临时文件，返回文件路径列表"""
        file_paths = []
        json.dump(result, open("lofter_tmp.json", "w", encoding="utf-8"), ensure_ascii=False, indent=4)
        return file_paths


    @filter.event_message_type(filter.EventMessageType.ALL, priority=10)
    async def auto_parse_lofter(self, event: AstrMessageEvent, *args, **kwargs):
        """自动解析 Lofter 链接的消息处理器"""
        if (event is None) or (not hasattr(event, "message_str")):
            print("No message_str attribute in event.")
            return
        message_str = event.message_str
        message_obj_str = str(event.message_obj)

        cookie = self.lofter_cookie if hasattr(self, "lofter_cookie") else ""
        pattern = r"[a-zA-Z0-9-_]+\.lofter\.com/post/[a-zA-Z0-9-_]+"

        # 检查是否是回复消息，如果是则忽略
        if re.search(r"reply", message_str):
            return

        matches = re.search(pattern,message_obj_str) or re.search(pattern, message_str)

        if not (matches):
            return

        for match in matches.groups():
            result = await get_post("https://"+match, cookie, timeout=15)
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
