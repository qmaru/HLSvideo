# -*- coding: UTF-8 -*-
# @author AoBeom
# @create date 2017-12-27 18:00:45
# @modify date 2019-06-19 14:25:19
# @desc [STchannel Video Download]
import datetime
import json
import logging
import os
import platform
import re
import shutil
import sys
import time
from multiprocessing.dummy import Pool

import requests
from Crypto.Cipher import AES

SESSION = requests.Session()
WORKDIR = os.path.dirname(os.path.realpath(sys.argv[0]))
DATENAME = time.strftime('%y%m%d%H%M%S', time.localtime(time.time()))
TOKEN_FILE = os.path.join(WORKDIR, ".token.json")


def log(mode, *para):
    logging.basicConfig(
        level=logging.NOTSET, format='%(asctime)s - %(filename)s [%(levelname)s] %(message)s')
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    log = getattr(logging, mode)
    para = [str(i) for i in para]
    msg = " - ".join(para)
    log(msg)


def execute_time(func):
    def wrapper():
        start = time.time()
        func()
        end = time.time()
        log("info", "Execute: {}s".format(str(int(end - start))))
    return wrapper


def get_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            data = json.loads(f.read())
        token = data.get("token")
        return token
    return None


def set_token(token):
    data = {"token": token}
    with open(TOKEN_FILE, "w") as f:
        f.write(json.dumps(data))


class STchannelAPI():
    def __init__(self):
        self.user_api = "https://st-api.st-channel.jp/v1/users"
        self.movie_api = "https://st-api.st-channel.jp/v1/movies?"
        self.headers = {
            "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 7.1.1; E6533 Build/32.4.A.0.160)",
            "Content-Type": "application/json; charset=UTF-8"
        }

    def __dformat(self, date):
        dateformat = datetime.datetime.strptime(
            date, '%Y-%m-%dT%H:%M:%S+09:00')
        dateformat = str(dateformat)
        darray = time.strptime(dateformat, "%Y-%m-%d %H:%M:%S")
        dformats = time.strftime("%Y-%m-%d %H:%M:%S", darray)
        return dformats

    def auth_token(self):
        log("info", "[01] Get token...")
        if get_token():
            return get_token()
        else:
            userInfo = SESSION.post(self.user_api, headers=self.headers, timeout=30).text
            token = json.loads(userInfo)["api_token"]
            set_token(token)
            return token

    def get_info(self):
        token = self.auth_token()
        log("info", "[02] Token: {}".format(token))
        header_auth = self.headers.copy()
        header_auth["authorization"] = "Bearer " + token
        api_param = {
            "since_id": 0,
            "device_type": 2,
            "since_order": 0,
            "sort": "order"
        }
        log("info", "[03] Get movie information with API...")
        response = SESSION.get(
            self.movie_api, headers=header_auth, params=api_param, timeout=30)
        code = response.status_code
        while code != 200:
            log("info", "Token Refresh...")
            token = self.get_token()
            header_auth["Authorization"] = "Bearer " + token
            response = SESSION.get(
                self.movie_api, headers=header_auth, params=api_param, timeout=30)
            code = response.status_code
        movie_info = json.loads(response.text)
        return movie_info

    def get_movie_url(self, movie_info):
        st_info = []
        for index, value in enumerate(movie_info["movies"]):
            st_new = {}
            st_title = value["title"].strip()
            st_movie = requests.utils.unquote(value["movie_url_everyone"]).replace(
                "ulizasekailab", "https").replace("videoquery=", "")
            st_thumbnail = value["thumbnail_path"]
            st_date = self.__dformat(value["publish_start_date"])
            st_new["index"] = str(index + 1)
            st_new["title"] = st_title
            st_new["movie_url"] = st_movie
            st_new["picture_url"] = st_thumbnail
            st_new["date"] = st_date
            st_info.append(st_new)
        return st_info


class HLSdownload():
    def __init__(self):
        self.headers = {
            "User-Agent": "UlizaPlayer_Android/2.5.2 (Android/7.1.1; E6533; Build/32.4.A.0.160; Radio/8994-FAAAANAZQ-00028-36)"
        }

    def get_response(self, url):
        return SESSION.get(url, headers=self.headers)

    def get_content(self, url):
        return SESSION.get(url, headers=self.headers).text

    def get_binary(self, url):
        return SESSION.get(url, headers=self.headers).content

    def create_folder(self, name):
        unique_name = "{}_{}".format(DATENAME, name)
        save_path = os.path.join(WORKDIR, unique_name)
        if os.path.exists(save_path):
            return save_path
        os.mkdir(save_path)
        return save_path

    def decrypt_media(self, data, key, iv):
        cryptor = AES.new(key, AES.MODE_CBC, iv)
        data_dec = cryptor.decrypt(data)
        return data_dec

    def get_best_info(self, playlist):
        log("info", "[04] Get best URL from playlist: {}".format(playlist))
        playlist_content = self.get_content(playlist)
        rule_m3u8 = r"^[\w\-\.\/\:\?\&\=\%\,\+]+"
        m3u8_urls = re.findall(rule_m3u8, playlist_content, re.S | re.M)
        m3u8_best_url = ''.join(m3u8_urls)
        log("info", "[05] Get m3u8 content from best URL: {}".format(m3u8_best_url))
        m3u8_content = self.get_content(m3u8_best_url)

        parts = m3u8_best_url.split("/")
        video_host = "http://" + parts[2] + "/" + parts[3] + "/"

        rule_video = r'[^#\S+][\w\/\-\.\:\?\&\=]+'
        video_uris = re.findall(rule_video, m3u8_content, re.S | re.M)
        video_urls = [video_host + i.strip() for i in video_uris]
        log("info", "[06] A video URL: {}".format(video_urls[0]))

        rule_key = r'URI=\"(.*?)\"'
        keyurl = re.findall(rule_key, m3u8_content)
        key_url = ''.join(keyurl)
        log("info", "[07] Key URL: {}".format(key_url))
        key = self.get_binary(key_url)

        key_video = {
            "key": key,
            "urls": video_urls
        }
        return key_video

    def __download(self, para):
        url = para[0]
        key = para[1]
        iv = para[2]
        files = para[3]
        res = self.get_response(url)
        with open(files, "wb") as code:
            data = self.decrypt_media(res.content, key, iv)
            code.write(data)

    def __concat(self, save_path):
        log("info", "[09] Merge video...")
        videos = [os.path.join(save_path, v) for v in os.listdir(save_path)]
        output_video = os.path.join(WORKDIR, "{}.ts".format(DATENAME))
        if "Windows" in platform.system():
            input_video = "+".join(videos)
            cmd = "copy /B {} {} >nul 2>nul".format(input_video, output_video)
        else:
            input_video = " ".join(videos)
            cmd = "cat {} > {}".format(input_video, output_video)
        os.system(cmd)

        os.chmod(save_path, 128)
        shutil.rmtree(save_path)
        log("info", "[10] Finished. Check {}.ts".format(DATENAME))

    def run(self, key_video):
        log("info", "[08] Downloading... & Decrypting...")
        key = key_video["key"]
        urls = key_video["urls"]
        total = len(urls)
        keys = [key] * total
        ivs = [bytes.fromhex('%032x' % i) for i in range(0, total)]
        save_path = self.create_folder("videos")
        files = [os.path.join(save_path, str(i).zfill(4) + ".ts") for i in range(0, total)]

        pool = Pool(4)
        pool.map(self.__download, list(zip(urls, keys, ivs, files)))
        pool.close()
        pool.join()

        self.__concat(save_path)


def main():
    api = STchannelAPI()
    hls = HLSdownload()
    movie_info = api.get_info()
    movie_urls = api.get_movie_url(movie_info)
    for movie in movie_urls:
        url = movie["movie_url"]
        key_video = hls.get_best_info(url)
        hls.run(key_video)


if __name__ == '__main__':
    main()
