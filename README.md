a tool for downloading songs from youtube


### installation

```commandline
git clone https://github.com/rowericzi/song_downloader
cd song_downloader
pip install .
```


### usage

```commandline
song_downloader "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```
will download the best quality audio stream from https://www.youtube.com/watch?v=dQw4w9WgXcQ as .m4a

```commandline
song_downloader "never gonna give you up"
```
 will search youtube for "never gonna give you up" and dowload the first
audio from the first result as .m4a

```commandline
song_downloader <link_to_spotify_playlist>
```
 will get the track list from given spotify playlist and look for the
songs on youtube, then download them
 
note: spotify sign-in is needed for the last option to work

in either case, files will be saved in the current working directory
