import requests

from utils.interrupt import interrupt
from utils.log import log
from utils.tool import iswindows

Session = requests.Session()
Session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=100))
Session.mount('http://', requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=100))


class Reqmini():
    def __init__(self, proxies=None):
        if proxies:
            proxyinfo = {
                "http": "http://" + proxies,
                "https": "https://" + proxies
            }
            self.proxies = proxyinfo
        else:
            self.proxies = proxies

    def get(self, url, headers=None, cookies=None, timeout=30):
        headers = {
            "User-Agent": "Mozilla/5.0 (iPad; CPU OS 11_0 like Mac OS X) AppleWebKit/604.1.34 (KHTML, like Gecko) Version/11.0 Mobile/15A5341f Safari/604.1"
        }
        if headers:
            Session.headers.update(headers)
        if cookies:
            Session.cookies.update(cookies)
        if self.proxies:
            Session.proxies.update(self.proxies)
        try:
            response = Session.get(url, timeout=timeout)
            return response
        except BaseException as e:
            log("error", e)

    def download(self, para):
        urls = para[0]
        files = para[1]
        try:
            r = self.get(urls)
            with open(files, "wb") as code:
                for chunk in r.iter_content(chunk_size=1024):
                    code.write(chunk)
        except BaseException:
            self.__retry(urls, files)

    def __retry(self, urls, files):
        try:
            log("info", "Retrying...", "")
            r = self.get(urls)
            with open(files, "wb") as code:
                for chunk in r.iter_content(chunk_size=1024):
                    code.write(chunk)
        except BaseException:
            msg = "{} is failed.".format(urls[0])
            if iswindows():
                interrupt("windows", msg)
            else:
                interrupt("linux", msg)
