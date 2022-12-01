import sys
import os
import time
import threading
import json

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from lib.download.SP_Downloader import SP_Downloader
from lib.utils.PrintUtils import PrintUtils
from lib.scrape.DirScraper import DirScraper

data_directory = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
log_directory = os.path.join(data_directory, "logs")
# download_history = os.path.join(log_directory, "download_history.log")
# silence_history = os.path.join(log_directory, "silence_history.log")
unsilenced_videos_dir = "unsilenced_videos"
videos_dir = os.path.join(data_directory, "videos")
credentials_dir = os.path.join(data_directory, "credentials")
sp_dirs_file = os.path.join(data_directory, "sp_dirs_to_scan.json")
credentials_lastusername = os.path.join(data_directory, "credentials_lastusername")
credentials_password = os.path.join(data_directory, "credentials_password")
tmp_directory = os.path.join(data_directory, "tmp")

enc_key = "qCVjXuHqfNQ4JiuFD9iK" # random string used for encoding the credentials, TODO: INSICURE
sp_dirs = None

def init():
    if not os.path.exists(sp_dirs_file):
        print(f"{sp_dirs_file} not found, creating template to be filled")
        with open(sp_dirs_file, "w") as f:
            f.write(json.dumps([{"local_dir": "Local name directory", "url": "Sharepoint url directory", "file_prefix": "PREFIX ", "ignore-item" : "true"}], indent=4))
        exit(0)
    if not os.path.exists(tmp_directory):
        os.mkdir(tmp_directory)
    if not os.path.exists(log_directory):
        os.mkdir(log_directory)
    if not os.path.exists(videos_dir):
        os.mkdir(videos_dir)
# def init_local_dirs(sp_dirs):

#     # if not os.path.exists(download_history):
#     #     open(download_history, "w").close()
#     # if not os.path.exists(silence_history):
#     #     open(silence_history, "w").close()
#     # if not os.path.exists(unsilenced_videos_dir):
#         # os.mkdir(unsilenced_videos_dir)
def init_local_spdirs():
    for sp_dir in sp_dirs:
        video_dir_path = os.path.join(videos_dir, sp_dir["local_dir"])
        if not os.path.exists(video_dir_path):
            os.mkdir(video_dir_path)
        
        unsilenced_videos_dir_path = os.path.join(unsilenced_videos_dir, sp_dir["local_dir"])
        if not os.path.exists(unsilenced_videos_dir_path):
            os.mkdir(unsilenced_videos_dir_path)

def main():
    init()
    with open(sp_dirs_file) as json_file: # read sharepoint directories to scan
        sp_dirs = json.load(json_file)
    init_local_spdirs(sp_dirs)
    accounts = []
    
    for sp_dir in sp_dirs:
        sp_videos = []
        for account in accounts:
            if "ignore" in sp_dir and sp_dir["ignore"]:
                print("Ignoring ", sp_dir["local_dir"])
                continue
            print(f"Looking new Sharepoint videos for {sp_dir['local_dir']} using {account['username']}", end="\r")
            ds = DirScraper(
                dir_url=sp_dir["url"],
                username=account["username"],
                password=account["password"],
                cookies_file=account["cookies_file"]
            )
            print(" " * 100, end="\r")
            print(f"Scraped Sharepoint directory for {sp_dir['local_dir']} using {account['username']} in {ds.directory_content['total_time_to_load']} seconds")
            if len(ds.directory_content["videos"]) == 0:
                print(f"No videos found for {sp_dir['local_dir']} using {account['username']}")
                break
            for video in ds.directory_content["videos"]:
                found = False
                for sp_video in sp_videos:
                    if sp_video["filename"] == video["filename"]:
                        sp_video["sources"].append(video["manifest"])
                        found = True
                        break
                if not found:
                    sp_videos.append({
                        "filename": video["filename"],
                        "sources": [video["manifest"]]
                    })
        print("Now downloading videos")

        downloader = SP_Downloader(
            tmp_directory = tmp_directory,
            chunk_length = 600,
            chunk_threads = len(accounts)*2,
            download_history = None # TODO
        )

        for sp_video in sp_videos:
            args = (sp_video, sp_dir["file_prefix"], sp_dir["local_dir"])
            down_thread = threading.Thread(target=downloader.download_spvideo, args=args)
            down_thread.start()
            status = downloader.pretty_status()
            while(down_thread.is_alive()):
                status = downloader.pretty_status()
                print(status)
                time.sleep(0.5)
                PrintUtils.clear_line(status.count("\n")+1)
            print(status)


        # downloader.download_spvideos(
        #     videos=sp_videos,
        #     file_prefix=sp_dir["file_prefix"],
        #     output_dir=os.path.join(videos_dir, sp_dir["local_dir"])
        # )
                

if __name__ == "__main__":
    main()