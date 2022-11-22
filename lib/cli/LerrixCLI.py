from concurrent.futures import ThreadPoolExecutor
import sys
import os
import time
import threading
import json
from lib.download.Downloader import Downloader
from lib.scrape.MultiDirScraper import MultiDirScraper
from lib.unsilence.Unsilencer import Unsilencer

from lib.utils.DataKeeper import DataKeeper

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from lib.download.SP_Downloader import SP_Downloader
from lib.utils.PrintUtils import PrintUtils
from lib.scrape.DirScraper import DirScraper

class LerrixCLI:
    DEFAULT_CONFIG_FILE_LOCATION = os.path.join(os.path.dirname(os.path.dirname(__file__)), "lerrix_config.json")
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

    
    def run(self):
        # scrape using multiple accounts, getting manifests
        # download using multiple sources
        # unsilence
        for sp_dir in self.config["sp_dirs"]:
            if sp_dir["ignore-item"]:
                print("Ignoring item: " + sp_dir["local_dir"])
                continue
            print("Scraping directory: " + sp_dir["local_dir"])
            multidir_scraper = MultiDirScraper(sp_dir["url"], self.accounts)
            multidir_scraper.load()
            print(f"Scraping done in {multidir_scraper.directory_content['total_time_to_load']}")

            downloader = Downloader(
                tmp_directory = self.config["tmp_directory"],
                chunk_length = self.config["download_chunk_length"],
                chunk_threads = self.config["download_chunk_threads"],
            )
            for video in multidir_scraper.directory_content["videos"]:
                thread = threading.Thread(target=downloader.download, args=(video["manifests"], sp_dir["local_dir"]))
                thread.start()
                try:
                    while thread.is_alive():
                        status = downloader.pretty_status()
                        print(status)
                        time.sleep(0.5)
                        PrintUtils.clear_line(status.count("\n")+1)
                except KeyboardInterrupt:
                    downloader.interrupt = True
                    print("Download stopped")
            unsilencer = Unsilencer(self.config["tmp_directory"])

            for input in os.listdir(sp_dir["local_dir"]):
                input_filename = os.path.basename(input)
                output = os.path.join(self.config["unsilenced_videos_dir"], sp_dir["local_dir"], input_filename)
                
                thread = threading.Thread(target=unsilencer.unsilence, args=(input, output))
                thread.start()
                try:
                    while thread.is_alive():
                        status = unsilencer.pretty_status()
                        print(status)
                        time.sleep(0.5)
                        PrintUtils.clear_line(status.count("\n")+1)
                except KeyboardInterrupt:
                    downloader.interrupt = True
                    print("Download stopped")

    def init_local_dirs(self):
        dirs_to_create = [
            self.config["data_directory"],
            self.config["tmp_directory"],
            self.config["log_directory"],
            self.config["unsilenced_videos_dir"],
            self.config["videos_dir"],
            self.config["accounts_dir"],
            self.config["unsilenced_videos_dir"],
            self.config["cookies"]
        ]
        for d in dirs_to_create:
            if not os.path.exists(d):
                print("Creating directory: " + d)
                os.makedirs(d)

        for sp_dir in self.config["sp_dirs"]:
            if sp_dir["ignore-item"]:
                print("Ignoring item: " + sp_dir["local_dir"])
                continue
            dirs_to_create = [
                os.path.join(self.videos_dir, sp_dir["local_dir"]),
                os.path.join(self.unsilenced_videos_dir, sp_dir["local_dir"])
            ]
            for d in dirs_to_create:
                if not os.path.exists(d):
                    print("Creating directory: " + d)
                    os.makedirs(d)
    
    def init_accounts_and_cookies(self):
        accounts = []
        account_files = os.listdir(self.accounts_dir)
        if len(account_files) == 0:
            print("No accounts found in accounts directory, please add accounts to the directory")
            exit(0)
        for account_file in account_files:
            dkeeper = DataKeeper(account_file, self.ENC_KEY)
            psw = dkeeper.load()
            if psw is None:
                print("No password found for account: " + account_file)
                continue
            accounts.append({"username": account_file, "password": psw})

        for cookie_file in os.listdir(self.cookies_dir):
            if cookie_file not in account_files:
                print("Cookie file found without account: " + cookie_file)
                accounts.append({"username": None, "password": None, "cookie_file": cookie_file})
            for account in accounts:
                if account["username"] == cookie_file:
                    account["cookie_file"] = cookie_file
        
        return accounts

    def init_config(self):
        if not os.path.exists(self.config_file_location):
            config = {}
            config["data_directory"] = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
            config["tmp_directory"] = os.path.join(config["data_directory"], "tmp")
            config["log_directory"] = os.path.join(config["data_directory"], "logs")
            config["unsilenced_videos_dir"] = os.path.join(config["data_directory"], "unsilenced_videos")
            config["videos_dir"] = os.path.join(config["data_directory"], "videos")
            config["accounts_dir"] = os.path.join(config["data_directory"], "accounts")
            config["cookies"] = os.path.join(config["data_directory"], "cookies")
            config["sp_dirs"] = [{"local_dir": "Local name directory", "url": "Sharepoint url directory", "file_prefix": "PREFIX ", "ignore-item" : "true"}]
            config["scraping_threads"] = 1
            config["download_chunk_threads"] = 1
            config["download_chunk_length"] = 600
            with open(self.config_file_location, "w") as f:
                f.write(json.dumps(config, indent=4))
            return None
        else:
            with open(self.config_file_location, "r") as f:
                return json.load(f)
        