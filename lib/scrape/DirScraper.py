import time
import random
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from lib.scrape.SP_Scraper import SP_Scraper

class DirScraper(SP_Scraper):
    LINK_BTN_XPATH = "//div[@role='presentation']//button[@role='link']"
    CANCEL_VIDEOWATCH_BTN_XPATH = "//button[@role='menuitem']//i[@data-icon-name='Cancel']"

    def __init__(self, dir_url, username=None, password=None, cookies=None, cookies_file=None):
        super().__init__(username, password, cookies, cookies_file)
        self.dir_url = dir_url
        self.directory_content = {"dir_url": dir_url}
        self.directory_content["videos"] = []
        if username is not None:
            self.directory_content["username"] = username
        if cookies is not None:
            self.directory_content["cookies"] = cookies

    def load(self, ignore_func_btn=None, then_quit=False):
        self.directory_content["load_start_time"] = time.time()
        self.goto_page(self.dir_url)
        time.sleep(2) # TODO find a better way to wait for the page to load
        WebDriverWait(self.driver, self.timeout).until(EC.element_to_be_clickable((By.XPATH, DirScraper.LINK_BTN_XPATH)))
        link_btns = self.driver.find_elements(By.XPATH, DirScraper.LINK_BTN_XPATH)
        
        video_filenames = []
        video_manifests = []
        video_ignored_count = 0
        video_ignored_filenames = []
        for link_btn in link_btns:
            if ignore_func_btn is not None and ignore_func_btn(link_btn):
                video_ignored_count += 1
                video_ignored_filenames.append(link_btn.text)
                continue
            # if "20221115" not in link_btn.text: # TODO
            #     continue
            WebDriverWait(self.driver, self.timeout).until(EC.element_to_be_clickable(link_btn))
            link_btn.click()
            time_before_waiting = time.time()
            manifest_count = len(self._get_manifests())
            while(time.time()-time_before_waiting < self.timeout): # wait for getting manifest
                if len(self._get_manifests()) != manifest_count:
                    break
                time.sleep(0.5)

            time.sleep(random.randint(5, 15)) # TODO

            manifests_found = self._get_manifests()
            if len(video_filenames) == len(manifests_found):
                print(f"WARNING: Cannot retrieve manifest for {link_btn.text}")
                print(f"Ignoring {link_btn.text}...")
                video_ignored_count += 1
                video_ignored_filenames.append(link_btn.text)
            else:
                video_filenames.append(link_btn.text)
                video_manifests.append(manifests_found[-1])
                
            self._func_when_ready(By.XPATH, DirScraper.CANCEL_VIDEOWATCH_BTN_XPATH, "click")
        self.directory_content["load_end_time"] = time.time()
        self.directory_content["total_time_to_load"] = self.directory_content["load_end_time"] - self.directory_content["load_start_time"]
        self.directory_content["videos"] = [{"filename": filename, "manifest": manifest} for filename, manifest in zip(video_filenames, video_manifests)]
        self.directory_content["video_ignored_filenames"] = video_ignored_filenames
        if then_quit:
            self.driver_quit()