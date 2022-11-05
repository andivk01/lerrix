import subprocess

def duration(input):
    ffmpeg_cmd = ["ffprobe", "-i", input, "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"]
    ffmpeg_process = subprocess.Popen(
        ffmpeg_cmd,
        stdout = subprocess.PIPE,
        stderr = subprocess.STDOUT,
        universal_newlines = True
    )
    ffmpeg_out = ffmpeg_process.stdout
    ffmpeg_process.wait()

    if ffmpeg_process.returncode == 0:
        try:
            return float(ffmpeg_out.read())
        except:
            return None
    else:
        return None

def time_in_seconds(time):
    time = time.split(":")
    return int(time[0]) * 3600 + int(time[1]) * 60 + float(time[2])