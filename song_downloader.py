import sys
import warnings
import re

import spotipy
from pytubefix import YouTube
from youtube_search import YoutubeSearch
from spotipy import SpotifyPKCE

CLIENT_ID = "dbabf45ecf1c4645853f4baafc3096b4"
REDIRECT_URL = "http://localhost:8080"


def download_from_yt_url(url: str):
    print(f"Downloading audio from {url}")
    yt = YouTube(url)
    yt.streams.get_audio_only().download()
    print("Downloading finished")


def download_from_yt_by_name(search_term: str):
    print(f"Searching youtube for \"{search_term}\"")
    search_result = YoutubeSearch(search_term, max_results=1).to_dict()[0]
    video_url = f"https://www.youtube.com/watch?v={search_result['id']}"
    print(f"Found: {search_result['title']}, url: {video_url}")
    download_from_yt_url(video_url)


def extract_playlist_id_from_url(playlist_url: str):
    if match := re.match(r"https://open.spotify.com/playlist/(.*)\?", playlist_url):
        return match.groups()[0]
    else:
        raise ValueError("Expected format: https://open.spotify.com/playlist/...")


def download_from_spotify(playlist_url: str):
    playlist_id = extract_playlist_id_from_url(playlist_url)
    spotipy_pkce = SpotifyPKCE(client_id=CLIENT_ID, redirect_uri=REDIRECT_URL, scope="playlist-read-private,"
                                                                                     "playlist-read-collaborative")
    access_token = spotipy_pkce.get_access_token()
    sp = spotipy.Spotify(auth=access_token)
    playlist = sp.playlist(playlist_id)
    playlist_name = playlist["name"]
    print(f"Downloading songs from playlist \"{playlist_name}\"")
    for track in playlist["tracks"]["items"]:
        track_name = track["track"]["name"]
        main_track_artist = track["track"]["artists"][0]["name"]
        download_from_yt_by_name(f"{main_track_artist} - {track_name}")


def main():
    user_input = sys.argv[1]
    if "youtube.com" in user_input:
        # assume it's a link - let's worry about validation later
        download_from_yt_url(user_input)
    elif "spotify.com" in user_input:
        warnings.warn(f"For Spotify, only downloading full playlists is supported. Assuming {user_input} is a valid "
                      f"playlist link - if not, something may break.")
        download_from_spotify(user_input)
    else:
        download_from_yt_by_name(user_input)


if __name__ == '__main__':
    main()
