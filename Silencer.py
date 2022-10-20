from FFmpegUtils import FFmpegUtils
from Video import Video
import time
import subprocess
import re
import os
import shutil

class Silencer:
    def __init__(self, silence_history, db_min=35, min_silence_length=0.5, tmp_directory="tmp"):
        self.silence_history = silence_history
        self.db_min = db_min
        self.min_silence_length = min_silence_length
        self.tmp_directory = tmp_directory
    
    def unsilence_videos(self, videos, output_dir, codec="libx265"):
        for video_in in videos:
            video_out = Video(
                original_name = video_in.original_name,
                location = os.path.join(output_dir, video_in.formatted_name),
                formatted_name=video_in.formatted_name
            )
            self.unsilence(video_in, video_out, codec)

    def unsilence(self, video_in, video_out, codec="libx265"):
        with open(self.silence_history, "r") as f:
            if video_in.formatted_name in f.read():
                print(f"Video {video_in.formatted_name} is already unsilenced, skipping...")
                return
        intervals = self.detect_silence(video_in)
        tmpdir = os.path.join(self.tmp_directory, "tmp" + str(int(time.time())))
        if os.path.exists(tmpdir):
            shutil.rmtree(tmpdir)
        os.mkdir(tmpdir)
        videoparts_file = open(os.path.join(os.path.abspath(tmpdir), "videoparts"), "w")
        start_unsilence_time = time.time()
        for idx_interval, interval in enumerate(intervals):
            print(f" "*110, end="\r") # cleaning line
            print(f"Extracting video part {idx_interval+1}/{len(intervals)}, interval length: {(interval[1]-interval[0]):.2f}s, interval_range: {interval[0]:.2f}s -> {interval[1]:.2f}s", end="\r")
            file_part_output = os.path.join(os.path.abspath(tmpdir), f"{idx_interval}.{video_in.extension}")
            command = [
                "ffmpeg",
                "-loglevel", "quiet",
                "-ss", f"{interval[0]}",
                "-to", f"{interval[1]}",
                "-i", f"{video_in.location}",
                "-vsync", "1",
                "-async", "1",
                "-safe", "0",
                "-ignore_unknown", "-y",
                file_part_output
            ]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
            videoparts_file.write(f"file '{file_part_output}'\n")
        videoparts_file.close()
        print(f"\nAll video parts extracted in {time.time()-start_unsilence_time:.2f}s, reassemling video...")
        start_time = time.time()
        command = [
            "ffmpeg",
            "-y", # overwrite output file if it exists
            "-v", "quiet",
            "-stats", 
            "-f", "concat",
            "-safe", "0", "-i",
            os.path.join(os.path.abspath(tmpdir), "videoparts"),  
            "-c:v", codec,
            video_out.location
        ]
        subprocess.run(command)
        with open(self.silence_history, "a") as f:
            f.write(video_in.formatted_name + "\n")
        print(f"Video reassembled in {(time.time() - start_time):.2f}s")
        shutil.rmtree(tmpdir) 

    def detect_silence(self, video):
        print(f"Detecting silence in {video.location}...")
        start_detect_time = time.time()
        cmd = [
            'ffmpeg',
            '-y', 
            "-v", "quiet",
            "-stats", 
            '-i', video.location,
            '-af',
            f'silencedetect=noise=-{self.db_min}dB:d={self.min_silence_length}',
            "-f", "null", "-"
            ]
        console_output = subprocess.Popen(
            cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            universal_newlines = True
        ).stdout

        silence_times = []
        video_length = 1 # duration of audio file
        prev_percentage = 0 # progress percentage
        for line in console_output:
            if "[silencedetect" in line:
                capture = re.search("\\[silencedetect @ [0-9xa-f]+] silence_([a-z]+): (-?[0-9]+.?[0-9]*[e-]*[0-9]*)", line)
                if capture is None:
                    continue
                silence_times.append(float(capture[2]))
                if capture[1] == "start":
                    percentage = int(silence_times[-1] / video_length * 100)
                    if prev_percentage != percentage:
                        prev_percentage = percentage
                        print(f" "*110, end="\r") # cleaning line
                        print(f"Processed {percentage}% of audio file, audio length: {(video_length/60):.2f}mins", end="\r")
            elif "Duration" in line:
                capture = re.search("Duration: ([0-9:]+.?[0-9]*)", line)
                if capture is None:
                    continue
                video_length = FFmpegUtils.time_in_seconds(capture[1])
        
        print(f"\nSearch for silence finished in {int(time.time() - start_detect_time)}s")
        return Silencer._complementary_intervals(silence_times, video_length)

    def _complementary_intervals(times, audio_duration):
        times = [0] + times + [audio_duration]
        intervals = []
        nosilence_time = 0
        for i in range(0, len(times)-1, 2):
            if times[i+1] - times[i] < 0.1: # if interval length is less than 0.1s=100ms
                continue
            if times[i] == times[i+1]:
                continue
            nosilence_time += times[i+1] - times[i]
            if i > 0:
                if times[i-1] < times[i] - 0.02: # add 20ms on left of the interval
                    times[i] = times[i] - 0.02
            if i < len(times)-2:
                if times[i+2] > times[i+1] + 0.02:
                    times[i+1] = times[i+1] + 0.02
            intervals.append((times[i], times[i+1]))
        print(f"With silence: {int(audio_duration/60)}mins, without silence: {int(nosilence_time/60)}mins, reduction: {(1 - nosilence_time/audio_duration)*100:.2f}%")

        return intervals