"""
KUS Announcement Monitor system.
Monitoring: http://www.kus.ku.ac.th/news.php
Made by Tpmonkey
"""

from discord.ext.commands import (
    Cog, Context, command, is_owner, has_permissions, BucketType
)
from discord.ext.commands import cooldown as cd
from discord.ext.tasks import loop
from discord import Embed, Colour

import config
from bot import Bot
from utils.utils import limit

from datetime import datetime
from bs4 import BeautifulSoup
import traceback
import logging

log = logging.getLogger(__name__)

MAIN_URL = config.main_url
NEWS_URL = config.news_url

COOLDOWN = config.kus_news_cooldown

class KUSNews(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.data = None
        self.ids = None
        self.channels = None
        self.enable = True
        self.looping.start()
    
    def cog_unload(self):
        self.looping.cancel()
    
    async def save(self) -> None:
        await self.bot.database.dump("NEWS-CHANNELS", self.channels)
        log.debug('saved news channels')
    
    async def load_data(self) -> None:
        self.channels = await self.bot.database.load("NEWS-CHANNELS")
        self.ids = await self.bot.database.load("NEWS-IDS")
        log.debug('loaded data')

    async def __fetch__(self):
        r = await self.bot.trust_session.get(NEWS_URL)
        return await r.text()
    
    async def __get__data(self):
        respone_text = await self.__fetch__()

        soup = BeautifulSoup(respone_text, "html.parser")
        home = soup.find(attrs={"class":"home-news"})

        if home is None and self.enable:
            self.enable = False
            await self.bot.log(__name__, 'Unable to fetch kus data, disabled system.')
            return None
        elif home is None and not self.enable:
            self.enable = True
            await self.bot.log(__name__, 'successfully fecthed kus data, enabled system.')

        news = home.find_all("div", attrs={"class":"headline left"})
        pics = home.find_all("div", attrs={"class":"img-container left"})

        return [
            ( 
                new.get_text(), 
                new.find('a').get("href"), 
                MAIN_URL + pic.find("img").get("src"),
                new.find('a').get("href")
            ) for new, pic in zip(news, pics)
        ]
    
    @loop(hours=COOLDOWN)
    async def looping(self) -> None:
        if self.channels is None: await self.load_data()
        
        self.data = await self.__get__data()

        # Sometimes, website prevend bot to acces.
        if not self.enable:
            log.debug('trying to update news but is not enable, passing...')
            return

        news = {id: (n, u, p) for n, u, p, id in self.data}
        new_ids = [i for n, u, p, i in self.data]

        # If the existing data in database is not the same as present one.
        if new_ids != self.ids:
            await self.bot.log(__name__, "New data detected")
            await self.bot.log(__name__, 
                f"\n**From** `{self.ids}`" \
                f"\n**To** `{new_ids}`")

            # Remove all prevoius data.
            for _ in self.ids:
                if _ in new_ids: new_ids.remove(_)
            
            datas = [news[key] for key in new_ids] 
            embeds = [self.create_embed(n, u, p) for n, u, p in datas]
            await self.bot.log(__name__, f"**Found:** {datas}")

            if len(embeds) != 0:
                for _ in self.channels:
                    channel = self.bot.get_channel(_)
                    if channel is None: continue
                    await self.bot.log(__name__, f"Sending news to {channel}//{_}")

                    # Send news
                    for embed in embeds[::-1]:
                        try: await channel.send(embed=embed)
                        except:
                            await self.bot.log(__name__, 
                                f":negative_squared_cross_mark: Unable to send news embed to `{channel}`" \
                                f"with traceback: \n{traceback.format_exc()}")
                            break        
                        
                await self.bot.log(__name__, f"Sended news to all channels. (Total of {len(self.channels)})")
            else:
                await self.bot.log(__name__, "Ghost-News detected, No messages were sended.")
            
            ids = [id for n, u, p, id in self.data]
            await self.bot.database.dump("NEWS-IDS", ids)
            self.ids = ids
            await self.bot.log(__name__, "Saved new data.")
    
    def create_embed_(self, name, url, pic) -> Embed:        
        embed = Embed(
            colour = Colour.from_rgb(170, 3, 250),
            description = name.replace("...อ่านต่อ", f"[...อ่านต่อ]({url})"),
            timestamp = datetime.utcnow()
        )
        embed.set_author(name = "ข่าวประชาสัมพันธ์", url = MAIN_URL, icon_url= MAIN_URL + "images_kus/kus_logo.png")
        embed.set_thumbnail(url=pic)
        embed.set_footer(text = "โรงเรียนสาธิตแห่งมหาวิทยาลัยเกษตรศาสตร์")

        return embed
    
    def create_embed(self, name, url, pic) -> Embed:
        if url.startswith("news_detail"): url = MAIN_URL + url
        
        embed = Embed(
            colour = Colour.from_rgb(170, 3, 250),
            description = name.replace("...อ่านต่อ", f"[...อ่านต่อ]({url})"),
            timestamp = datetime.utcnow()
        )
        embed.set_author(
            name = "ข่าวประชาสัมพันธ์", 
            url = MAIN_URL, 
            icon_url= MAIN_URL + "images_kus/kus_logo.png"
        )
        embed.set_image(url=pic)
        embed.set_footer(text = "โรงเรียนสาธิตแห่งมหาวิทยาลัยเกษตรศาสตร์")

        return embed
    
    @command(name="set-news")
    @has_permissions(manage_guild=True)
    @cd(1, 20)
    async def set_news(self, ctx: Context) -> None:
        """Add News-Channel, Run this on it"""
        channel_id = ctx.channel.id

        if channel_id in self.channels:
            await ctx.send(":x: **Already added.**")
            return
        
        self.channels.append(channel_id)
        await ctx.send("Added Channel.")
        await self.save()
        await self.bot.log(__name__, f"New news Channel has been added, {ctx.channel}//{channel_id}")
    
    @command(name="remove-news")
    @has_permissions(manage_guild=True)
    @cd(1, 20)
    async def remove_news(self, ctx: Context) -> None:
        """Remove News-Channel, Run this on it."""
        channel_id = ctx.channel.id

        if channel_id not in self.channels:
            await ctx.send(":x: **Already removed.**")
            return
        
        self.channels.remove(channel_id)
        await ctx.send("Removed Channel.")
        await self.save()
        await self.bot.log(__name__, f"New news Channel has been removed, {ctx.channel}//{channel_id}")
    
    @command(name="news")
    @cd(1, 30, BucketType.guild)
    async def news_embed(self, ctx: Context, amount: int = 3) -> None:
        """Show 3 Newest Announcements."""
        if not self.enable:
            embed = Embed(
                title = "คำสั่งนี้ ได้ถูกปิดการใช้งานชั่วคราว",
                description = f"เนื่องจากทางโรงเรียน มีการจำกัดการเข้าใช้งานของบอทไว้ \nจึงไม่สามารถดึงข้อมูลดังกล่าวได้\n\nหากต้องการอ่านประชาสัมพันธ์ สามารถคลิกได้[ที่นี่]({NEWS_URL})",
                timestamp = ctx.message.created_at,
                colour = Colour.from_rgb(170, 3, 250)
            )
            await ctx.send(embed=embed)
            return
        elif self.data is None:
            await ctx.send("กำลังโหลดข้อมูล - กรุณารอสักครู่...")
            return

        amount = limit(amount, 1, 10)
        embeds = [self.create_embed(n, u, p) for n, u, p, id in self.data]
        for _ in range(amount):
            await ctx.send(embed=embeds[_])
    
    @command(name="embeds")
    @is_owner()
    async def embeds_(self, ctx: Context) -> None:
        """Admin command for test embeds."""
        n, u, p, id = self.data[0]
        embed1 = self.create_embed(n, u, p)
        embed2 = self.create_embed_(n, u, p)

        await ctx.send(embed=embed1)
        await ctx.send(embed=embed2)
    
    @command(hidden=True)
    async def tada(self, ctx: Context) -> None:
        await ctx.send(":tada:")

    @command(hidden=True)
    async def lenny(self, ctx: Context) -> None:
        await ctx.send("( ͡° ͜ʖ ͡°)")
    
    @command(hidden=True)
    @is_owner()
    async def quickfix(self, ctx: Context) -> None:
        async for mess in self.bot.get_channel(728489165565591562).history(limit=3):
            if mess.id == 841860207117074462:
                message = mess
                break
            
        n, u, p, id = self.data[0]
        embed = self.create_embed(n, u, p)
        await message.edit(embed=embed)


def setup(bot: Bot) -> None:
    bot.add_cog(KUSNews(bot))