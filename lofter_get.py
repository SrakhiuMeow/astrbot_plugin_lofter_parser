import asyncio
from functools import partial

import aiohttp
from bs4 import BeautifulSoup
from bs4.element import Tag

from astrbot.api import logger


async def get_post(
    pageUrl: str, lofter_cookie: str, *, timeout: int = 10
) -> dict | None:
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
        async with aiohttp.ClientSession(
            headers=headers, timeout=timeout_obj
        ) as session:
            async with session.get(pageUrl) as resp:
                resp.raise_for_status()
                text = await resp.text()

        # 解析页面内容
        soup = await asyncio.get_running_loop().run_in_executor(
            None, partial(BeautifulSoup, text, "html.parser")
        )

        # Try multiple selectors for Lofter content area; the HTML class varies
        # by theme / post type (no single "content" class exists across themes).
        content_div = None
        for selector in (
            "div.ctc",  # content container (older themes) — must precede div.text
            "div.ct",  # content area (older themes)
            "div.m-detail",  # detail page container
            "div.m-postdtl",  # post detail wrapper (some themes)
            "div.content",  # generic content class (some themes)
            "div.text",  # main text block (fallback, lowest priority)
        ):
            candidate = soup.select_one(selector)
            if isinstance(candidate, Tag):
                content_div = candidate
                break

        if content_div is None:
            logger.warning(
                "无法在页面中找到内容区域，页面可能使用了未适配的主题。URL: %s", pageUrl
            )
            return None

        logger.info("Lofter网页抓取成功.")

        # 将图片提取出来
        images = []
        for img in content_div.find_all("img"):
            if not isinstance(img, Tag):
                continue
            # Prefer data-origin (full-res), then src, then data-src
            src = img.get("data-origin") or img.get("src") or img.get("data-src")
            if isinstance(src, str):
                src = src.split("?")[0]  # 去掉URL参数
                images.append(src)

        # 将视频提取出来
        videos = []
        for video in content_div.find_all("video"):
            if not isinstance(video, Tag):
                continue
            src = video.get("src")
            poster = video.get("poster")
            if isinstance(src, str):
                video_info = {"src": src}
                if isinstance(poster, str):
                    video_info["poster"] = poster.split("?")[0]
                videos.append(video_info)

        result = {
            "html": str(content_div),
            "text": content_div.get_text(separator="\n", strip=True),
            "images": images,
            "videos": videos,
        }
        return result

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.error(
            "获取或解析Lofter帖子时出错: %s: %s", type(e).__name__, e, exc_info=True
        )
        return None
