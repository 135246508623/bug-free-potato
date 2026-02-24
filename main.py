from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

@register("getkey", "YourName", "Delta 卡密获取插件", "1.0.0")
class GetKeyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        pass

    @filter.command("getkey")
    async def getkey(self, event: AstrMessageEvent):
        """处理 /getkey 指令"""
        yield event.plain_result("检测到您的Delta卡密开始解析")

    async def terminate(self):
        pass
