import time
import subprocess
import os
import shutil
import re
import math
import threading
import time
import hashlib
import traceback
from concurrent.futures import ThreadPoolExecutor
from lib.utils.FFmpegUtils import duration, time_in_seconds
from lib.utils.SPUtils import handle_exc

class Downloader:
    NOT_DOWNLOADING = "NOT_DOWNLOADING"
    DOWNLOADING = "DOWNLOADING"
    REASSEMBLING = "REASSEMBLING"
    SKIPPED = "SKIPPED"
    FINISHED = "FINISHED"
    ERROR = "ERROR"
    DONE_CONSTS = ["FINISHED", "ERROR", "SKIPPED"]

    UNDONE_PREFIX = "undone_"
    BROKEN_PREFIX = "broken_"
    CHUNK_EXTENSION = "chunk"
    CHUNK_CONCAT_FILENAME = "concat.txt"

    def __init__(self, tmp_directory, chunk_length=600, chunk_threads=1):
        assert chunk_length > 0
        assert chunk_threads > 0
        if not os.path.exists(tmp_directory):
            try:
                os.makedirs(tmp_directory)
            except:
                raise ValueError("Could not create tmp directory")
        
        self.tmp_directory = tmp_directory
        self.downloads = []
        self.chunk_length = chunk_length
        self.chunk_threads = chunk_threads
        self.interrupt = False

    def download(self, sources, output, overwrite=False, ffmpeg_mod_func=None, ffmpeg_concat_mod_func=None):
        assert len(sources) > 0
        assert output is not None
        if not os.path.exists(os.path.dirname(output)):
            os.makedirs(os.path.dirname(output))

        download = {
            "id": str(hashlib.sha256(str(output).encode()).hexdigest()),
            "start_time": time.time(),
            "status": Downloader.NOT_DOWNLOADING,
            "sources": sources,
            "output": output,
            "overwrite": overwrite,
            "filename": output.split("/")[-1],
            "file_extension": output.split(".")[-1],
            "chunk_length": self.chunk_length,
            "current_chunk": 1,
            "chunks": [],
            "thread_ident": threading.get_ident(),
            "reassembling_progress": 0,
            "reassembling_speed": 0
        }
        download["tmpdir"] = os.path.join(self.tmp_directory, "tmp" + download["id"])
        self.downloads.append(download)
        if self.interrupt:
            return download
        if os.path.exists(output) and not overwrite:
            Downloader.set_status(download, Downloader.SKIPPED, "File already exists")
            return download
        
        if not os.path.exists(download["tmpdir"]):
            os.mkdir(download["tmpdir"])
        else:
            downloaded_chunks = [
                f.split(".")[0] for f in os.listdir(download["tmpdir"]) 
                if (not f.startswith(Downloader.UNDONE_PREFIX)) and f.endswith(Downloader.CHUNK_EXTENSION) 
            ]
            undone_chunks = [
                f.split(".")[0].replace(Downloader.UNDONE_PREFIX, "") for f in os.listdir(download["tmpdir"])
                if f.startswith(Downloader.UNDONE_PREFIX) and f.endswith(Downloader.CHUNK_EXTENSION)
            ]
            try:
                downloaded_chunks = [int(elem) for elem in downloaded_chunks]
                undone_chunks = [int(elem) for elem in undone_chunks]
            except:
                Downloader.set_status(download, Downloader.ERROR, "Error while casting downloaded/undone chunks to int", traceback.format_exc())
                download["total_time"] = time.time() - download["start_time"]
                return download
            if len(downloaded_chunks) > 0:
                download["current_chunk"] = max(downloaded_chunks) + 1
            if len(undone_chunks) > 0:
                download["current_chunk"] = min(undone_chunks)
            download["chunks"] = [{"number": chunk_number, "status": Downloader.SKIPPED} for chunk_number in downloaded_chunks]
        
        download["video_length"] = duration(download["sources"][0])
        if download["video_length"] is None:
            Downloader.set_status(download, Downloader.ERROR, "Could not get video length")
            download["total_time"] = time.time() - download["start_time"]
            return download
        download["n_chunks"] = math.ceil(download["video_length"] / self.chunk_length)
        Downloader.set_status(download, Downloader.DOWNLOADING, "Downloading")

        with ThreadPoolExecutor(max_workers=self.chunk_threads) as executor:
            for chunk_number in range(download["current_chunk"], download["n_chunks"] + 1):
                download_chunk_func = handle_exc()(self.download_chunk)
                executor.submit(download_chunk_func, download, chunk_number, ffmpeg_mod_func=ffmpeg_mod_func)

        if self.interrupt:
            return download

        Downloader.set_status(download, Downloader.REASSEMBLING, "Reassembling")
        with open(os.path.join(download["tmpdir"], Downloader.CHUNK_CONCAT_FILENAME), "w") as concat_file:
            for chunk_number in range(1, download["n_chunks"] + 1):
                concat_file.write(f"file '{os.path.join(download['tmpdir'], str(chunk_number) + '.' + Downloader.CHUNK_EXTENSION)}'\n")

        ffmpeg_cmd = [
            "ffmpeg",
            "-v", "quiet",
            "-stats",
            "-f", "concat",
            "-safe", "0",
            "-i", os.path.join(download["tmpdir"], Downloader.CHUNK_CONCAT_FILENAME),
            "-c", "copy",
            "-y",
            download["output"]
        ]
        if ffmpeg_concat_mod_func is not None:
            ffmpeg_cmd = ffmpeg_concat_mod_func(ffmpeg_cmd)

        ffmpeg_process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        ffmpeg_out = ffmpeg_process.stdout
        
        for line in ffmpeg_out:
            if self.interrupt:
                return download
            if ffmpeg_process.poll() is not None and ffmpeg_process.returncode != 0:
                Downloader.set_status(download, Downloader.ERROR, "Error while reassembling chunks", "ffmpeg returned " + str(ffmpeg_process.returncode))
            if line.startswith("frame="):
                capture = re.search("time=([0-9:]+.?[0-9]*)", line)
                if capture:
                    download["reassembling_progress"] = time_in_seconds(capture[1])
                capture = re.search("speed=([0-9.]+.?[0-9]*)x", line)
                if capture:
                    download["reassembling_speed"] = float(capture[1])

        output_duration = duration(download["output"])
        if output_duration is not None:
            duration_diff = math.fabs(output_duration - download["video_length"])
            if duration_diff > 1:
                Downloader.set_status(download, Downloader.ERROR, "Error while reassembling chunks", f"Output file duration is not the same as the video length, difference of {duration_diff}s")
                os.rename(download["output"], os.path.join(os.path.dirname(download["output"]), Downloader.BROKEN_PREFIX + os.path.basename(download["output"])))
                return download
        else:
            print("WARNING: Could not get output duration, cannot check if it is the same as the video length.")

        shutil.rmtree(download["tmpdir"], ignore_errors=True)

        download["time_to_download"] = time.time() - download["start_time"]
        Downloader.set_status(download, Downloader.FINISHED, "finished")
        return download

    def download_chunk(self, download, chunk_number, source_idx=None, ffmpeg_mod_func=None):
        if self.interrupt:
            return
        chunk = {
            "number": chunk_number,
            "status": Downloader.DOWNLOADING,
            "progress": 0,
            "speed": 0,
            "start_time": time.time(),
            "tmp_output": os.path.join(download["tmpdir"], f"{Downloader.UNDONE_PREFIX}{chunk_number}.{Downloader.CHUNK_EXTENSION}"),
            "output": os.path.join(download["tmpdir"], f"{chunk_number}.{Downloader.CHUNK_EXTENSION}"),
        }
        download["chunks"].append(chunk)
        download["current_chunk"] = chunk_number

        if os.path.exists(chunk["output"]):
            Downloader.set_status(chunk, Downloader.SKIPPED, "Chunk already downloaded")
            return
        if source_idx is None:
            source_idx = chunk_number % len(download["sources"])
        chunk["ffmpeg_cmd"] = [
            "ffmpeg", 
            "-ss", str((chunk_number-1) * self.chunk_length),
            "-t", str(self.chunk_length),
            "-i",
            download["sources"][source_idx],
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "34",
            "-f", download["file_extension"],
            "-y", chunk["tmp_output"]
        ]
        if ffmpeg_mod_func is not None:
            chunk["ffmpeg_cmd"] = ffmpeg_mod_func(chunk["ffmpeg_cmd"])

        ffmpeg_process = subprocess.Popen(chunk["ffmpeg_cmd"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        ffmpeg_out = ffmpeg_process.stdout

        for line in ffmpeg_out:
            if self.interrupt:
                return
            if ffmpeg_process.poll() is not None and ffmpeg_process.returncode != 0 or "NULL @" in line or "HTTP ERROR" in line.upper():
                print(line) # TODO
                Downloader.set_status(chunk, Downloader.ERROR, "Error while downloading chunk", "ffmpeg returned " + str(ffmpeg_process.returncode + " while executing " + " ".join(chunk["ffmpeg_cmd"])))
                Downloader.set_status(download, Downloader.ERROR, "Error while downloading chunk", "ffmpeg returned " + str(ffmpeg_process.returncode + " while executing " + " ".join(chunk["ffmpeg_cmd"])))
                self.interrupt = True
                return

            if line.startswith("frame="):
                capture = re.search("time=([0-9:]+.?[0-9]*)", line)
                if capture:
                    chunk["progress"] = time_in_seconds(capture[1])
                capture = re.search("speed=([0-9.]+.?[0-9]*)x", line)
                if capture:
                    chunk["speed"] = float(capture[1])

        if os.path.exists(chunk["tmp_output"]):
            os.rename(chunk["tmp_output"], chunk["output"])
        else:
            Downloader.set_status(chunk, Downloader.ERROR, "Error while downloading chunk", f"Cannot find downloaded chunk ({chunk['tmp_output']}) while moving it to final destination")
            Downloader.set_status(download, Downloader.ERROR, "Error while downloading chunk", f"Cannot find downloaded chunk ({chunk['tmp_output']}) while moving it to final destination")
            self.interrupt = True
            return
        chunk["time_to_download"] = time.time() - chunk["start_time"]
        Downloader.set_status(chunk, Downloader.FINISHED, "finished")

    def set_status(obj, status, status_msg=None, status_details=None):
        obj["status"] = status
        if status_msg is not None:
            obj["status_msg"] = status_msg
        if status_details is not None:
            obj["status_details"] = status_details

    def pretty_status(self): # used for debug purposes
        to_return = ""
        total_progress = 0
        total_speed = 0
        for download in self.downloads:
            to_return += f"File: {download['filename']}\n"
            to_return += f"Status: {download['status']}\n"
            to_return += f"n_sources: {len(download['sources'])}\n"
            if "n_chunks" in download:
                to_return += f"n_chunks: {download['n_chunks']}\n"
                to_return += f"current_chunk: {download['current_chunk']}\n"
            if "reassembling_progress" in download:
                to_return += f"reassembling_progress: {download['reassembling_progress']}\n"
                to_return += f"reassembling_speed: {download['reassembling_speed']}\n"
            if "time_to_download" in download:
                to_return += f"time_to_download: {download['time_to_download']}\n"

            to_return += f"tmpdir: {download['tmpdir']}\n"
            if download["status"] == Downloader.DOWNLOADING:
                to_return += f"video_length: {download['video_length']}\n"
                to_return += f"Chunks {download['current_chunk']}/{download['n_chunks']}:\n"

                for chunk in download["chunks"]:
                    if chunk["status"] == Downloader.DOWNLOADING:
                        total_progress += chunk["progress"]
                        total_speed += chunk["speed"]
                        to_return += f"\tChunk_{chunk['number']}: {chunk['status']} {int(chunk['progress'])}/{self.chunk_length}s {chunk['speed']}x\n"
                    elif chunk["status"] == Downloader.FINISHED or chunk["status"] == Downloader.SKIPPED:
                        total_progress += self.chunk_length # TODO 
                        to_return += f"\tChunk_{chunk['number']}: {chunk['status']}\n"
                    elif chunk["status"] == Downloader.ERROR:
                        to_return += f"\tChunk_{chunk['number']}:"
                        if "status_msg" in chunk:
                            to_return += f"\tError: {chunk['status_msg']}\n"
                        if "status_details" in chunk:
                            to_return += f"\tError details: {chunk['status_details']}\n"
                        if "ffmpeg_cmd" in chunk:
                            ffmpeg_cmd_str = " ".join(chunk["ffmpeg_cmd"])
                            to_return += f"\tffmpeg_cmd: {ffmpeg_cmd_str}\n"
                to_return += f"Total progress: {int(total_progress)}/{download['video_length']}s\n"
                to_return += f"Total speed: {total_speed:.2f}x\n"
            elif download["status"] == Downloader.REASSEMBLING:
                to_return += f"Reassembling progress: {download['reassembling_progress']}/{download['video_length']}\n"
                to_return += f"Reassembling speed: {download['reassembling_speed']}\n"
            elif download["status"] == Downloader.ERROR:
                if "status_msg" in download:
                    to_return += f"Error: {download['status_msg']}\n"
                if "status_details" in download:
                    to_return += f"Error details: {download['status_details']}\n"
        return to_return