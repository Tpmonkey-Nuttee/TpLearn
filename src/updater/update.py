"""
Fetch & Download newer version from Github, 
Replace all files and Restart process.
"""

import os
import shutil
import zipfile
import requests

from logging import getLogger
from discord.ext.commands import Context

log = getLogger(__name__)

async def update(url: str, path: str, ctx: Context = None) -> None:
    await download(url, ctx)

    await move_files(path)

    shutil.rmtree("./updater/TpLearn-master")

    await ctx.send("All files are ready.")
    

async def download(url: str, ctx: Context = None) -> None:
    log.info(f"Downloading... {url}")

    await ctx.send("Downloading new version.")

    r = requests.get(url)
    
    with open("./updater/new.zip", "wb") as f:
        f.write(r.content)

    log.info("Unpacking zip file")

    await ctx.send("Unpacking zip file")

    with zipfile.ZipFile("./updater/new.zip","r") as zip_ref:
        zip_ref.extractall("./updater")
        
    log.info("Unpacked")

    os.remove("./updater/new.zip")

    log.info("Deleted zip file")
    

async def move_files(path: str) -> None:
    source_dir = "./updater/TpLearn-master/src"
    target_dir = path # "./test"

    file_names = os.listdir(source_dir)

    for file_name in file_names:
        source = os.path.join(source_dir, file_name)
        dst = os.path.join(target_dir, file_name)

        if os.path.isfile(source):
            log.info(f"Moving file:\n{source} -> {dst}")
            shutil.move(source, dst)
        elif os.path.isdir(source):
            log.info(f"Moving folder:\n{source} -> {dst}")
            shutil.copytree(source, dst, dirs_exist_ok=True)
        else:
            log.warning(f"Unknown file: {source}")
    
    try:
        shutil.rmtree(source_dir)
    except OSError:
        pass