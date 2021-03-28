from discord.ext.commands import Cog, Context, command
from discord.ext.tasks import loop
from discord import Embed, Colour

from bot import Bot

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from datetime import datetime

MAIN_URL = "http://www.kus.ku.ac.th/"
NEWS_URL = "http://www.kus.ku.ac.th/news.php"

class KUSNews(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.data = None
        self.ids = None
        self.channels = None
        self.looping.start()
    
    def cog_unload(self):
        self.looping.cancel()
    
    async def save(self) -> None:
        await self.bot.database.dump("NEWS-CHANNELS", self.channels)
    
    async def load_data(self) -> None:
        self.channels = await self.bot.database.load("NEWS-CHANNELS")
        self.ids = await self.bot.database.load("NEWS-IDS")

    async def __fetch__(self):
        async with ClientSession() as sess:
            async with sess.get(NEWS_URL) as r:
                respone_text = await r.text()
                await sess.close()

        # await self.bot.log(__name__, "Fetching data")

        return respone_text
    
    async def __get__data(self):
        respone_text = await self.__fetch__()

        soup = BeautifulSoup(respone_text, "html.parser")
        home = soup.find(attrs={"class":"home-news"})

        news = home.find_all("div", attrs={"class":"headline left"})
        pics = home.find_all("div", attrs={"class":"img-container left"})

        # await self.bot.log(__name__, "Formatted data")

        return [
            ( 
                new.get_text(), 
                MAIN_URL+new.find('a').get("href"), 
                MAIN_URL + pic.find("img").get("src"),
                new.find('a').get("href")
            ) for new, pic in zip(news, pics)
        ]
    
    @loop(hours=1)
    async def looping(self) -> None:
        if self.channels is None or self.ids is None:
            await self.load_data()
        
        self.data = await self.__get__data()

        news = {id: (n, u, p) for n, u, p, id in self.data}
        new_ids = [i for n, u, p, i in self.data]

        # print(self.ids)
        # print(new_ids)

        if new_ids != self.ids:
            # Place Holder
            _p = new_ids

            await self.bot.log(__name__, "New data detected")

            for _ in self.ids:
                if _ in _p:
                    _p.remove(_)
            
            datas = [news[key] for key in _p]
            
            embeds = [self.create_embed(n, u, p) for n, u, p in datas]

            for _ in self.channels:
                channel = self.bot.get_channel(_)
                if channel is not None:
                    await self.bot.log(__name__, f"Sending news to {channel}//{_}")

                    # Send news
                    for embed in embeds[::-1]:
                        await channel.send(embed=embed)
                else:
                    await self.bot.log(__name__, f"Unable to send news with channel ID: {_}", True)
                
            await self.bot.log(__name__, "Sended news to all channels, saving data...")
            ids = [id for n, u, p, id in self.data]
            await self.bot.database.dump("NEWS-IDS", ids)
            self.ids = ids
            await self.bot.log(__name__, "Confirmed, Saved all data.")
    
    def create_embed(self, name, url, pic) -> Embed:
        embed = Embed(
            colour = Colour.from_rgb(170, 3, 250),
            description = name.replace("...อ่านต่อ", f"[...อ่านต่อ]({url})"),
            timestamp = datetime.utcnow()
        )
        # embed.set_author(name=name, url=url)
        embed.set_thumbnail(url=pic)
        embed.set_footer(text = "โรงเรียนสาธิตแห่งมหาวิทยาลัยเกษตรศาสตร์", icon_url= MAIN_URL + "images_kus/kus_logo.png")

        return embed
    
    def create_embed__(self, name, url, pic) -> Embed:
        embed = Embed(
            colour = Colour.from_rgb(170, 3, 250),
            description = name.replace("...อ่านต่อ", f"[...อ่านต่อ]({url})"),
            timestamp = datetime.utcnow()
        )
        embed.set_author(name = "โรงเรียนสาธิตแห่งมหาวิทยาลัยเกษตรศาสตร์", url = "http://www.kus.ku.ac.th/", icon_url= MAIN_URL + "images_kus/kus_logo.png")
        embed.set_thumbnail(url=pic)
        embed.set_footer(text="ข่าวประชาสัมพันธ์")

        return embed
    
    @command(name="set-news")
    async def set_news(self, ctx: Context) -> None:
        channel_id = ctx.channel.id

        if channel_id in self.channels:
            await ctx.send("Already added")
            return
        
        self.channels.append(channel_id)
        await ctx.send("Added Channel")
        await self.save()
        await self.bot.log(__name__, f"New news Channel has been added, {ctx.channel}//{channel_id}")
    
    @command(name="remove-news")
    async def remove_news(self, ctx: Context) -> None:
        channel_id = ctx.channel.id

        if channel_id not in self.channels:
            await ctx.send("Already removed")
            return
        
        self.channels.remove(channel_id)
        await ctx.send("Removed Channel")
        await self.save()
        await self.bot.log(__name__, f"New news Channel has been removed, {ctx.channel}//{channel_id}")
    
    @command(name="news")
    async def news_embed(self, ctx: Context) -> None:
        embeds = [self.create_embed(n, u, p) for n, u, p, id in self.data]
        for embed in embeds:
            await ctx.send(embed=embed)
    
    @command(name="embeds")
    async def embeds_(self, ctx: Context) -> None:

        n, u, p, id = self.data[0]
        embed1 = self.create_embed(n, u, p)
        embed2 = self.create_embed__(n, u, p)

        await ctx.send(embed=embed1)
        await ctx.send(embed=embed2)
    
    @command(name="id")
    async def get_id(self, ctx: Context) -> None:

       
        ids = [id for n, u, p, id in self.data]
        await ctx.send(ids)


def setup(bot: Bot) -> None:
    bot.add_cog(KUSNews(bot))