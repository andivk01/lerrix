from concurrent.futures import ThreadPoolExecutor
from datetime import time
from lib.scrape.DirScraper import DirScraper


class MultiDirScraper():
    def __init__(self, dir_url, accounts, scraping_threads=1): # TODO videos_ignored, ignore_func ecc...
        self.dir_scrapers = [DirScraper(dir_url, account["username"], account["password"], cookies_file=account["cookie_file"]) for account in self.accounts]
        self.directory_content = {"dir_url": dir_url, "accounts": accounts, "videos": []} # TODO videos_ignored, ignore_func ecc...
    
    def load(self):
        self.directory_content["load_start_time"] = time.time()
        with ThreadPoolExecutor(max_workers=self.SCRAPE_THREADS) as executor:
            for scraper in self.dir_scrapers:
                executor.submit(scraper.load, True)

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