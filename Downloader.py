from Video import Video
import time
import subprocess
import os
import shutil

class Downloader:

    def __init__(self, download_history, tmp_directory="tmp"):
        self.download_history = download_history
        self.tmp_directory = tmp_directory
    
    def download_videos(self, videos, file_prefix, output_dir, ffmpeg_params=None, codec="libx265", overwrite=False):
        output_videos = []
        for video_in in videos:
            video_out = Video(
                original_name = f"{video_in.original_name}",
                location = f"{os.path.join(output_dir, f'{file_prefix}{video_in.formatted_name}')}",
                formatted_name = f"{file_prefix}{video_in.formatted_name}"
            )
            print(f"Downloading {video_in.original_name}")
            download_time = self.download(video_in, video_out, ffmpeg_params, codec, overwrite)
            print(f"Downloaded {video_out.formatted_name} in {download_time:.2f} seconds")
            output_videos += [video_out]
        return output_videos

    def download(self, video_in, video_out, ffmpeg_params=None, codec="libx265", overwrite=False):
        with open(self.download_history, "r") as f:
            if video_in.formatted_name in f.read():
                print(f"Skipping {video_in.formatted_name} because it's already downloaded")
                return
        start_download_time = time.time()
        tmpdir = os.path.join(self.tmp_directory, "tmp" + str(int(time.time())))
        tmpfileout = os.path.join(tmpdir, video_out.formatted_name)
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        os.mkdir(tmpdir)
        command = ["ffmpeg"]
        command += ["-y"] if overwrite else ["-n"]
        command += [
            "-v", "quiet",
            "-stats", 
            "-i", f"{video_in.location}",
            "-c:v", f"{codec}",
            "-crf", "34", # TODO make this a parameter?
        ]
        if ffmpeg_params is not None and ffmpeg_params != 0:
            command += ffmpeg_params
        command.append(tmpfileout)
        subprocess.run(command)

        if os.path.exists(tmpfileout):
            shutil.move(tmpfileout, video_out.location) # TODO FILE NOT FOUND
        else: 
            print(f"ERROR: File downloaded not found {tmpfileout}") # TODO HANDLE ERROR
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        with open(self.download_history, "a") as f:
            f.write(video_in.formatted_name + "\n")

        return time.time() - start_download_time