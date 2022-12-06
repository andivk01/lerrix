import time
import pickle
import os
from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

class SP_Scraper:
    USERNAME_FIELD_XPATH = "//div[@class='login-paginated-page']//input[@id='i0116']"
    PASSWORD_FIELD_XPATH = "//div[@class='login-paginated-page']//input[@id='i0118']"
    LOGIN_URL = "login.microsoftonline.com"

    def __init__(self, username=None, password=None, cookies=None,
                cookies_file=None, implicit_wait=15, timeout=15, args=["--mute-audio"], driver=None):
        
        if cookies is not None and cookies_file is not None:
            raise ValueError("Cookies and cookies_file are mutually exclusive")
        self.username = username
        self.password = password
        self.cookies = cookies
        self.cookies_file = cookies_file
        self.implicit_wait = implicit_wait
        self.timeout = timeout
        self.args = args
        self.driver = driver

        if cookies is None:
            if self.cookies_file is not None and os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'rb') as f:
                    self.cookies = pickle.load(f)
            elif self.username is None or self.password is None:
                raise ValueError("Username or password is not provided, and cookies not found")
    
    def new_driver(self):
        chrome_opt = webdriver.ChromeOptions()
        chrome_opt.add_experimental_option("excludeSwitches", ["enable-logging"]) # removes bluetooth error
        for arg in self.args:
            chrome_opt.add_argument(arg)
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_opt)
        if self.cookies is not None: # I'm preloading cookies (not yet in the correct domain)
            driver.execute_cdp_cmd('Network.enable', {})
            for cookie in self.cookies:
                driver.execute_cdp_cmd('Network.setCookie', cookie)
            driver.execute_cdp_cmd('Network.disable', {})
        driver.implicitly_wait(self.implicit_wait) 
        return driver

    def driver_quit(self):
        if self.driver is not None:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass
    
    def is_on_login_page(self):
        return SP_Scraper.LOGIN_URL in self.driver.current_url
    
    def goto_page(self, url):
        if self.driver is None:
            self.driver = self.new_driver()
            
        self.driver.get(url)
        if self.is_on_login_page():
            self.login()
            if not self.is_on_login_page() and self.driver.current_url != url:
                self.driver.get(url)

    def login(self):
        if not self.is_on_login_page():
            return
        if self.cookies_file is not None and os.path.exists(self.cookies_file):
            os.remove(self.cookies_file)
        if self.username is None or self.password is None:
            raise ValueError("Username or password is not provided and cookies are not valid.")

        try:
            self._func_when_ready(By.XPATH, SP_Scraper.USERNAME_FIELD_XPATH, "send_keys", func_params=(self.username))
            self._func_when_ready(By.ID, "idSIButton9", "click")
        except Exception as e: # TODO only log
            print("Exception: ", e)
        try:
            self._func_when_ready(By.XPATH, SP_Scraper.PASSWORD_FIELD_XPATH, "click")
            self._func_when_ready(By.XPATH, SP_Scraper.PASSWORD_FIELD_XPATH, "send_keys", func_params=(self.password))
            self._func_when_ready(By.ID, "idSIButton9", "click")
            self._func_when_ready(By.ID, "idBtn_Back", "click")
        except Exception as e: # TODO only log
            print("Exception: ", e)

        if self.is_on_login_page():
            raise ValueError("Login failed")

        self.cookies = self.driver.get_cookies()
        if self.cookies_file is not None:
            with open(self.cookies_file, 'wb') as f:
                pickle.dump(self.cookies, f)

    def _get_manifests(self):
        return [request.url for request in self.driver.requests if "videomanifest" in request.url]

    def _func_when_ready(self, by, elem_id, func_name, func_params=None, timeout=3, wait_retry=0.5, wait_bef_trying=1):
        time.sleep(wait_bef_trying)
        start = time.time()
        while time.time() - start < timeout:
            elem = self.driver.find_element(by, elem_id)
            if not elem.is_enabled():
                time.sleep(wait_retry)
                continue
            try:
                func = getattr(elem, func_name)
                if func_params is None:
                    func()
                else:
                    func(func_params)
                return
            except Exception:
                time.sleep(wait_retry)
        return False # TODO raise exception?