import asyncio
import traceback

import aiohttp
from bs4 import BeautifulSoup
from bs4.element import Tag

from astrbot.api import logger


async def get_post(pageUrl: str, lofter_cookie: str, *, timeout: int = 10) -> dict | None:
    """
    异步获取 Lofter 帖子内容并解析
    Args:
        pageUrl: Lofter 帖子 URL
        lofter_cookie: 用于访问 Lofter 的 Cookie 字符串
        timeout: 请求超时时间，单位秒，默认值为 10 秒
    """

    timeout_obj = aiohttp.ClientTimeout(total=timeout)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:145.0) Gecko/20100101 Firefox/145.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Cookie": lofter_cookie,
        "Accept-Encoding": "gzip, deflate, br, zstd",
    }

    try:
        async with aiohttp.ClientSession(headers=headers, timeout=timeout_obj) as session:
            async with session.get(pageUrl) as resp:
                resp.raise_for_status()
                text = await resp.text()

        # 解析页面内容，截取其中class="content"的div
        soup = BeautifulSoup(text, "html.parser")
        content_div = soup.find("div", class_="content")
        if not isinstance(content_div, Tag):
            return None
        logger.info("Lofter网页抓取成功.")

        # 将图片提取出来
        images = []
        for img in content_div.find_all("img"):
            if not isinstance(img, Tag):
                continue
            src = img.get("src") or img.get("data-src")
            if isinstance(src, str):
                src = src.split("?")[0]  # 去掉URL参数
                images.append(src)

        # TODO: 处理视频内容
        videos = []

        result = {
            "html": str(content_div),
            "text": content_div.get_text(separator="\n", strip=True),
            "images": images,
            "videos": videos
        }
        return result

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        traceback.print_exc()
        logger.error("获取或解析Lofter帖子时出错: %s: %s", type(e).__name__, e)
        return None
