from DirScraper import DirScraper
from Silencer import Silencer
from Downloader import Downloader
import keyring
import os
import argparse
import json

last_username_key = "last_username"
keyring_id = "lerrix_keyring"
log_directory = "logs"
download_history = f"{log_directory}/download_history.log"
silence_history = f"{log_directory}/silence_history.log"
unsilenced_videos_dir = "unsilenced_videos"
videos_dir = "videos"
sp_dirs_file = "sp_dirs_to_scan.json"
codecs_available = ["copy", "libx265", "libx264", "h264_amf"]

def credentials():
    username = keyring.get_password(keyring_id, last_username_key)
    if username is None:
        username = input("Username: ")
        keyring.set_password(keyring_id, last_username_key, username)
    else:
        print("Using username: " + username)
    password = keyring.get_password(keyring_id, username)
    if password is None:
        password = input("Password: ")
        keyring.set_password(keyring_id, username, password)
    else:
        print("Using password from keyring")
    return username, password

def init_local_dirs(sp_dirs):
    if not os.path.exists(log_directory):
        os.mkdir(log_directory)
    if not os.path.exists(unsilenced_videos_dir):
        os.mkdir(unsilenced_videos_dir)
    if not os.path.exists(videos_dir):
        os.mkdir(videos_dir)
    for sp_dir in sp_dirs:
        video_dir_path = videos_dir + "/" + sp_dir["local_dir"]
        if not os.path.exists(video_dir_path):
            os.mkdir(video_dir_path)
        
        unsilenced_videos_dir_path = unsilenced_videos_dir + "/" + sp_dir["local_dir"]
        if not os.path.exists(unsilenced_videos_dir_path):
            os.mkdir(unsilenced_videos_dir_path)

if __name__ == "__main__":
    # arguments for executing only one of the functionalities, TODO
    # TODO: add argument for reading manifests from file instead of scraping (when running all scripts at once)
    parser = argparse.ArgumentParser(description='LERRIX v0.1')
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--manifests", help="Download manifests from sharepoint's directory url")
    group.add_argument("--download", help="Download video by URL")
    group.add_argument("--unsilence", help="Unsilence video by videopath")
    parser.add_argument("--output", help="Output file/directory path")
    parser.add_argument("--dvcodec", help="Video codec for downloader's output", choices=codecs_available, default="libx264")
    parser.add_argument("--svcodec", help="Video codec for silencer's output", choices=codecs_available, default="libx265")
    args = parser.parse_args()

    if args.manifests:
        if args.manifests.startswith("https://"):
            username, password = credentials()
            ds = DirScraper(args.manifests, username, password, log_file=args.output)
            time_to_load = ds.load()
            print(f"Loaded in {time_to_load:.2f} seconds, output in {args.output}")
            ds.driver_quit()
    elif args.download:
        print("Not implemented yet")
    elif args.unsilence:
        print("Not implemented yet")
    else:
        print("No arguments passed, running all the script")

        with open(sp_dirs_file) as json_file: # read sharepoint directories to scan
            sp_dirs = json.load(json_file)
        init_local_dirs(sp_dirs)

        username, password = credentials()

        for sp_dir in sp_dirs:
            ds = DirScraper(sp_dir["url"], username, password, log_file=f"{log_directory}/{sp_dir['local_dir']}.log")
            time_to_load = ds.load()
            print(f"Loaded {sp_dir['local_dir']} in {time_to_load} seconds")
            
            video_dir_path = videos_dir + "/" + sp_dir["local_dir"]
            unsilenced_videos_dir_path = unsilenced_videos_dir + "/" + sp_dir["local_dir"]

            downloader = Downloader(download_history) # download_history is used to avoid downloading the same file twice
            downloaded_videos = downloader.download_videos(
                videos = ds.videos,
                output_dir = video_dir_path,
                file_prefix = sp_dir["file_prefix"],
                ffmpeg_params = sp_dir["ffmpeg_download_params"],
                codec=args.dvcodec
            )
            silencer = Silencer(silence_history) # silence_history is used to avoid silencing the same file twice
            silencer.unsilence_videos(downloaded_videos, unsilenced_videos_dir_path, codec=args.svcodec)
            
            ds.driver_quit()