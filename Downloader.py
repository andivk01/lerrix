from Video import Video
import time
import subprocess

class Downloader:

    def __init__(self, download_history):
        self.download_history = download_history
    
    def download_videos(self, videos, file_prefix, output_dir, ffmpeg_params=None, codec="libx265"):
        history_file = open(self.download_history, "a+")
        history = history_file.read().splitlines()
        output_videos = []
        for video_in in videos:
            video_out = Video(
                original_name = f"{file_prefix}{video_in.original_name}",
                location = f"{output_dir}/{file_prefix}{video_in.formatted_name}"
            )
            if video_in.original_name in history:
                print(f"Skipping {video_in.original_name} because it's already downloaded")
                continue
            print(f"Downloading {video_in.location}")
            download_time = self._download(video_in, video_out, ffmpeg_params, codec)
            print(f"Downloaded {video_out.location} in {download_time} seconds")
            output_videos += [video_out]
            history_file.write(video_in.original_name)
            history_file.write("\n")
            history_file.flush()
        history_file.close()
        return output_videos

    def _download(self, video_in, video_out, ffmpeg_params=None, codec="libx265"):
        start_download_time = time.time()
        command = [
            "ffmpeg",
            "-y", # overwrite output file if it exists
            "-v", "quiet",
            "-stats", 
            "-i", f"{video_in.location}",
            "-c:v", f"{codec}",
            "-crf", "34", # TODO make this a parameter?
            "-y"
        ]
        if ffmpeg_params is not None and ffmpeg_params != 0:
            command += ffmpeg_params
        command.append(video_out.location)
        subprocess.run(command)

        return time.time() - start_download_time