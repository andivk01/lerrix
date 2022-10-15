class FFmpegUtils:
    def time_in_seconds(time):
        time = time.split(":")
        return int(time[0]) * 3600 + int(time[1]) * 60 + float(time[2])