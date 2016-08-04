# Streamer of audio (or any kind of data really)

```bash
# Start redis:
redis-server

# Start server:
./server.py

# Start sharer client:
./client.py 127.0.0.1 5005 share song.wav # -> Room id: 12345

# Start listener client:
./client.py 127.0.0.1 5005 listener 12345
```

# TODO
  - mp3
  - golang
  - [edge case] close connections when song ends