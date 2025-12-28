from musicdl import musicdl

music_client = musicdl.MusicClient(music_sources=['YouTubeMusicClient','AppleMusicClient'])
music_client.startcmdui()