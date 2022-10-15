from Video import Video
import time
import subprocess

class Downloader:

    def __init__(self, download_history):
        self.download_history = download_history
    
    def download_videos(self, videos, file_prefix, output_dir, ffmpeg_params=None, codec="libx265"):
        output_videos = []
        for video_in in videos:
            video_out = Video(
                original_name = f"{video_in.original_name}",
                location = f"{output_dir}/{file_prefix}{video_in.formatted_name}",
                formatted_name = f"{file_prefix}{video_in.formatted_name}"
            )
            print(f"Downloading {video_in.original_name}")
            download_time = self.download(video_in, video_out, ffmpeg_params, codec)
            print(f"Downloaded {video_out.formatted_name} in {download_time:.2f} seconds")
            output_videos += [video_out]
        return output_videos

    def download(self, video_in, video_out, ffmpeg_params=None, codec="libx265"):
        with open(self.download_history, "r") as f:
            if video_in.formatted_name in f.read():
                print(f"Skipping {video_in.formatted_name} because it's already downloaded")
                return
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

        with open(self.download_history, "a") as f:
            f.write(video_in.formatted_name + "\n")

        return time.time() - start_download_time