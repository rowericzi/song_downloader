import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import ffmpeg
import requests
from mutagen.mp4 import MP4, MP4Cover
from pytubefix import Playlist, Stream, YouTube
from pytubefix.exceptions import VideoUnavailable
from requests.exceptions import HTTPError
from spotipy import Spotify, SpotifyPKCE
from spotipy.cache_handler import CacheFileHandler
from youtube_search import YoutubeSearch

CLIENT_ID = "dbabf45ecf1c4645853f4baafc3096b4"
REDIRECT_URL = "http://localhost:8080"


@dataclass
class SongDescription:
    """A class for storing information about a song"""

    title: str = None
    artist: str = None
    album: str = None
    cover_art_url: str = None
    youtube_url: str = None

    def search(self) -> str:
        return f"{self.artist} - {self.title}"


def try_add_metadata(filename: str, song: SongDescription) -> None:
    audio_file = MP4(filename)

    if song.cover_art_url is None:
        url_data = urlparse(song.youtube_url)
        query = parse_qs(url_data.query)
        video_id = query["v"][0]
        song.cover_art_url = f"https://img.youtube.com/vi/{video_id}/0.jpg"

    try:
        response = requests.get(song.cover_art_url)
        cover_data = response.content
        audio_file.tags["covr"] = [
            MP4Cover(cover_data, imageformat=MP4Cover.FORMAT_JPEG)
        ]
    except HTTPError as err:
        print(
            f"[warning] failed to download album cover for {song.search()}: {str(err)}"
        )

    if song.title is not None:
        audio_file.tags["\xa9nam"] = song.title
    if song.artist is not None:
        audio_file.tags["\xa9ART"] = song.artist
    if song.album is not None:
        audio_file.tags["\xa9alb"] = song.album

    audio_file.save()


def convert_mp4_audio_to_m4a(filename: Path) -> Path:
    new_name = filename.with_suffix(".m4a")
    # TODO: remove loglevel="quiet" when debugging
    ffmpeg.input(str(filename)).audio.output(
        filename=new_name, acodec="copy", loglevel="quiet"
    ).run(overwrite_output=True)
    Path.unlink(filename)
    return new_name


def get_audio_stream(
    song: SongDescription, max_retries: int = 5, retry_timeout: int = 5
) -> Stream:
    num_attempts = 0
    while True:
        try:
            audio_stream = YouTube(
                song.youtube_url, client="ANDROID_MUSIC"
            ).streams.get_audio_only()
            return audio_stream
        except VideoUnavailable:
            num_attempts += 1
            if num_attempts >= max_retries:
                raise
            print(
                f"[warning] an issue with downloading {song.artist} - {song.title}, retrying in {retry_timeout} seconds..."
            )
            time.sleep(retry_timeout)


def download_from_yt_url(song: SongDescription) -> None:
    audio_stream = get_audio_stream(song)
    path_as_m4a = Path(audio_stream.default_filename).with_suffix(".m4a")
    if path_as_m4a.exists():
        print(f'[info] file "{path_as_m4a}" already exists, skipping download...')
        try_add_metadata(str(path_as_m4a), song)
        return
    print(f'[info] downloading "{path_as_m4a}" from {song.youtube_url}')
    filepath = audio_stream.download()
    print("[info] downloading finished")
    new_name = convert_mp4_audio_to_m4a(Path(filepath))
    try_add_metadata(str(new_name), song)


def get_youtube_url_from_name(search_term: str) -> str:
    search_result = YoutubeSearch(search_term, max_results=1).to_dict()[0]
    video_url = f"https://www.youtube.com/watch?v={search_result['id']}"
    return video_url


def get_urls_from_youtube_playlist(playlist_url: str) -> list[str]:
    playlist = Playlist(playlist_url)
    return [url for url in playlist.video_urls]


def get_spotify_playlist_id_from_url(playlist_url: str) -> str:
    if match := re.match(r"https://open.spotify.com/playlist/(.*)\?", playlist_url):
        return match.groups()[0]
    else:
        raise ValueError(
            "invalid spotify link, expected format: https://open.spotify.com/playlist/..."
        )


def get_songs_from_spotify_playlist(playlist_url: str) -> list[SongDescription]:
    playlist_id = get_spotify_playlist_id_from_url(playlist_url)
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
    sp = Spotify(auth=access_token)
    playlist = sp.playlist(playlist_id)["tracks"]
    track_list_internal = []
    playlist_items = playlist["items"]
    while playlist["next"]:
        playlist = sp.next(playlist)
        playlist_items.extend(playlist["items"])
    for track in playlist_items:
        track_name = track["track"]["name"]
        main_track_artist = track["track"]["artists"][0]["name"]
        album_name = track["track"]["album"]["name"]
        cover_art_url = track["track"]["album"]["images"][0]["url"]
        track_list_entry: SongDescription = SongDescription(
            title=track_name,
            artist=main_track_artist,
            album=album_name,
            cover_art_url=cover_art_url,
        )
        track_list_internal.append(track_list_entry)
    return track_list_internal


def main():
    if len(sys.argv) != 2:
        print(
            """[error] a positional argument required. supported formats:
- a semicolon-separated list of search terms
- link to a youtube video
- link to a youtube playlist
- link to a spotify playlist"""
        )
        exit(1)
    user_input = sys.argv[1]
    songs_with_yt_urls: list[SongDescription] = []
    if "spotify.com" in user_input:
        songs_with_yt_urls = get_songs_from_spotify_playlist(user_input)
        print("[info] found the following youtube links for given song titles:")
        for song in songs_with_yt_urls:
            song.youtube_url = get_youtube_url_from_name(song.search())
            print(f"- {song.search()}: {song.youtube_url}")
    elif "youtube.com" in user_input:
        if "playlist" in user_input:
            songs_with_yt_urls = [
                SongDescription(youtube_url=url)
                for url in get_urls_from_youtube_playlist(user_input)
            ]
        else:
            songs_with_yt_urls = [SongDescription(youtube_url=user_input)]
    else:  # assume the input is a semicolon-separated list of videos to download
        names = user_input.split(";")
        songs_with_yt_urls = [
            SongDescription(youtube_url=url)
            for url in [get_youtube_url_from_name(name) for name in names]
        ]

    if len(songs_with_yt_urls) == 0:
        print(
            "[error] something went wrong, list of urls to download is empty. maybe the playlist is private?"
        )
        exit(1)

    for song in songs_with_yt_urls:
        try:
            download_from_yt_url(song)
        except VideoUnavailable:
            print(f"[error] couldn't download due to youtube error, skipping...")


if __name__ == "__main__":
    main()
