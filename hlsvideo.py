# -*- coding: UTF-8 -*-
# @author AoBeom
# @create date 2017-12-25 04:49:59
# @modify date 2019-06-06 16:02:31
# @desc [HLS downloader]
import argparse
import os
import platform
import re
import time

from Crypto.Cipher import AES

from utils import tool
from utils.concat import concat
from utils.interrupt import interrupt
from utils.log import log
from utils.reqmini import Reqmini
from utils.threadbar import threadProcBar

DATENAME = time.strftime('%y%m%d%H%M%S', time.localtime(time.time()))
WORKDIR = os.path.dirname(os.path.abspath(__file__))


class HLSVideo():
    def __init__(self, debug, proxies):
        self.debug = debug
        self.keyparts = 1

        if proxies:
            self.reqmini = Reqmini(proxies)
        else:
            self.reqmini = Reqmini()

    def get_content(self, url):
        res = self.reqmini.get(url)
        content = res.text
        return content

    def get_best_video_url(self):
        self.playlist_content = self.get_content(self.playlist)
        # 提取m3u8列表的最高分辨率的文件
        rule_m3u8 = r"^[\w\-\.\/\:\?\&\=\%\,\+]+"
        rule_bd = r"BANDWIDTH=([\w]+)"
        rule_bd_gyao = r"EXT-X-STREAM-INF:PROGRAM-ID=1,BANDWIDTH=([\w]+)"
        # 根据码率匹配
        if "m3u8" in self.playlist_content:
            m3u8urls = re.findall(rule_m3u8, self.playlist_content, re.S | re.M)
            bandwidth = re.findall(rule_bd, self.playlist_content, re.S | re.M)
            # GYAO 特殊处理 12为估算值
            if len(bandwidth) > 12:
                bandwidth = re.findall(rule_bd_gyao, self.playlist_content, re.S | re.M)
            bandwidth = [int(b) for b in bandwidth]
            group = zip(m3u8urls, bandwidth)
            maxband = max(group, key=lambda x: x[1])
            m3u8best = maxband[0]
            if self.debug:
                log("debug", "m3u8url", m3u8best)
            return m3u8best
        elif "EXT-X-ENDLIST" in self.playlist_content:
            return self.playlist
        else:
            msg = "URL_ERROR: {}".format(self.playlist)
            if tool.iswindows():
                interrupt("windows", msg)
            else:
                interrupt("linux", msg)

    def get_best_audio_url(self):
        audio_m3u8_rule = r'TYPE=AUDIO.*?URI=\"(.*?)\"'
        audio_m3u8_url = re.findall(audio_m3u8_rule, self.playlist_content, re.S | re.M)
        return audio_m3u8_url[-1]

    def set_m3u8_host(self, m3u8best):
        if self.type in ["GYAO"]:
            m3u8host = "https://" + self.playlist.split("/")[2] + "/"
        elif self.type in ["ABEMA", "Yahoo"]:
            uri = [_ for _ in self.playlist.split("/")[1:-1] if _]
            m3u8host = "https://" + "/".join(uri) + "/"
        else:
            m3u8host = tool.check_host("m3u8 host", m3u8best)
        return m3u8host

    def set_media_host(self, m3u8best=None, audio=False):
        rule = r'[^#\S+][~\w\/\-\.\:\?\&\=\,\+\%]+'
        if audio:
            media_url = re.findall(rule, self.m3u8_audio_bestmatch, re.S | re.M)
        else:
            media_url = re.findall(rule, self.m3u8_bestmatch, re.S | re.M)

        if self.type in ["GYAO"]:
            media_host = "https://" + self.playlist.split("/")[2] + "/"
        elif self.type in ["Asahi", "STchannel", "FOD"]:
            uri = [_ for _ in m3u8best.split("/")[1:-1] if _]
            media_host = "https://" + "/".join(uri) + "/"
        else:
            media_host = tool.check_host("video host", media_url[0].strip())
        media_urls = [media_host + v.strip() for v in media_url]
        return media_host, media_urls

    def get_iv(self):
        if self.type in ["ABEMA", "TVer"]:
            rule_iv = r'IV=0x([\w]+)'
            iv_value = re.findall(rule_iv, self.m3u8_bestmatch)
            return "".join(iv_value)
        else:
            return None

    def get_keyurls(self, audio=False):
        rule_key = r'URI=\"(.*?)\"'
        if audio:
            keyurls = re.findall(rule_key, self.m3u8_audio_bestmatch)
        else:
            keyurls = re.findall(rule_key, self.m3u8_bestmatch)
        if self.type == "Yahoo":
            uri_part = self.playlist.split("/")
            keyurls = [uri_part[0] + "//" + uri_part[2] + keyurls[0]]
            return keyurls
        keyurls = [self.set_m3u8_host(m3u8best=i) + i for i in keyurls]
        return keyurls

    def get_keystr(self, keyurls, keytype):
        keylist = []
        if keyurls:
            # tv-asahi 根据 key 的数量分片
            if "tv-asahi" in self.m3u8_bestmatch:
                if len(keyurls) > 1:
                    key_parts = keyurls[1].split("/")[-1].split("=")[-1]
                    self.keyparts = int(key_parts)
                    if self.debug:
                        log("debug", "videoparts", self.keyparts)
            key_num = len(keyurls)
            log("info", "(1)GET {} Key".format(keytype), key_num)
            key_dict = {}
            for key_index, key_url in enumerate(keyurls):
                keyname = str(key_index + 1).zfill(4)
                key_binary = self.reqmini.get(key_url).content
                if self.debug:
                    log("debug", "keyinfo", key_binary)
                key_dict[keyname] = key_binary
            keylist.append(key_dict)
            return keylist
        else:
            return keylist

    def set_save_folder(self, data, folder_name):
        save_path = []
        media_folder = tool.create_folder(WORKDIR, DATENAME, folder_name)
        if self.debug:
            log("debug", "encfolder", media_folder)
        # Rename the video for sorting
        for i in range(0, len(data)):
            media_num = i + 1
            media_name = str(media_num).zfill(4) + ".ts"
            media_path = os.path.join(media_folder, media_name)
            save_path.append(media_path)
        return media_folder, save_path

    # 识别HLS的类型
    def hlsAnalyze(self, playlist):
        type_dict = {
            "GYAO": "gyao",
            "TVer": "manifest.prod.boltdns.net",
            "Asahi": "tv-asahi",
            "STchannel": "www2.uliza.jp",
            "FOD": "i.fod.fujitv.co.jp",
            "MBS": "secure.brightcove.com",
            "ABEMA": "vod-abematv",
            "Yahoo": "gw-yvpub.c.yimg.jp"
        }
        # 通过关键字判断HLS的类型
        siteRule = r'http[s]?://[\S]+'
        check_url = re.search(siteRule, playlist)
        if check_url:
            for site, keyword in type_dict.items():
                if keyword in playlist:
                    video_type = site
                    break
                type_check = self.reqmini.get(playlist).text
                if keyword in type_check:
                    video_type = site
                    break
            else:
                video_type = None
            if video_type == "TVer":
                tool.ffmpeg_check()
            if video_type in ["GYAO", "MBS"]:
                self.keyparts = 10
            if video_type == "ABEMA":
                spec_info = """Please debug: source -> theoplayer.d.js -> var t = e.data\r\nConsole: Array.from(e.data.N8, function(byte){return ('0' + (byte & 0xFF).toString(16)).slice(-2);}).join('')"""
                print(spec_info)
            self.type = video_type
            self.playlist = playlist
            log("info", "Media Type: {}".format(video_type))
            if self.debug:
                log("debug", video_type, playlist)
            return playlist, video_type
        else:
            msg = "URL Invalid"
            if tool.iswindows():
                interrupt("windows", msg)
            else:
                interrupt("linux", msg)

    # 根据类型做不同的处理 下载key并提取video列表
    def hlsInfo(self):
        key_video = {}

        # 获取 m3u8 播放列表最佳分辨率的地址
        m3u8best = self.get_best_video_url()

        # 设置 m3u8 的 host
        m3u8host = self.set_m3u8_host(m3u8best=m3u8best)
        if self.debug:
            log("debug", "m3u8host", m3u8host)

        m3u8_best_url = m3u8host + m3u8best
        self.m3u8_bestmatch = self.get_content(m3u8_best_url)

        # 设置 video 的 host 并获取视频列表
        videohost, videourls = self.set_media_host(m3u8best=m3u8best)
        if self.debug:
            log("debug", "videohost", videohost)

        if self.debug:
            log("debug", "videourls", videourls[0])

        self.iv = self.get_iv()
        if self.debug:
            log("debug", "videoiv", self.iv)
        video_keyurls = self.get_keyurls()
        if video_keyurls:
            self.unencrypt = False
        else:
            self.unencrypt = True

        if self.debug:
            if video_keyurls:
                log("debug", "video keyurl", video_keyurls[0])
            else:
                log("debug", "video keyurl", video_keyurls)

        if self.type == "ABEMA":
            keyfile = input("Enter Hex Key: ")
            log("info", "(1)Format Key", keyfile)
            videokeys = [
                {
                    "0001": bytes.fromhex(keyfile)
                }
            ]
        else:
            videokeys = self.get_keystr(video_keyurls, "video")

        # 获取 m3u8 播放列表最佳音频地址
        if self.type == "TVer":
            m3u8_best_audio_url = self.get_best_audio_url()
            self.m3u8_audio_bestmatch = self.get_content(m3u8_best_audio_url)
            audiohost, audiourls = self.set_media_host(audio=True)
            self.iv_audio = self.get_iv()
            audio_keyurls = self.get_keyurls(audio=True)
            audiokeys = self.get_keystr(audio_keyurls, "audio")
            if self.debug:
                log("debug", "audiohost", audiohost)
                log("debug", "audiourls", audiourls[0])
                log("debug", "audioiv", self.iv_audio)
        else:
            audiourls = None
            audiokeys = None

        key_video["vurls"] = videourls
        key_video["vkeys"] = videokeys
        key_video["aurls"] = audiourls
        key_video["akeys"] = audiokeys
        return key_video

    def set_download(self, media_prefix, media_save_path, urls, mediatype):
        total = len(urls)
        log("info", "(2)GET {}".format(mediatype), total)
        log("info", "--- Downloading ---")
        thread = int(total // 4)
        if thread > 100:
            thread = 20
        else:
            thread = 10
        t = threadProcBar(self.reqmini.download, list(zip(urls, media_save_path)), thread)
        t.worker()
        t.process()
        present = len(os.listdir(media_prefix))
        if present != total:
            log("error", "total_error", present + "/" + total)
            exit()

    # 下载函数
    def hlsDL(self, key_video):
        vurls = key_video["vurls"]
        vkeys = key_video["vkeys"]
        aurls = key_video["aurls"]
        akeys = key_video["akeys"]
        if aurls or akeys:
            # 音频保存路径列表
            audio_prefix, audios_save_path = self.set_save_folder(aurls, "encrypt_audio")
            self.set_download(audio_prefix, audios_save_path, aurls, "audio")
            if akeys:
                self.hlsDec(akeys, audios_save_path, "decrypt_audio")
            else:
                self.hlsConcat(audios_save_path, "encrypt_audio")

        # 视频保存路径列表
        video_prefix, videos_save_path = self.set_save_folder(vurls, "encrypt_video")
        self.set_download(video_prefix, videos_save_path, vurls, "video")

        # Check the number of keys
        key_num = len(vkeys)

        # 有key则调用解密函数
        if key_num != 0:
            log("info", "(3)Decrypting...")
            self.hlsDec(vkeys, videos_save_path, "decrypt_video")
        # 无key则直接合并视频
        else:
            log("info", "(3)Unencrypted...Merging...")
            self.hlsConcat(videos_save_path, "encrypt_video")

        self.data_check()

    def decrypt_media(self, data, key, iv):
        cryptor = AES.new(key, AES.MODE_CBC, iv)
        data_dec = cryptor.decrypt(data)
        return data_dec

    # 视频解密函数
    def hlsDec(self, keys, media, folder_prefix):
        key_num = len(keys)
        media_num = len(media)

        dec_media = []
        video_save_folder = tool.create_folder(WORKDIR, DATENAME, folder_prefix)
        # 只有一个 key
        if self.keyparts == 1:
            for i in range(0, key_num):
                keys = keys[i]
                for key_binary in keys.values():
                    indexs = range(0, media_num)
                    for index in indexs:
                        input_media = media[index]
                        if self.iv:
                            iv = bytes.fromhex(self.iv)
                        else:
                            iv = bytes.fromhex('%032x' % index)
                        if tool.iswindows():
                            output_media_name = media[index].split("\\")[-1] + "_dec.ts"
                        else:
                            output_media_name = media[index].split("/")[-1] + "_dec.ts"
                        output_media = os.path.join(video_save_folder, output_media_name)
                        dec_media.append(output_media)
                        with open(input_media, "rb") as vin, open(output_media, "wb") as vout:
                            output_dec = self.decrypt_media(vin.read(), key_binary, iv)
                            vout.write(output_dec)
            self.hlsConcat(dec_media, folder_prefix)
        # 多个 key
        else:
            if self.keyparts > 0:
                parts_s = int(self.keyparts)
            else:
                parts_s = int(round((media_num) / float(key_num)))
            output_media_part = []
            for key in range(0, key_num):
                for key_binary in keys.values():
                    index_s = key * parts_s
                    index_e = index_s + parts_s
                    indexs = range(index_s + 1, index_e + 1)
                    for index in indexs:
                        input_media = media[index]
                        if self.iv:
                            iv = bytes.fromhex(self.iv)
                        else:
                            iv = bytes.fromhex('%032x' % index)
                        if tool.iswindows():
                            tmp_output_media_name = "video_" + media[index].split("\\")[-1] + "_dec.ts"
                        else:
                            tmp_output_media_name = "video_" + media[index].split("/")[-1] + "_dec.ts"
                        output_media = os.path.join(video_save_folder, tmp_output_media_name)
                        with open(input_media, "rb") as vin, open(output_media, "wb") as vout:
                            output_dec = self.__aes_dec(vin.read(), key_binary, iv)
                            vout.write(output_dec)
                        output_media_part.append(output_media)
            self.hlsConcat(output_media_part, folder_prefix)

    # 视频合并函数
    def hlsConcat(self, videolist, folder_prefix):
        video_folder = tool.create_folder(WORKDIR, DATENAME, folder_prefix)
        videoput = os.path.join(video_folder, "{}_{}.ts".format(folder_prefix, DATENAME))
        if tool.iswindows():
            concat(videolist, video_folder, videoput, "windows")
        else:
            concat(videolist, video_folder, videoput, "linux")
        tool.data_transfer(videoput, WORKDIR)

    def data_check(self):
        if self.type == "TVer":
            log("info", "(4)Merging Meida...")
            tver_output = os.path.join(WORKDIR, DATENAME + "_all.ts")
            if self.unencrypt:
                tver_video = os.path.join(WORKDIR, "encrypt_video_{}.ts".format(DATENAME))
                tver_audio = os.path.join(WORKDIR, "encrypt_audio_{}.ts".format(DATENAME))
            else:
                tver_video = os.path.join(WORKDIR, "decrypt_video_{}.ts".format(DATENAME))
                tver_audio = os.path.join(WORKDIR, "decrypt_audio_{}.ts".format(DATENAME))
            tool.ffmpeg_concat(tver_video, tver_audio, tver_output)
            msg = "Please Check [ {} ]".format(tver_output)
            if not self.debug:
                encpath_audio = os.path.join(WORKDIR, "encrypt_audio_{}".format(DATENAME))
                decpath_audio = os.path.join(WORKDIR, "decrypt_audio_{}".format(DATENAME))
                tool.clean_cache(encpath_audio, decpath_audio)
        else:
            media_path = os.path.join(WORKDIR, "decrypt_video_{}.ts".format(DATENAME))
            msg = "Please Check [ {} ]".format(media_path)
        if not self.debug:
            encpath_video = os.path.join(WORKDIR, "encrypt_video_{}".format(DATENAME))
            decpath_video = os.path.join(WORKDIR, "decrypt_video_{}".format(DATENAME))
            tool.clean_cache(encpath_video, decpath_video)
        if tool.iswindows():
            interrupt("windows", msg)
        else:
            interrupt("linux", msg)


def opts():
    paras = argparse.ArgumentParser(description="Download HLS video")
    paras.add_argument('-d', dest='debug', action="store_true", default=False, help="DEBUG")
    paras.add_argument('-p', dest='proxy', action="store", default=None, type=str, help="proxy")
    args = paras.parse_args()
    return args


def main():
    para = opts()
    debug = para.debug
    proxies = para.proxy

    playlist = input("Enter Playlist URL: ")
    if playlist:
        HLS = HLSVideo(debug=debug, proxies=proxies)
        HLS.hlsAnalyze(playlist)
        keyvideo = HLS.hlsInfo()
        HLS.hlsDL(keyvideo)
    else:
        msg = "URL Invalid."
        if 'Windows' in platform.system():
            interrupt("windows", msg)
        else:
            interrupt("linux", msg)


if __name__ == "__main__":
    main()
