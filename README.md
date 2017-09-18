# Sinusbot - File Importer
A CLI Tool to Import audio files via the HTTP API. Written in Python.

# Usage:

```
usage: ./sinusbot_uploader.py [ -h hostname ] [ -p port] [ -U user ] [ -P password ] [ -b remote_dir_uuid ] [ -r ] [ -s ] LOCAL_DIRECTORY

  args:
    LOCAL_DIRECTORY    directory to upload

  options:
    -h, --host         API hostname (default: 127.0.0.1)
    -p, --port         API port (default: 8087)
    -U, --user         auth username (default: sinus)
    -P, --password     auth password (default: sinus)
    -r, --recursive    process directory recursively
    -s, --ssl          enable SSL (disabled by default)
    -b, --base         specify remote base directory uuid (default: empty for the root
```
