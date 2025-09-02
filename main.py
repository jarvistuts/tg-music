import asyncio
import sys
import shlex

RTMPS_URL = "rtmps://dc5-1.rtmp.t.me/s/2683771050:sjv1b-tEC_-_M6JOf8kvaw"


async def bash(cmd: str) -> tuple[str, str]:
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return out.decode().strip(), err.decode().strip()


async def ytdl(link: str) -> tuple[int, list[str]]:
    cmd = (
        "yt-dlp --cookies cookies.txt "
        '-f "bv*[vcodec^=avc1]+ba[acodec=aac]/b[ext=mp4]" '
        "--get-url " + shlex.quote(link)
    )
    out, err = await bash(cmd)
    if out:
        return 1, out.splitlines()
    return 0, [err]


async def stream_video(link: str, rtmps_url: str) -> None:
    while True:                               # <── restart loop
        ok, result = await ytdl(link)
        if not ok:
            print(f"[yt-dlp] {result[0]}", file=sys.stderr)
            await asyncio.sleep(5)            # brief pause before retry
            continue

        video_url, *audio_url = result
        audio_url = audio_url[0] if audio_url else video_url

        ffmpeg_cmd = (
            f"ffmpeg -hide_banner -loglevel info -re "
            f'-i "{video_url}" -i "{audio_url}" '
            f"-c copy -f flv {shlex.quote(rtmps_url)}"
        )

        print("[ffmpeg] Starting copy-stream →", rtmps_url)
        proc = await asyncio.create_subprocess_shell(
            ffmpeg_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            async for line in proc.stderr:
                print(line.decode().rstrip())
        except asyncio.CancelledError:
            proc.kill()
            await proc.wait()
            raise
        finally:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()

        print("[loop] FFmpeg exited, fetching fresh URLs…")


if __name__ == "__main__":
    url = "https://youtu.be/vB0V3iCSzQw?si=ZocGWzFbVsN6zwmo"
    try:
        asyncio.run(stream_video(url, RTMPS_URL))
    except KeyboardInterrupt:
        pass


