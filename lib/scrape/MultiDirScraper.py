from concurrent.futures import ThreadPoolExecutor
import time
from lib.scrape.DirScraper import DirScraper
from lib.utils.SPUtils import handle_exc


class MultiDirScraper():
    def __init__(self, dir_url, accounts, scraping_threads=1):
        self.dir_url = dir_url
        self.accounts = accounts
        self.scraping_threads = scraping_threads
        self.dir_scrapers = [DirScraper(dir_url, account["username"], account["password"], cookies_file=account["cookie_file"]) for account in self.accounts]
        self.directory_content = {"dir_url": dir_url, "accounts": accounts, "videos": []} # TODO videos_ignored
    
    def load(self, ignore_func_btn=None, then_quit=False):
        self.directory_content["load_start_time"] = time.time()
        with ThreadPoolExecutor(max_workers=self.scraping_threads) as executor:
            for scraper in self.dir_scrapers:
                load_func = handle_exc()(scraper.load)
                executor.submit(load_func, ignore_func_btn, then_quit)

        for scraper in self.dir_scrapers:
            for scraped_video in scraper.directory_content["videos"]:
                multidirscraped_video = self._video_by_filename(scraped_video["filename"])
                if multidirscraped_video:
                    multidirscraped_video["manifests"].append(scraped_video["manifest"])
                else:
                    self.directory_content["videos"].append({"filename": scraped_video["filename"], "manifests": [scraped_video["manifest"]]})
            scraper.driver_quit()

        self.directory_content["load_end_time"] = time.time()
        self.directory_content["total_time_to_load"] = self.directory_content["load_end_time"] - self.directory_content["load_start_time"]
        
    def _video_by_filename(self, filename):
        for video in self.directory_content["videos"]:
            if video["filename"] == filename:
                return video
        return False