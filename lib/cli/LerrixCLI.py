import sys
import os
import time
import threading
import json
from lib.download.Downloader import Downloader

from lib.download.SP_Downloader import SP_Downloader
from lib.utils import SPUtils
from lib.utils.PrintUtils import PrintUtils
from lib.scrape.MultiDirScraper import MultiDirScraper
from lib.unsilence.Unsilencer import Unsilencer

from lib.utils.DataKeeper import DataKeeper
from lib.utils.SPUtils import format_filename, handle_exc

class LerrixCLI:
    DEFAULT_CONFIG_FILE_LOCATION = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "lerrix_config.json")
    ENC_KEY = "qCVjXuHqfNQ4JiuFD9iK"
    SCRAPE_THREADS = 1

    def __init__(self, config_file_location=DEFAULT_CONFIG_FILE_LOCATION):
        self.config_file_location = config_file_location
        self.config = self.init_config()
        if self.config is None:
            print("Config file not found, created template to be filled")
            exit(0)
        self.init_local_dirs()
        self.accounts = self.init_accounts_and_cookies()

    def ignore_btn_from_scraping(self, btn): # TODO: place somewhere else these functions
        return self.ignore_from_downloading(btn.text)
    def ignore_from_downloading(self, video_title):
        with open(self.config["download_history_file"], "r") as f:
            for line in f:
                if video_title in line or format_filename(video_title) in line:
                    return True
        return False
    def ignore_from_unsilencing(self, video_title): # TODO: place somewhere else these functions
        with open(self.config["unsilence_history_file"], "r") as f:
            for line in f:
                if video_title in line or format_filename(video_title) in line:
                    return True
        return False

    def run(self):
        for sp_dir in self.config["sp_dirs"]:
            if sp_dir["ignore-item"]:
                print("Ignoring item: " + sp_dir["local_dir"])
                continue
            print(f"Scraping new content from directory: {sp_dir['local_dir']}")
            multidir_scraper = MultiDirScraper(sp_dir["url"], self.accounts, scraping_threads=self.config["scraping_threads"])
            multidir_scraper.load(ignore_func_btn=self.ignore_btn_from_scraping, then_quit=True)
            PrintUtils.clear_line()
            print(f"Scraped new content from directory: {sp_dir['local_dir']} in {multidir_scraper.directory_content['total_time_to_load']}s")
            downloader = SP_Downloader(
                tmp_directory = self.config["tmp_directory"],
                chunk_length = self.config["download_chunk_length"],
                chunk_threads = min(self.config["download_chunk_threads"], len(self.accounts))
            )
            videos_to_download = [{"filename": video["filename"], "sources": video["manifests"]} for video in multidir_scraper.directory_content["videos"]]
            output_download_dir = os.path.join(self.config["videos_dir"], sp_dir["local_dir"])
            download_spvideos_func = handle_exc()(downloader.download_spvideos)
            ffmpeg_mod_func = None
            if "ffmpeg_add_params" in sp_dir and len(sp_dir["ffmpeg_add_params"]) > 0:
                ffmpeg_mod_func = lambda x: SPUtils.ffmpeg_add_params(x, sp_dir["ffmpeg_add_params"])
            thread = threading.Thread(target=download_spvideos_func, args=(videos_to_download, sp_dir["file_prefix"], output_download_dir, ffmpeg_mod_func))
            thread.start()
            try:
                while thread.is_alive():
                    status = downloader.pretty_status()
                    print(status, end="")
                    time.sleep(1.5)
                    PrintUtils.clear_line(status.count("\n"))
            except KeyboardInterrupt:
                downloader.interrupt = True
                print("Download stopped")
                sys.exit(0)
            for download in downloader.downloads:
                if download["status"] == Downloader.FINISHED:
                    with open(self.config["download_history_file"], "a") as f:
                        print("Logged download: " + download["filename"])
                        f.write(download["filename"] + "\n")

            unsilencer = Unsilencer(self.config["tmp_directory"])

            for input in os.listdir(os.path.join(self.config["videos_dir"], sp_dir["local_dir"])):
                input_filename = os.path.basename(input)
                input = os.path.join(self.config["videos_dir"], sp_dir["local_dir"], input)
                output = os.path.join(self.config["unsilenced_videos_dir"], sp_dir["local_dir"], input_filename)
                thread = threading.Thread(target=unsilencer.unsilence, args=(input, output))
                thread.start()
                try:
                    while thread.is_alive():
                        status = unsilencer.pretty_status()
                        print(status, end="")
                        time.sleep(1.5)
                        PrintUtils.clear_line(status.count("\n"))
                except KeyboardInterrupt:
                    unsilencer.interrupt = True
                    print("Unsilencing stopped")
                    sys.exit(0)
            for unsilence in unsilencer.unsilences:
                if unsilence["status"] == Unsilencer.FINISHED:
                    with open(self.config["unsilence_history_file"], "a") as f:
                        print("Logged unsilence: " + unsilence["filename"])
                        f.write(unsilence["filename"] + "\n")
    def init_local_dirs(self):
        dirs_to_create = [
            self.config["data_directory"],
            self.config["tmp_directory"],
            self.config["log_directory"],
            self.config["unsilenced_videos_dir"],
            self.config["videos_dir"],
            self.config["accounts_dir"],
            self.config["unsilenced_videos_dir"],
            self.config["cookies_dir"]
        ]
        for d in dirs_to_create:
            if not os.path.exists(d):
                print("Creating directory: " + d)
                os.makedirs(d)
        sorted_sp_dirs = self.config["sp_dirs"]
        sorted_sp_dirs.sort(key=lambda x: x["priority"])

        for sp_dir in sorted_sp_dirs:
            if sp_dir["ignore-item"]:
                print("Ignoring item: " + sp_dir["local_dir"])
                continue
            dirs_to_create = [
                os.path.join(self.config["videos_dir"], sp_dir["local_dir"]),
                os.path.join(self.config["unsilenced_videos_dir"], sp_dir["local_dir"])
            ]
            for d in dirs_to_create:
                if not os.path.exists(d):
                    print("Creating directory: " + d)
                    os.makedirs(d)
        if not os.path.exists(self.config["download_history_file"]):
            with open(self.config["download_history_file"], "w") as f:
                f.write("")
        if not os.path.exists(self.config["unsilence_history_file"]):
            with open(self.config["unsilence_history_file"], "w") as f:
                f.write("")
    def init_accounts_and_cookies(self):
        accounts = []
        account_files = os.listdir(self.config["accounts_dir"])
        if len(account_files) == 0:
            print("No accounts found in accounts directory, please add accounts to the directory")
            exit(0)
        for account_file in account_files:
            account_file_path = os.path.join(self.config["accounts_dir"], account_file)
            cookie_file_path = os.path.join(self.config["cookies_dir"], account_file)
            dkeeper = DataKeeper(account_file_path, self.ENC_KEY)
            psw = dkeeper.load()
            if psw is None:
                print("No password found for account: " + account_file)
                continue
            accounts.append({"username": account_file, "password": psw, "cookie_file": cookie_file_path})

        for cookie_file in os.listdir(self.config["cookies_dir"]):
            if cookie_file not in account_files:
                print("Cookie file found without account: " + cookie_file)
                accounts.append({"username": None, "password": None, "cookie_file": cookie_file})
        
        return accounts

    def init_config(self):
        if not os.path.exists(self.config_file_location):
            config = {}
            config["data_directory"] = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")
            config["tmp_directory"] = os.path.join(config["data_directory"], "tmp")
            config["log_directory"] = os.path.join(config["data_directory"], "logs")
            config["download_history_file"] = os.path.join(config["data_directory"], "logs", "download_history.log")
            config["unsilence_history_file"] = os.path.join(config["data_directory"], "logs", "unsilence_history.log")
            config["unsilenced_videos_dir"] = os.path.join(config["data_directory"], "unsilenced_videos")
            config["videos_dir"] = os.path.join(config["data_directory"], "videos")
            config["accounts_dir"] = os.path.join(config["data_directory"], "accounts")
            config["cookies_dir"] = os.path.join(config["data_directory"], "cookies")
            config["sp_dirs"] = [{"local_dir": "Local name directory", "url": "Sharepoint url directory", "file_prefix": "PREFIX ", "ignore-item": "true", "priority": 1}]
            config["scraping_threads"] = 1
            config["download_chunk_threads"] = 1
            config["download_chunk_length"] = 600
            with open(self.config_file_location, "w") as f:
                f.write(json.dumps(config, indent=4))
            return None
        else:
            with open(self.config_file_location, "r") as f:
                return json.load(f)
        