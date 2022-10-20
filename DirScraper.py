from SP_Scraper import SP_Scraper
from Video import Video
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import time
import json

class DirScraper(SP_Scraper):

    def __init__(self, dir_url, username=None, password=None, cookies=None, log_file=None):
        super().__init__(username, password, cookies)
        self.dir_url = dir_url
        self.log_file = log_file
        self.videos = []

    def load(self, titles_to_ignore_file=None):
        start_time = time.time()
        self.get_request(self.dir_url)
        
        time.sleep(3)
        WebDriverWait(self.driver, self.timeout).until(EC.element_to_be_clickable((By.XPATH, "//div[@role='presentation']//button[@role='link']")))
        link_btns = self.driver.find_elements("xpath", "//div[@role='presentation']//button[@role='link']")

        video_titles = []
        titles_to_ignore = []
        if titles_to_ignore_file is not None:
            with open(titles_to_ignore_file) as file:
                titles_to_ignore = file.read().splitlines()
        
        video_ignored_count = 0
        for link_btn in link_btns:
            if Video.formatted_name(link_btn.text) in titles_to_ignore:
                video_ignored_count += 1
                continue
            video_titles.append(link_btn.text)
            link_btn.click()
            time.sleep(5) # wait for getting manifest
            self.click_btn_by(id="//button[@role='menuitem']//i[@data-icon-name='Cancel']", by=By.XPATH)
        if video_ignored_count > 0:
            print(f"Number of videos ignored from scraping: {video_ignored_count}")
        manifests = [request.url for request in self.driver.requests if "videomanifest" in request.url]
        self.videos = [Video(original_name, location=manifest) for original_name, manifest in zip(video_titles, manifests)]
        if self.log_file is not None:
            with open(self.log_file, "w") as f:
                f.write(json.dumps([video.to_dict() for video in self.videos]))
        return time.time() - start_time
