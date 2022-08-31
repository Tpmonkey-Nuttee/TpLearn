"""
KUS Announcement Monitor system.
Monitoring: http://www.kus.ku.ac.th/news.php
Made by Tpmonkey
"""

from discord import Embed, Colour
from discord.ext.tasks import loop
from discord.ext.commands import cooldown as cd
from discord.ext.commands import (
    Cog, Context, command, is_owner, has_permissions, BucketType
)

import config
from bot import Bot

import logging
import asyncio
import traceback
from hashlib import sha1
from typing import Optional
from datetime import datetime
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

MAIN_URL = config.main_url
NEWS_URL = config.news_url

COOLDOWN = config.kus_news_cooldown

def hash(text: str) -> str:
    return sha1(bytes(text, "utf-8")).hexdigest()

class NewsManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.news = list(bot.database.loads("NEWS-IDS", []))
    
    def save(self) -> None:
        self.bot.database.dumps("NEWS-IDS", self.news)
    
    def extend(self, title: str) -> None:
        hash_title = hash(title)

        if hash_title not in self.news:
            self.news.append(hash_title)
        
        if len(self.news) > 20:
            del self.news[0]
        
        self.save()
        
    def compare(self, new_news: list) -> list:
        """Compare new and old news to find a new news.

        Args:
            new_news (list): news
            [(title, url, image, id), (...), ...]

        Returns:
            list: results
        """
        log.debug(f"Comparing {len(new_news)} news.")
        results = []
        
        for new in new_news:
            if hash(new[0]) not in self.news:
                log.debug(f"Found: {new[0]}")
                results.append(new)
                self.extend(new[0])
        
        return results

class KUSNews(Cog):
    """KUS monitor system, Use command below to set it up!"""
    def __init__(self, bot: Bot):
        self.bot = bot
        self.data = None
        self.channels = None
        self.cookies = None
        
        self.enable = True
        self.sendEmbed = True
        
        self.manager = NewsManager(bot)
        self.looping.start()
    
    def cog_unload(self):
        self.looping.cancel()
    
    @Cog.listener()
    async def on_resumed(self) -> None:
        """
        Check if loop running correctly.
        """
        if not self.looping.is_running():
            self.looping.restart()
            await self.bot.log(__name__, "KUS monitor is not running, Restarted", True)
            await self.bot.log(__name__, traceback.format_exc())
    
    async def save(self) -> None:
        await self.bot.database.dump("KUS-COOKIES", self.cookies)
        await self.bot.database.dump("NEWS-CHANNELS", self.channels)
        log.debug('saved news channels')
    
    async def load_data(self) -> None:
        self.cookies = await self.bot.database.load("KUS-COOKIES", None)
        self.channels = await self.bot.database.load("NEWS-CHANNELS", {})
        log.debug('loaded data')

    async def __fetch__(self) -> str:
        r = await self.bot.trust_session.get(NEWS_URL, cookies=self.cookies)
        return await r.text()
    
    async def __get__data(self) -> Optional[list]:
        respone_text = await self.__fetch__()

        soup = BeautifulSoup(respone_text, "html.parser")
        home = soup.find(attrs={"class":"home-news"})

        if home is None and self.enable:
            self.enable = False
            await self.bot.log(__name__, 'Unable to fetch kus data, disabled system until cookie is set.', mention=True)
            return None

        if home is not None and not self.enable:
            self.enable = True
            await self.bot.log(__name__, 'successfully fecthed kus data, enabled system.')

        if home is None and not self.enable:
            return None

        news = home.find_all("div", attrs={"class":"headline left"})
        pics = home.find_all("div", attrs={"class":"img-container left"})

        return [
            ( 
                new.get_text(), # Header
                new.find('a').get("href"), # url
                MAIN_URL + pic.find("img").get("src"), # Thumbnail url
                new.find('a').get("href") # News IDs
            ) for new, pic in zip(news, pics)
        ]
    
    @loop(hours=COOLDOWN)
    async def looping(self) -> None:
        if self.channels is None: 
            await self.load_data()
        
        self.data = await self.__get__data()

        # Sometimes, website prevend bot to acces.
        if not self.enable:
            log.debug('trying to update news but is not enable, passing...')
            return

        news = self.manager.compare(self.data)
        
        if news:            
            if len(news) > 6:
                await self.bot.log(__name__, f"Canceling: Too many news, Something may went wrong ({len(new_ids)} news).", True)
                self.sendEmbed = False
            
            # Format from [(title, url, image, id), ...] to [(title, url, image)]
            # But convert the image from gif to image.
            formatted_news = []
            for new in news:                
                # Convert to image, bc gif in embed is broken for some reason....
                image_url = await self.bot.get_image_from_gif(new[2])

                formatted_news.append(
                    [new[0], new[1], image_url]
                )
                
                # Prevent rate-limit.
                await asyncio.sleep(2)

            embeds = [self.create_embed(n, u, p) for n, u, p in formatted_news]

            await self.bot.log(__name__, f"New data detected\n**Found:** {formatted_news}")

            log_msg = ""
            
            # Do not send an embed(s) if it's the first fetch.
            if len(embeds) != 0 and self.sendEmbed:
                for _ in self.channels:
                    channel = self.bot.get_channel(_)
                    if channel is None: 
                        continue
                    
                    log_msg += f"[->] {channel.name}: {_}\n"
                    
                    # Send news
                    for embed in embeds[::-1]:
                        try: 
                            await channel.send(embed=embed)
                            await asyncio.sleep(1)
                        except Exception:
                            log_msg += f"[x] {channel}: {traceback.format_exc(limit = -1)}\n"
                            break        


                log_msg += f"total {len(self.channels)} channels"
                await self.bot.log(__name__, log_msg)
            
        self.bot.last_check['kus-news'] = datetime.utcnow()
    
    def create_embed(self, name, url, pic) -> Embed:
        if url.startswith("news_detail"): 
            url = MAIN_URL + url
        
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
    
    @command(name="set-news", aliases = ("add-news", ))
    @has_permissions(manage_guild=True)
    @cd(1, 15)
    async def set_news(self, ctx: Context) -> None:
        """Add News-Channel, Run this on it"""
        channel_id = ctx.channel.id

        if channel_id in self.channels:
            return await ctx.send(":x: **This channel is already added.**")            
        
        self.channels.append(channel_id)
        await ctx.send("**Successfully Added Channel.**\nMonitoring: <http://www.kus.ku.ac.th/news.php>")
        await self.save()
        await self.bot.log(__name__, f"New news Channel has been added, {ctx.channel}//{channel_id}")
    
    @command(name="remove-news", aliases=("delete-news", ))
    @has_permissions(manage_guild=True)
    @cd(1, 15)
    async def remove_news(self, ctx: Context) -> None:
        """Remove News-Channel, Run this on it."""
        channel_id = ctx.channel.id

        if channel_id not in self.channels:
            return await ctx.send(":x: **This channel is already removed.**")            
        
        self.channels.remove(channel_id)
        await ctx.send("**Successfully Removed Channel.**")
        await self.save()
        await self.bot.log(__name__, f"New news Channel has been removed, {ctx.channel}//{channel_id}")
    
    @command(name="news")
    @cd(3, 10, BucketType.guild)
    async def news_embed(self, ctx: Context, amount: int = 3) -> None:
        """Show 3 Newest Announcements."""
        if not self.enable:
            embed = Embed(
                title = "คำสั่งนี้ ได้ถูกปิดการใช้งานชั่วคราว",
                description = f"เนื่องจากทางโรงเรียน มีการจำกัดการเข้าใช้งานของบอทไว้ \nจึงไม่สามารถดึงข้อมูลดังกล่าวได้\n\nหากต้องการอ่านประชาสัมพันธ์ สามารถคลิกได้[ที่นี่]({NEWS_URL})",
                timestamp = ctx.message.created_at,
                colour = Colour.from_rgb(170, 3, 250)
            )
            return await ctx.send(embed=embed)        
            
        if self.data is None:
            return await ctx.send("กำลังโหลดข้อมูล - กรุณารอสักครู่...")            

        amount = max(min(10, amount), 1)
        embeds = [self.create_embed(n, u, p) for n, u, p, _ in self.data]
        for new in range(amount):
            await ctx.send(embed=embeds[new])
    
    @command(name="setcookie")
    @is_owner()
    async def setcookie(self, ctx: Context, cookie: str) -> None:
        """Set PHPSESSID cookie.
        """
        self.cookies = {
            "PHPSESSID": cookie
        }
        await self.save()
        self.enable = True
        await ctx.send("Saved cookie, Trying to fetch data.")

        ret = await self.__get__data()
        if ret is not None:
            return await ctx.send("Fetch successful!")
        
        self.enable = False
        await ctx.send("Unable to fetch data, Disabled system.")      

    @command(name="reloadkus")
    @is_owner()
    async def reloadkus(self, ctx: Context) -> None:
        self.looping.restart()
        await ctx.send("Reloaded.")  
    
    @command(hidden=True)
    async def tada(self, ctx: Context) -> None:
        await ctx.send(":tada:")

    @command(hidden=True)
    async def lenny(self, ctx: Context) -> None:
        await ctx.send("( ͡° ͜ʖ ͡°)")


def setup(bot: Bot) -> None:
    bot.add_cog(KUSNews(bot))