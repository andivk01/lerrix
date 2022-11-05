import time
from selenium.webdriver.common.by import By
from lib.scrape.SP_Scraper import SP_Scraper

class VideoScraper(SP_Scraper):
    CANCEL_VIDEOWATCH_BTN_XPATH = "//button[@role='menuitem']//i[@data-icon-name='Cancel']"
    
    def __init__(self, video_url, username=None, password=None, cookies=None, cookies_file=None):
        super().__init__(username, password, cookies, cookies_file)
        self.video_url = video_url
        self.video_content = {
            "video_url": video_url
        }
        if username is not None:
            self.video_content["username"] = username
        if cookies is not None:
            self.video_content["cookies"] = cookies

    def load(self, quit_after=True):
        self.goto_page(self.video_content["video_url"])
        manifest_count = len(self._get_manifests())
        time_before_waiting = time.time()
        while(time.time()-time_before_waiting < self.timeout): # wait for getting manifest
            if len(self._get_manifests()) != manifest_count:
                break
            time.sleep(0.5)
        self.driver._func_when_ready(By.XPATH, VideoScraper.CANCEL_VIDEOWATCH_BTN_XPATH, "click")
        self.video_content["manifest"] = self._get_manifests()[-1] 
        if quit_after:
            self.driver_quit()
        return self.video_content["manifest"]