# -*- coding: UTF-8 -*-
# @author AoBeom
# @create date 2017-12-27 18:00:45
# @modify date 2017-12-27 18:00:45
# @desc [STchannel Video Download]
import binascii
import os
import platform
import re
import shutil
import subprocess
import sys
import time
from multiprocessing.dummy import Pool

import requests


class HLSVideo(object):
    def __init__(self):
        self.datename = time.strftime(
            '%y%m%d%H%M%S', time.localtime(time.time()))
        self.videoname = ""
        self.openssl = ""

    # request
    def __requests(self, url, headers=None, cookies=None, timeout=30):
        if headers:
            headers = headers
        else:
            headers = {
                "User-Agent": "UlizaPlayer_Android/2.5.2 (Android/7.1.1; E6533; Build/32.4.A.0.160; Radio/8994-FAAAANAZQ-00028-36)"
            }
        if cookies:
            response = requests.get(url, headers=headers,
                                    cookies=cookies, timeout=timeout)
        else:
            response = requests.get(url, headers=headers, timeout=timeout)
        return response

    # windows / other
    def __isWindows(self):
        return 'Windows' in platform.system()

    # create folder [ filename + now_date ]
    def __isFolder(self, filename):
        try:
            filename = filename + "_" + self.datename
            propath = os.getcwd()
            video_path = os.path.join(propath, filename)
            if not os.path.exists(video_path):
                os.mkdir(video_path)
                return video_path
            else:
                return video_path
        except BaseException, e:
            raise e

    def __errorList(self, value, para1=None, para2=None, para3=None):
        infos = {
            "url_error": "Url is incorrect.",
            "key_error": "Wrong key. Please check url.",
            "total_error": "Video is not complete, please download again [Total: {} Present: {}]".format(para1, para2),
            "not_found": "Not Found {}.ts".format(para1),
            "dec_error": "Solve the problem, please run again [ hlsvideo -e {} -k {} ]".format(para1, para2),
        }
        available = "url_error, key_error, total_error"
        print infos.get(value, "Keyword: " + available)
        raw_input("Press Enter to exit.\r\n")
        sys.exit()

    # openssl / ffmpeg
    def __execCheck(self, video_type):
        prog_openssl = subprocess.Popen(
            "openssl version", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        result_err = prog_openssl.stderr.read()
        if result_err:
            self.openssl = raw_input("openssl path: \r\n")

    # main function [ key, video_url ]
    def hlsInfo(self, playlist):
        playlist = playlist
        key_video = []
        response = self.__requests(playlist)
        m3u8_list_content = response.text
        cookies = response.cookies
        rule_m3u8 = r"^[\w\-\.\/\:\?\&\=]+"
        rule_px = r"RESOLUTION=[\w]+"
        if "m3u8" in m3u8_list_content:
            m3u8urls = re.findall(rule_m3u8, m3u8_list_content, re.S | re.M)
            # check resolution
            px_sel_num = len(m3u8urls)
            if px_sel_num != 1:
                px_sels = re.findall(rule_px, m3u8_list_content, re.S | re.M)
                px_sels = [p.split("=")[-1].replace("x", "").zfill(4)
                           for p in px_sels]
                if len(px_sels) == 0:
                    rule_bd = r"BANDWIDTH=[\w]+"
                    bd_sels = re.findall(
                        rule_bd, m3u8_list_content, re.S | re.M)
                    bd_sels = [b.split("=")[-1].zfill(4) for b in bd_sels]
                    maxindex = bd_sels.index(max(bd_sels))
                else:
                    maxindex = px_sels.index(max(px_sels))
                m3u8kurl = m3u8urls[maxindex]
            else:
                m3u8kurl = ''.join(m3u8urls)
        else:
            self.__errorList("url_error")

        # stchannel info
        parts = m3u8kurl.split("/")
        m3u8host = "http://" + parts[2] + "/" + parts[3] + "/"
        m3u8main = m3u8kurl
        m3u8_content = self.__requests(m3u8main).text

        rule_video = r'[^#\S+][\w\/\-\.\:\?\&\=]+'
        videourl = re.findall(rule_video, m3u8_content, re.S | re.M)
        videohost = m3u8host

        # download key and save urls
        rule_key = r'URI=\"(.*?)\"'
        keyurl = re.findall(rule_key, m3u8_content)
        keyfolder = self.__isFolder("keys")
        keylist = []
        print "(1)Key downloading...[{}]".format(str(len(keyurl)))
        keyurl = ''.join(keyurl)
        # download key
        keyname = "STkey"
        keypath = os.path.join(keyfolder, keyname)
        keylist.append(keypath)
        r = self.__requests(keyurl, cookies=cookies)
        with open(keypath, "wb") as code:
            for chunk in r.iter_content(chunk_size=1024):
                code.write(chunk)
        if os.path.getsize(keypath) != 16:
            self.__errorList("key_error")
        key_video.append(keylist)
        # save urls
        videourls = [videohost + v.strip() for v in videourl]
        key_video.append(videourls)
        return key_video

    def __retry(self, urls, files):
        try:
            print "   Retrying..."
            r = self.__requests(urls)
            with open(files, "wb") as code:
                for chunk in r.iter_content(chunk_size=1024):
                    code.write(chunk)
        except BaseException:
            print "[%s] is failed." % urls

    def __download(self, para):
        urls = para[0]
        files = para[1]
        try:
            r = self.__requests(urls)
            with open(files, "wb") as code:
                for chunk in r.iter_content(chunk_size=1024):
                    code.write(chunk)
        except BaseException:
            self.__retry(urls, files)

    def hlsDL(self, keyvideo):
        keyvideo = keyvideo
        # Check the number of keys
        keypath = [''.join(kv) for kv in keyvideo[0]]
        videourls = keyvideo[1]
        videos = []
        video_folder = self.__isFolder("encrypt")
        # Rename the video for sorting
        for i in range(0, len(videourls)):
            video_num = i + 1
            video_name = str(video_num).zfill(4) + ".ts"
            video_encrypt = os.path.join(video_folder, video_name)
            videos.append(video_encrypt)
        total = len(videourls)
        print "(2)GET Videos...[{}]".format(total)
        print "Please wait..."
        thread = total / 4
        # Multi-threaded configuration
        if thread > 100:
            thread = 20
        else:
            thread = 10
        pool = Pool(thread)
        pool.map(self.__download, zip(videourls, videos))
        pool.close()
        pool.join()
        present = len(os.listdir(video_folder))
        if present != total:
            self.__errorList("total_error", total, present)
        # Video merge
        keypath = ''.join(keypath)
        self.hlsDec(keypath, videos)
        folder = "decrypt_" + self.datename
        videoname = os.path.join(folder, self.datename + ".ts")
        if os.path.exists(videoname):
            print "(3)Successful!"
            print "(4)Please check [ %s ]" % (self.datename + ".ts")

        # clear
        enpath = "encrypt_" + self.datename
        kpath = "keys_" + self.datename
        os.chmod(folder, 128)
        os.chmod(enpath, 128)
        os.chmod(kpath, 128)
        shutil.rmtree(enpath)
        shutil.rmtree(kpath)
        shutil.copy(videoname, os.getcwd())
        shutil.rmtree(folder)

    def __concat(self, ostype, inputv, outputv):
        if ostype == "windows":
            os.system("copy /B " + inputv + " " + outputv + " >nul 2>nul")
        elif ostype == "linux":
            os.system("cat " + inputv + " >" + outputv)

    def hlsConcat(self, videolist, outname=None):
        if outname is None:
            outname = self.datename + ".ts"
        else:
            outname = outname
        videolist = videolist
        stream = ""
        videofolder = self.__isFolder("decrypt")
        videoput = os.path.join(videofolder, outname)
        if self.__isWindows():
            for v in videolist:
                stream += v + "+"
            videoin = stream[:-1]
            self.__concat("windows", videoin, videoput)
        else:
            for v in videolist:
                stream += v + " "
            videoin = stream[:-1]
            self.__concat("linux", videoin, videoput)

    def hlsDec(self, keypath, videos):
        videos = videos
        indexs = range(0, len(videos))
        ivs = range(1, len(videos) + 1)
        k = keypath
        # format key
        STkey = open(k, "rb").read()
        KEY = binascii.b2a_hex(STkey)
        videoin = self.__isFolder("encrypt")
        videoout = self.__isFolder("decrypt")
        new_videos = []
        # Decrypt the video
        for index in indexs:
            inputV = videos[index]
            iv = ivs[index]
            if self.__isWindows():
                outputV = videos[index].split("\\")[-1] + "_dec.ts"
            else:
                outputV = videos[index].split("/")[-1] + "_dec.ts"
            # format iv
            iv = '%032x' % iv
            inputVS = os.path.join(videoin, inputV)
            outputVS = os.path.join(videoout, outputV)
            if self.openssl:
                prog = self.openssl
            else:
                prog = "openssl"
            command = prog + " aes-128-cbc -d -in " + inputVS + \
                " -out " + outputVS + " -nosalt -iv " + iv + " -K " + KEY
            os.system(command)
            new_videos.append(outputVS)
        self.hlsConcat(new_videos)


def main():
    HLS = HLSVideo()
    playlist = raw_input("Enter Playlist url: ")
    keyvideo = HLS.hlsInfo(playlist)
    HLS.hlsDL(keyvideo)
    raw_input("Please press Enter to exit.")


if __name__ == '__main__':
    main()
