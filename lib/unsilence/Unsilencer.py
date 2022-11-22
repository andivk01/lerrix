import threading
import time
import subprocess
import re
import os
import shutil
import hashlib
from lib.utils.FFmpegUtils import FFmpegUtils, duration, time_in_seconds
from lib.scrape.Video import Video

class Unsilencer:
    NOT_UNSILENCING = "NOT_UNSILENCING"
    DETECTING = "DETECTING"
    EXTRACTING = "EXTRACTING"
    REASSEMBLING = "REASSEMBLING"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"
    FINISHED = "FINISHED"

    CHUNK_EXTENSION = "chunk"
    CHUNK_CONCAT_FILENAME = "concat.txt"

    def __init__(self, tmp_directory):
        self.tmp_directory = tmp_directory
        if not os.path.exists(tmp_directory):
            try:
                os.makedirs(tmp_directory)
            except:
                raise ValueError("Could not create tmp directory")
        self.unsilences = []
        self.interrupt = False

    def unsilence(self, input, output, overwrite=False, dB=30, silence_length=0.5, ffmpeg_concat_mod_func=None):
        unsilence = {
            "id": str(hashlib.sha256(str(output).encode()).hexdigest()),
            "start_time": time.time(),
            "status": Unsilencer.NOT_UNSILENCING,
            "input": input,
            "output": output,
            "overwrite": overwrite,
            "filename": output.split("/")[-1],
            "file_extension": output.split(".")[-1],
            "thread_ident": threading.get_ident(),
            "detecting_progress": 0,
            "extracting_progress": 0,
            "reassembling_progress": 0,
            "reassembling_speed": 0,
            "dB": dB,
            "silence_length": silence_length
        }
        unsilence["tmpdir"] = os.path.join(self.tmp_directory, "tmp" + unsilence["id"])
        self.unsilences.append(unsilence)

        if self.interrupt:
            return unsilence        
        if os.path.exists(output) and not overwrite:
            Unsilencer.set_status(unsilence, Unsilencer.SKIPPED, "File already exists")
            return unsilence
        if not os.path.exists(unsilence["tmpdir"]):
            os.mkdir(unsilence["tmpdir"])
        unsilence["video_length"] = duration(unsilence["sources"][0])
        if unsilence["video_length"] is None:
            Unsilencer.set_status(unsilence, Unsilencer.ERROR, "Could not get video length")
            return unsilence
        Unsilencer.set_status(unsilence, Unsilencer.DETECTING)
        self.silencedetect(unsilence, dB, silence_length)
        if len(unsilence["intervals"]) == 0:
            Unsilencer.set_status(unsilence, Unsilencer.SKIPPED, "No interval with audio detected")
            return unsilence
        
        Unsilencer.set_status(unsilence, Unsilencer.EXTRACTING)
        self.audioextract(unsilence)
        Unsilencer.set_status(unsilence, Unsilencer.REASSEMBLING, "Reassembling")
        with open(os.path.join(unsilence["tmpdir"], Unsilencer.CHUNK_CONCAT_FILENAME), "w") as concat_file:
            for chunk_number in range(1, len(unsilence["intervals"]) + 1):
                concat_file.write(f"file '{os.path.join(unsilence['tmpdir'], str(chunk_number) + '.' + Unsilencer.CHUNK_EXTENSION)}'\n")

        ffmpeg_cmd = [
            "ffmpeg",
            "-v", "quiet",
            "-stats",
            "-f", "concat",
            "-safe", "0",
            "-i", os.path.join(unsilence["tmpdir"], Unsilencer.CHUNK_CONCAT_FILENAME),
            "-c", "copy",
            "-y",
            unsilence["output"]
        ]
        if ffmpeg_concat_mod_func is not None:
            ffmpeg_cmd = ffmpeg_concat_mod_func(ffmpeg_cmd)

        ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        ffmpeg_out = ffmpeg_process.stdout
        
        for line in ffmpeg_out:
            if self.interrupt:
                return unsilence
            if ffmpeg_process.poll() is not None and ffmpeg_process.returncode != 0:
                Unsilencer.set_status(unsilence, Unsilencer.ERROR, "Error while reassembling chunks", "ffmpeg returned " + str(ffmpeg_process.returncode))
            if line.startswith("frame="):
                capture = re.search("time=([0-9:]+.?[0-9]*)", line)
                if capture:
                    unsilence["reassembling_progress"] = time_in_seconds(capture[1])
                capture = re.search("speed=([0-9.]+.?[0-9]*)x", line)
                if capture:
                    unsilence["reassembling_speed"] = float(capture[1])

        shutil.rmtree(unsilence["tmpdir"], ignore_errors=True)
        unsilence["end_time"] = time.time()
        Unsilencer.set_status(unsilence, Unsilencer.FINISHED, "finished")

    def audioextract(self, unsilence):
        for idx_interval, interval in enumerate(unsilence["intervals"]):
            if self.interrupt:
                return # TODO
            unsilence["extracting_progress"] = (idx_interval+1) / len(unsilence["intervals"])
            file_chunk_out = os.path.join(unsilence["tmpdir"], str(idx_interval+1) + "." + Unsilencer.CHUNK_EXTENSION)
            command = [ # TODO check if reencoding is necessary?
                "ffmpeg",
                "-v", "quiet",
                "-stats", 
                "-ss", f"{interval[0]}",
                "-to", f"{interval[1]}",
                "-i", unsilence['input'],
                "-vsync", "1",
                "-async", "1",
                "-safe", "0",
                "-ignore_unknown", "-y",
                "-f", unsilence["file_extension"],
                file_chunk_out
            ]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    
    def silencedetect(self, unsilence):
        unsilence["start_detecting_time"] = time.time()
        cmd = [
            'ffmpeg',
            '-y', 
            '-i', unsilence["input"],
            '-af',
            f'silencedetect=noise=-{unsilence["dB"]}dB:d={unsilence["silence_length"]}',
            "-f", "null", "-"
        ]
        console_output = subprocess.Popen(
            cmd,
            stdout = subprocess.PIPE,
            stderr = subprocess.STDOUT,
            universal_newlines = True
        ).stdout
        unsilence["times"] = []
        for line in console_output:
            if self.interrupt:
                return # TODO
            if "[silencedetect" in line:
                capture = re.search("\\[silencedetect @ [0-9xa-f]+] silence_([a-z]+): (-?[0-9]+.?[0-9]*[e-]*[0-9]*)", line)
                if capture is not None:
                    unsilence["times"].append(float(capture[2]))
                    unsilence["detecting_progress"] = float(capture[2]) / unsilence["video_length"]
            if "frame=" in line:
                capture = re.search("time=([0-9:]+.?[0-9]*)", line)
                if capture is not None:
                    unsilence["detecting_progress"] = duration(capture[1]) / unsilence["video_length"]

        new_times = [0] + new_times + [unsilence["video_length"]]
        unsilence["intervals"] = []
        audio_detected = 0
        for i in range(0, len(new_times)-1, 2):
            if self.interrupt:
                return # TODO
            if new_times[i+1] - new_times[i] < 0.1: # if audio interval length is less than 0.1s=100ms
                continue
            # if new_times[i] == new_times[i+1]: TODO remove? Considering if-statement above...
            #     continue
            audio_detected += new_times[i+1] - new_times[i]
            if i > 0:
                if new_times[i-1] < new_times[i] - 0.02: # add 20ms on left of the interval
                    new_times[i] = new_times[i] - 0.02
            if i < len(new_times)-2:
                if new_times[i+2] > new_times[i+1] + 0.02:
                    new_times[i+1] = new_times[i+1] + 0.02
            unsilence["intervals"].append((new_times[i], new_times[i+1]))
        unsilence["audio_detected"] = audio_detected
        unsilence["end_detecting_time"] = time.time()
        
    def set_status(obj, status, status_msg=None, status_details=None):
        obj["status"] = status
        if status_msg is not None:
            obj["status_msg"] = status_msg
        if status_details is not None:
            obj["status_details"] = status_details
    
    def pretty_status(self):
        to_return = ""
        for unsilence in self.unsilences:
            to_return += f"File {unsilence['input']}:\n"
            to_return += f"Output: {unsilence['output']}\n"
            to_return += f"Status: {unsilence['status']}\n"
            if unsilence["status"] == Unsilencer.ERROR:
                to_return += f"Error: {unsilence['status_msg']}\n"
                to_return += f"Details: {unsilence['status_details']}\n"
            elif unsilence["status"] == Unsilencer.FINISHED:
                to_return += f"Finished in {unsilence['end_time'] - unsilence['start_time']}s\n"
                to_return += f"Detected {unsilence['audio_detected']}s of audio\n"
                to_return += f"Detected in {unsilence['end_detecting_time'] - unsilence['start_detecting_time']}s\n"
                to_return += f"Extracted in {unsilence['end_extracting_time'] - unsilence['start_extracting_time']}s\n"
                to_return += f"Reassembled in {unsilence['end_reassembling_time'] - unsilence['start_reassembling_time']}s\n"
            elif unsilence["status"] == Unsilencer.DETECTING:
                to_return += f"Detecting: {unsilence['detecting_progress'] * 100}%\n"
            elif unsilence["status"] == Unsilencer.EXTRACTING:
                to_return += f"Extracting: {unsilence['extracting_progress'] * 100}%\n"
            elif unsilence["status"] == Unsilencer.REASSEMBLING:
                to_return += f"Reassembling: {unsilence['reassembling_progress'] * 100}%\n"
            to_return += "\n"
        return to_return