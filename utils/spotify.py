from typing import List
from random import randint

# Spotify library.
import spotipy
from spotipy.client import SpotifyException
from spotipy.oauth2 import SpotifyClientCredentials

__all__ = ("getTracks", "getAlbum", "getRecommend", "SpotifyException")

import os

cid = os.getenv("CID")
secret = os.getenv("SECRET")

if cid is None or secret is None:
    raise ImportError(
        "Spotify Client ID and Client Secret is not setup.\n"
        "Please head to https://developer.spotify.com/dashboard/ to setup Spotify Service.\n"
        "Then, Set environment name CID (Client ID) and SECRET (Client Secret)"
    )

# Creating and authenticating our Spotify app.
client_credentials_manager = SpotifyClientCredentials(cid, secret)
spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

def getTracks(playlistURL: str) -> List[str]:   
    # Getting a playlist.
    results = spotify.user_playlist_tracks(user="", playlist_id=playlistURL, offset=0)
    trackList = []
    offset = 0

    # Loop untils all the tacks are extracted from playlist.
    # The reason behind is, Spotify API has limit at 100 tracks at a time, 
    # So to work around, We use offset insated
    while len(results["items"]) != 0:
        for i in results["items"]:
            trackList.append(f'{i["track"]["name"]} {i["track"]["artists"][0]["name"]}')
        offset += 100
        # Get it again, with an offset
        results = spotify.user_playlist_tracks(user="",playlist_id=playlistURL, offset=offset)
    return trackList

def getAlbum(albumURL: str) -> List[str]:
    # Getting a album.
    results = spotify.album_tracks(albumURL, offset=0)
    trackList = []
    offset = 0

    # For each track in the album.
    while len(results["items"]) != 0:
        for i in results["items"]:
            trackList.append(f'{i["name"]} {i["artists"][0]["name"]}')
        offset += 50
        results = spotify.album_tracks(albumURL, offset=offset)
    return trackList

def getRecommend(names: List[str], amount: int = 50) -> List[str]:    
    # Find uri
    uris = []
    for name in names:
        if "open.spotify.com/track/" in name:
            uris.append(name)
            continue
        r = spotify.search(q=name, limit=1)

        if len(r['tracks']['items']) == 0: continue # Not found    
        uris.append(r['tracks']['items'][0]['uri'])
    
    if len(uris) == 0:
        raise NameError

    # find recommendations
    r = spotify.recommendations(seed_tracks=uris, limit=randint(amount, 100)) 
    return [f'{i["name"]} {i["artists"][0]["name"]}' for i in r['tracks']]