"""9:16 프레임 → 릴스 MP4 (느린 줌 + 크로스페이드).
Instagram 릴스 규격(2026-09 Meta 문서): MP4, H264, progressive, closed GOP, 4:2:0,
23-60fps, 가로 1920px 이하, 3초~15분, 300MB 이하, AAC 48kHz 이하 128kbps.
assets/music/ 에 mp3가 있으면 하나를 골라 깔고, 없으면 무음 트랙을 넣는다.
"""
import json, random, re, subprocess
from pathlib import Path

FPS = 30
XF = 0.4  # 크로스페이드 길이(초)


def seg_duration(slide):
    text = re.sub(r"<[^>]+>", "", (slide.get("h", "") + slide.get("p", "") + slide.get("pre", "")))
    d = 1.8 + len(text) * 0.03
    if slide["type"] == "cta":
        d = max(d, 3.0)
    return round(min(max(d, 2.2), 4.2), 2)


def build_reel(frames, slides, out_mp4, music_dir=None, seed=None):
    frames = [str(f) for f in frames]
    durs = [seg_duration(s) for s in slides]
    inputs, filters = [], []
    for i, (f, d, s) in enumerate(zip(frames, durs, slides)):
        inputs += ["-loop", "1", "-t", f"{d + XF:.2f}", "-i", f]
        n = int((d + XF) * FPS)
        zmax = 1.08 if s["type"] in ("photo", "cover", "full", "detail") else 1.03
        # 2배 업스케일 후 zoompan → 줌 떨림 방지
        filters.append(
            f"[{i}:v]scale=2160:3840,zoompan=z='min(1+({zmax}-1)*on/{n},{zmax})':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={n}:s=1080x1920:fps={FPS},"
            f"format=yuv420p,setsar=1[v{i}]")
    # xfade 체인
    last = "v0"; offset = 0.0
    for i in range(1, len(frames)):
        offset += durs[i - 1]
        filters.append(f"[{last}][v{i}]xfade=transition=fade:duration={XF}:offset={offset:.2f}[x{i}]")
        last = f"x{i}"
    total = sum(durs) + XF
    # 오디오
    music = []
    if music_dir and Path(music_dir).exists():
        music = sorted(Path(music_dir).glob("*.mp3"))
    ai = len(frames)
    if music:
        random.seed(seed)
        inputs += ["-stream_loop", "-1", "-i", str(random.choice(music))]
        filters.append(f"[{ai}:a]atrim=0:{total:.2f},afade=t=in:d=0.5,afade=t=out:st={total - 1.2:.2f}:d=1.2,"
                       f"volume=0.8,aresample=48000[a]")
    else:
        inputs += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
        filters.append(f"[{ai}:a]anull[a]")
    cmd = (["ffmpeg", "-y", "-loglevel", "error"] + inputs +
           ["-filter_complex", ";".join(filters), "-map", f"[{last}]", "-map", "[a]",
            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-g", str(FPS * 2), "-flags", "+cgop", "-b:v", "3500k", "-maxrate", "5M", "-bufsize", "8M",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000", "-ac", "2",
            "-t", f"{total:.2f}", "-movflags", "+faststart", str(out_mp4)])
    subprocess.run(cmd, check=True)
    return total
