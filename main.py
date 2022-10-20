from DirScraper import DirScraper
from PrintColors import PrintColors
from Silencer import Silencer
from Downloader import Downloader
from getpass import getpass
import os
import argparse
import json
import shutil
from DataKeeper import DataKeeper

last_username_key = "last_username"
log_directory = "logs"
download_history = os.path.join(log_directory, "download_history.log")
silence_history = os.path.join(log_directory, "silence_history.log")
unsilenced_videos_dir = "unsilenced_videos"
videos_dir = "videos"
sp_dirs_file = "sp_dirs_to_scan.json"
codecs_available = ["copy", "libx265", "libx264", "h264_amf"]
credentials_lastusername = "credentials_lastusername"
credentials_password = "credentials_password"
tmp_directory = "tmp"

enc_key = "qCVjXuHqfNQ4JiuFD9iK" # random string used for encoding the credentials, TODO: INSICURE

def credentials():
    pkeeper = DataKeeper(credentials_lastusername, enc_key)
    username = pkeeper.load()
    if username is None:
        username = input("Username: ")
        pkeeper.store(username)
    else:
        print("Using username: " + username)

    pkeeper = DataKeeper(credentials_password, enc_key)
    password = pkeeper.load()
    if password is None:
        password = getpass("Password (hidden): ")
        pkeeper.store(password)
    else:
        print("Using password from credentials_password")
    return username, password

def init_local_dirs(sp_dirs):
    if os.path.exists(tmp_directory):
        shutil.rmtree(tmp_directory)
    os.mkdir(tmp_directory)
    if not os.path.exists(log_directory):
        os.mkdir(log_directory)
    if not os.path.exists(download_history):
        open(download_history, "w").close()
    if not os.path.exists(silence_history):
        open(silence_history, "w").close()
    if not os.path.exists(unsilenced_videos_dir):
        os.mkdir(unsilenced_videos_dir)
    if not os.path.exists(videos_dir):
        os.mkdir(videos_dir)
    for sp_dir in sp_dirs:
        video_dir_path = os.path.join(videos_dir, sp_dir["local_dir"])
        if not os.path.exists(video_dir_path):
            os.mkdir(video_dir_path)
        
        unsilenced_videos_dir_path = os.path.join(unsilenced_videos_dir, sp_dir["local_dir"])
        if not os.path.exists(unsilenced_videos_dir_path):
            os.mkdir(unsilenced_videos_dir_path)

if __name__ == "__main__":
    # arguments for executing only one of the functionalities, TODO
    # TODO: add argument for reading manifests from file instead of scraping (when running all scripts at once)
    parser = argparse.ArgumentParser(description='LERRIX v0.1')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--credentials', action='store_true', help='Change credentials')
    group.add_argument("--scrape-spdirs", help="Download manifests from sharepoint's directory url")
    group.add_argument("--download", help="Download video by URL")
    group.add_argument("--unsilence", help="Unsilence video by videopath")
    group.add_argument("--download-spdirs", help="Download all videos from sharepoint directories (without unsilencing)", nargs="?", const=True)
    parser.add_argument("--output", help="Output file/directory path")
    parser.add_argument("--dvcodec", help="Video codec for downloader's output", choices=codecs_available, default="libx264")
    parser.add_argument("--svcodec", help="Video codec for silencer's output", choices=codecs_available, default="libx265")
    parser.add_argument("--d-ow", help="Overwrite existing files while downloading", action="store_true")
    parser.add_argument("--ffmpeg-threads", help="Number of threads for ffmpeg", type=int, default=2)
    args = parser.parse_args()

    if args.scrape_spdirs:
        if args.scrape_spdirs.startswith("https://"):
            username, password = credentials()
            ds = DirScraper(args.scrape_spdirs, username, password, log_file=args.output)
            time_to_load = ds.load(download_history)
            print(f"Loaded in {time_to_load:.2f} seconds, output in {args.output}")
            ds.driver_quit()
    elif args.download:
        print("Not implemented yet")
    elif args.unsilence:
        print("Not implemented yet")
    elif args.credentials:
        if os.path.exists(credentials_lastusername):
            os.remove(credentials_lastusername)
        if os.path.exists(credentials_password):
            os.remove(credentials_password)
        credentials()
    else:
        with open(sp_dirs_file) as json_file: # read sharepoint directories to scan
            sp_dirs = json.load(json_file)
        PrintColors.set_color(PrintColors.OKYELLOW)
        init_local_dirs(sp_dirs)
        username, password = credentials()

        for sp_dir in sp_dirs:
            PrintColors.set_color(PrintColors.OKGREEN)
            if "ignore-item" in sp_dir and sp_dir["ignore-item"]:
                print(f"Ignoring {sp_dir['local_dir']}")
                continue
            ds = DirScraper(sp_dir["url"], username, password, log_file=f"{log_directory}/{sp_dir['local_dir']}.log")
            time_to_load = ds.load(download_history)
            print(f"Loaded {sp_dir['local_dir']} in {time_to_load:.2f} seconds")
            ds.driver_quit()

            video_dir_path = os.path.join(videos_dir, sp_dir["local_dir"])
            unsilenced_videos_dir_path = os.path.join(unsilenced_videos_dir, sp_dir["local_dir"])

            PrintColors.set_color(PrintColors.OKCYAN)
            downloader = Downloader(download_history) # download_history is used to avoid downloading the same file twice
            downloaded_videos = downloader.download_videos(
                videos = ds.videos,
                output_dir = video_dir_path,
                file_prefix = sp_dir["file_prefix"],
                ffmpeg_params = sp_dir["ffmpeg_download_params"],
                codec = args.dvcodec,
                overwrite = args.d_ow,
            )
            if not args.download_spdirs:
                PrintColors.set_color(PrintColors.OKMAGENTA)
                silencer = Silencer(silence_history) # silence_history is used to avoid silencing the same file twice
                silencer.unsilence_videos(downloaded_videos, unsilenced_videos_dir_path, codec=args.svcodec)