from seleniumwire import webdriver
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException        

import time
import pickle
import os

class SP_Scraper:
    args = ["--mute-audio"] #["--mute-audio", "--headless"] # TODO HEADLESS CASH
    implicit_wait = 15
    timeout = 15

    def __init__(self, username=None, password=None, cookies=None, cookies_file="cookies.pkl"):
        self.username = username
        self.password = password
        self.cookies = cookies
        self.cookies_file = cookies_file
        self.driver = None
        if cookies is None:
            if self.cookies_file is not None and os.path.exists(self.cookies_file):
                print(f"Loading cookies: {self.cookies_file}. If they are valid they'll be used to login instead of using username and password")
                with open(self.cookies_file, 'rb') as f:
                    self.cookies = pickle.load(f)
            else:
                if (self.username is None or self.password is None):
                    raise ValueError("Username or password is not provided, and cookies not found") # TODO CORRECT EXCEPTION?

    def _driver(self):
        chrome_opt = webdriver.ChromeOptions()
        for arg in SP_Scraper.args:
            chrome_opt.add_argument(arg)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_opt)
        if self.cookies is not None: # I'm preloading cookies (not yet in the correct domain)
            driver.execute_cdp_cmd('Network.enable', {})
            for cookie in self.cookies:
                driver.execute_cdp_cmd('Network.setCookie', cookie)
            driver.execute_cdp_cmd('Network.disable', {})
        driver.implicitly_wait(SP_Scraper.implicit_wait) 
        return driver
    
    def driver_quit(self):
        if self.driver is not None:
            self.driver.quit()

    def get_request(self, url):
        if self.driver is None:
            self.driver = self._driver()
        self.driver.get(url)
        self._login_if_needed()

    def _login_if_needed(self):
        if self._is_login_page():
            print("Logging is needed")
            if self.cookies is not None:
                print("Cookies are not valid anymore, need to login with credentials again")

            if self.username is not None and self.password is not None:
                usr = self.driver.find_element("id", "i0116")
                usr.send_keys(self.username)
                self.click_btn_by("idSIButton9")
                time.sleep(1)
                pwd = self.driver.find_element("id", "i0118")
                pwd.send_keys(self.password)
                time.sleep(1)
                self.click_btn_by("idSIButton9")
                self.click_btn_by("idBtn_Back")
                time.sleep(1)
                self.cookies = self.driver.get_cookies()
                self.cookies_to_file()
                print(f"Logged in with username {self.username}")
            else:
                raise ValueError("Username or password is not provided, and cookies are not valid")

    def _is_login_page(self): # check if present div with class login-paginated-page
        try:
            self.driver.implicitly_wait(2) 
            self.driver.find_element("xpath", "//div[@class='login-paginated-page']//input[@id='i0116']")
            self.driver.implicitly_wait(SP_Scraper.implicit_wait) 
        except NoSuchElementException:
            return False
        return True

    def cookies_to_file(self):
        with open(self.cookies_file, 'wb') as f:
            pickle.dump(self.cookies, f)

    def click_btn_by(self, id, before_wait=0.5, by=By.ID):
        time.sleep(before_wait)
        try:
            btn = WebDriverWait(self.driver, SP_Scraper.timeout).until(EC.element_to_be_clickable((by, id)))
            btn.click()
        except StaleElementReferenceException:
            btn = WebDriverWait(self.driver, SP_Scraper.timeout).until(EC.element_to_be_clickable((by, id)))
            btn.click()