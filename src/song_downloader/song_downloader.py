import re
import sys
import warnings
from pathlib import Path

import ffmpeg
import spotipy
from pytubefix import YouTube
from spotipy import SpotifyPKCE
from spotipy.cache_handler import CacheFileHandler
from youtube_search import YoutubeSearch

CLIENT_ID = "dbabf45ecf1c4645853f4baafc3096b4"
REDIRECT_URL = "http://localhost:8080"


def convert_mp4_audio_to_m4a(filename: Path):
    new_name = filename.with_suffix(".m4a")
    ffmpeg.input(str(filename)).audio.output(filename=new_name, acodec="copy").run(
        overwrite_output=True
    )
    Path.unlink(filename)


def download_from_yt_url(url: str):
    audio_stream = YouTube(url).streams.get_audio_only()
    path_as_m4a = Path(audio_stream.default_filename).with_suffix(".m4a")
    if path_as_m4a.exists():
        print(f"File {path_as_m4a} already exists, skipping...")
        return None
    print(f"Downloading audio from {url}")
    filepath = audio_stream.download()
    print("Downloading finished")
    return filepath


def download_from_yt_by_name(search_term: str):
    print(f'Searching youtube for "{search_term}"')
    search_result = YoutubeSearch(search_term, max_results=1).to_dict()[0]
    video_url = f"https://www.youtube.com/watch?v={search_result['id']}"
    print(f"Found: {search_result['title']}, url: {video_url}")
    filepath = download_from_yt_url(video_url)
    if filepath is None:
        return
    convert_mp4_audio_to_m4a(Path(filepath))


def extract_playlist_id_from_url(playlist_url: str):
    if match := re.match(r"https://open.spotify.com/playlist/(.*)\?", playlist_url):
        return match.groups()[0]
    else:
        raise ValueError("Expected format: https://open.spotify.com/playlist/...")


def download_from_spotify(playlist_url: str):
    playlist_id = extract_playlist_id_from_url(playlist_url)
    cache_path = Path.home() / ".cache" / "song_downloader"
    cache_path.mkdir(parents=True, exist_ok=True)
    cache_handler = CacheFileHandler(cache_path / "spotify_token.cache")
    spotipy_pkce = SpotifyPKCE(
        client_id=CLIENT_ID,
        redirect_uri=REDIRECT_URL,
        scope="playlist-read-private," "playlist-read-collaborative",
        cache_handler=cache_handler,
    )
    access_token = spotipy_pkce.get_access_token()
    sp = spotipy.Spotify(auth=access_token)
    playlist = sp.playlist(playlist_id)
    playlist_name = playlist["name"]
    print(f'Downloading songs from playlist "{playlist_name}"')
    for track in playlist["tracks"]["items"]:
        track_name = track["track"]["name"]
        main_track_artist = track["track"]["artists"][0]["name"]
        download_from_yt_by_name(f"{main_track_artist} - {track_name}")


def main():
    if len(sys.argv) != 2:
        print(
            "[error] required 1 positional argument: search term, youtube video link or spotify playlist link"
        )
        exit(1)
    user_input = sys.argv[1]
    if "youtube.com" in user_input:
        # assume it's a link - let's worry about validation later
        download_from_yt_url(user_input)
    elif "spotify.com" in user_input:
        warnings.warn(
            f"For Spotify, only downloading full playlists is supported. Assuming {user_input} is a valid "
            f"playlist link - if not, something may break."
        )
        download_from_spotify(user_input)
    else:
        download_from_yt_by_name(user_input)


if __name__ == "__main__":
    main()
