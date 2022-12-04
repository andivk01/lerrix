import threading
import time
import subprocess
import re
import os
import shutil
import hashlib
from lib.utils.FFmpegUtils import duration, time_in_seconds

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
        if not os.path.exists(input):
            Unsilencer.set_status(unsilence, Unsilencer.ERROR, "Input file does not exist")
            return unsilence
        unsilence["video_length"] = duration(unsilence["input"])
        if unsilence["video_length"] is None:
            Unsilencer.set_status(unsilence, Unsilencer.ERROR, "Could not get video length")
            return unsilence
        Unsilencer.set_status(unsilence, Unsilencer.DETECTING)
        self.silencedetect(unsilence)
        if len(unsilence["intervals"]) == 0:
            Unsilencer.set_status(unsilence, Unsilencer.SKIPPED, "No interval with audio detected")
            return unsilence
        
        Unsilencer.set_status(unsilence, Unsilencer.EXTRACTING)
        self.audioextract(unsilence)
        if self.interrupt:
            return
        unsilence["start_reassembling_time"] = time.time()
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
            "-c:v", "libx264",
            "-preset", "veryfast",
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
                    unsilence["reassembling_progress"] = time_in_seconds(capture[1]) / unsilence["video_length"]
                capture = re.search("speed=([0-9.]+.?[0-9]*)x", line)
                if capture:
                    unsilence["reassembling_speed"] = float(capture[1])
        unsilence["end_reassembling_time"] = time.time()
        shutil.rmtree(unsilence["tmpdir"], ignore_errors=True)
        unsilence["end_time"] = time.time()
        Unsilencer.set_status(unsilence, Unsilencer.FINISHED, "finished")

    def audioextract(self, unsilence):
        unsilence["start_extracting_time"] = time.time()
        for idx_interval, interval in enumerate(unsilence["intervals"]):
            if self.interrupt:
                return
            unsilence["extracting_progress"] = (idx_interval+1) / len(unsilence["intervals"])
            file_chunk_out = os.path.join(unsilence["tmpdir"], str(idx_interval+1) + "." + Unsilencer.CHUNK_EXTENSION)
            command = [
                "ffmpeg",
                "-v", "quiet",
                "-stats", 
                "-ss", f"{interval[0]}",
                "-to", f"{interval[1]}",
                "-i", unsilence['input'],
                "-vsync", "1",
                "-async", "1",
                "-preset", "ultrafast",
                "-safe", "0",
                "-ignore_unknown", "-y",
                "-f", unsilence["file_extension"],
                file_chunk_out
            ]
            subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        unsilence["end_extracting_time"] = time.time()
    
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
                return
            if "[silencedetect" in line:
                capture = re.search("\\[silencedetect @ [0-9xa-f]+] silence_([a-z]+): (-?[0-9]+.?[0-9]*[e-]*[0-9]*)", line)
                if capture is not None:
                    unsilence["times"].append(float(capture[2]))
                    unsilence["detecting_progress"] = float(capture[2]) / unsilence["video_length"]
            if "frame=" in line:
                capture = re.search("time=([0-9:]+.?[0-9]*)", line)
                if capture is not None:
                    unsilence["detecting_progress"] = time_in_seconds(capture[1]) / unsilence["video_length"]

        new_times = [0] + unsilence["times"] + [unsilence["video_length"]]
        unsilence["intervals"] = []
        audio_detected = 0
        for i in range(0, len(new_times)-1, 2):
            if self.interrupt:
                return
            if new_times[i+1] - new_times[i] < 0.1: # if audio interval length is less than 0.1s=100ms
                continue
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
        
    def set_status(obj, status, status_msg="", status_details=""):
        obj["status_msg"] = status_msg
        obj["status_details"] = status_details
        obj["status"] = status
    
    def pretty_status(self):
        to_return = ""
        for unsilence in self.unsilences:
            if unsilence["status"] == Unsilencer.SKIPPED or unsilence["status"] == Unsilencer.NOT_UNSILENCING:
                continue
            to_return += f"File {unsilence['input']}:\n"
            to_return += f"Output: {unsilence['output']}\n"
            to_return += f"Unsilencing status: {unsilence['status']}\n"
            if unsilence["status"] == Unsilencer.ERROR or unsilence["status"] == Unsilencer.SKIPPED:
                to_return += f"Status_msg: {unsilence['status_msg']}\n"
                to_return += f"Details: {unsilence['status_details']}\n"
            elif unsilence["status"] == Unsilencer.FINISHED:
                to_return += f"Finished in {unsilence['end_time'] - unsilence['start_time']}s\n"
                to_return += f"Detected {unsilence['audio_detected']}s of audio\n"
                to_return += f"Detected in {unsilence['end_detecting_time'] - unsilence['start_detecting_time']}s\n"
                to_return += f"Extracted in {unsilence['end_extracting_time'] - unsilence['start_extracting_time']}s\n"
                to_return += f"Reassembled in {unsilence['end_reassembling_time'] - unsilence['start_reassembling_time']}s\n"
            elif unsilence["status"] == Unsilencer.DETECTING:
                to_return += f"Detecting: {(unsilence['detecting_progress'] * 100):.2f}%\n"
            elif unsilence["status"] == Unsilencer.EXTRACTING:
                extr_percent = (unsilence["extracting_progress"] * 100)
                to_return += f"Extracting: {(extr_percent):.2f}%\n"
                if unsilence["extracting_progress"] > 0:
                    time_elapsed = (time.time() - unsilence["start_extracting_time"])
                    to_return += f"Speed: {extr_percent / time_elapsed:.2f}%/s\n"
            elif unsilence["status"] == Unsilencer.REASSEMBLING:
                to_return += f"Reassembling: {(unsilence['reassembling_progress'] * 100):.2f}%\n"
                to_return += f"Reassembling speed: {unsilence['reassembling_speed']:.2f}x\n"
        return to_return