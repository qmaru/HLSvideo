#!/usr/bin/env python
#-*- coding: UTF-8 -*-
import os
import sys
import platform
import requests
import re
import binascii
import time
import shutil
from multiprocessing.dummy import Pool


class HLSVideo(object):
    def __init__(self):
        self.datename = time.strftime(
            '%y%m%d%H%M%S', time.localtime(time.time()))
        self.videoname = ""

    def __is_windows_system(self):
        return 'Windows' in platform.system()

    def __is_folder(self, filename):
        try:
            filename = filename + "_" + self.datename
            py_path = os.getcwd()
            video_path = os.path.join(py_path, filename)
            if not os.path.exists(video_path):
                os.mkdir(video_path)
                return video_path
            else:
                return os.path.join(py_path, filename)
        except OSError, e:
            pass

    def hlsinfo(self, playlist):
        playlist = playlist
        key_video = []
        session = requests.Session()
        m3u8list_content = session.get(playlist).text
        rule_m3u8 = r"^[\w\-\.\/\:\?\&\=]+"
        rule_px = r"RESOLUTION=[\w]+"
        if "m3u8" in m3u8list_content:
            m3u8urls = re.findall(rule_m3u8, m3u8list_content, re.S | re.M)
            # check resolution
            px_sel_num = len(m3u8urls)
            if px_sel_num != 1:
                px_sels = re.findall(rule_px, m3u8list_content, re.S | re.M)
                px_sels = [p.split("=")[-1].replace("x", "").zfill(8)
                           for p in px_sels]
                if len(px_sels) == 0:
                    rule_bd = r"BANDWIDTH=[\w]+"
                    bd_sels = re.findall(
                        rule_bd, m3u8list_content, re.S | re.M)
                    bd_sels = [b.split("=")[-1].zfill(8) for b in bd_sels]
                    maxindex = bd_sels.index(max(bd_sels))
                else:
                    maxindex = px_sels.index(max(px_sels))
                m3u8kurl = m3u8urls[maxindex]
            else:
                m3u8kurl = ''.join(m3u8urls)
        else:
            print "Url is incorrect."
            raw_input("Please press Enter to exit.")
            sys.exit()

        # check m3u8 host
        parts = m3u8kurl.split("/")
        m3u8host = "http://" + parts[2] + "/" + parts[3] + "/"
        m3u8main = m3u8kurl
        m3u8_content = session.get(m3u8main).text

        # check video host
        rule_video = r'[^#\S+][\w\/\-\.\:\?\&\=]+'
        videourl = re.findall(rule_video, m3u8_content, re.S | re.M)
        videourl_check = videourl[0].strip()
        videohost = m3u8host

        # download key and save urls
        rule_key = r'URI=\"(.*?)\"'
        keyurl = re.findall(rule_key, m3u8_content)
        keyfolder = self.__is_folder("keys")
        keylist = []
        t = len(keyurl)
        print "(1)Key downloading...[%s]" % t
        keyurl = ''.join(keyurl)
        # download key
        keyname = "STkey"
        keypath = os.path.join(keyfolder, keyname)
        keylist.append(keypath)
        r = session.get(keyurl)
        with open(keypath, "wb") as code:
            code.write(r.content)
        if os.path.getsize(keypath) != 16:
            print "Wrong key. Please check url."
            sys.exit()
        key_video.append(keylist)
        # save urls
        videourls = []
        videourls = [videohost + v.strip() for v in videourl]
        key_video.append(videourls)
        return key_video

    def __retry(self, urls, files):
        try:
            print "   Retrying..."
            r = requests.get(urls, timeout=15)
            with open(files, "wb") as code:
                code.write(r.content)
        except:
            print "[%s] is failed." % files

    def __download(self, para):
        urls = para[0]
        files = para[1]
        try:
            r = requests.get(urls, timeout=30)
            with open(files, "wb") as code:
                code.write(r.content)
        except:
            self.__retry(urls, files)

    def hlsdl(self, keyvideo):
        keyvideo = keyvideo
        # Check the number of keys
        keypath = [''.join(kv) for kv in keyvideo[0]]
        key_num = len(keypath)
        videourls = keyvideo[1]
        videos = []
        video_folder = self.__is_folder("encrypt")
        # Rename the video for sorting
        for i in range(0, len(videourls)):
            I = i + 1
            video_name = str(I).zfill(8) + ".ts"
            video_encrypt = os.path.join(video_folder, video_name)
            videos.append(video_encrypt)
        total = len(videourls)
        print "(2)Videos downloading...[%s]" % total
        thread = total / 2
        pool = Pool(thread)
        pool.map(self.__download, zip(videourls, videos))
        pool.close()
        pool.join()
        present = len(os.listdir(video_folder))
        if present != total:
            print "Video is not complete, please download again [Total: %s Present: %s]" % (total, present)
            raw_input("Please press Enter to exit.")
            sys.exit()
        # Video merge
        keypath = ''.join(keypath)
        self.hlsdec(keypath, videos)
        folder = "decrypt_" + self.datename
        videoname = os.path.join(folder, self.datename + ".ts")
        if os.path.exists(folder):
            print "(3)Successful!"
            print "(4)Please check [ %s ]" % (self.datename + ".ts")

        # clear
        enpath = "encrypt_" + self.datename
        kpath = "keys_" + self.datename
        os.chmod(folder,128)
        os.chmod(enpath,128)
        os.chmod(kpath,128)
        shutil.rmtree(enpath)
        shutil.rmtree(kpath)
        shutil.copy(videoname, os.getcwd())
        shutil.rmtree(folder)


    def __concat(self, ostype, inputv, outputv, outname=None):
        if outname == None:
            outname = self.datename + ".ts"
            self.videoname = self.datename
        else:
            outname = outname
        if ostype == "windows":
            os.system("copy /B " + inputv + " " + outputv + " >nul 2>nul")
        elif ostype == "linux":
            os.system("cat " + inputv + " >" + outputv)

    def hlsconcat(self, videolist, outname=None):
        if outname == None:
            outname = self.datename + ".ts"
        else:
            outname = outname
        videolist = videolist
        stream = ""
        videofolder = self.__is_folder("decrypt")
        videoput = os.path.join(videofolder, outname)
        if self.__is_windows_system():
            for v in videolist:
                stream += v + "+"
            videoin = stream[:-1]
            self.__concat("windows", videoin, videoput, outname)
        else:
            for v in videolist:
                stream += v + " "
            videoin = stream[:-1]
            self.__concat("linux", videoin, videoput, outname)

    def hlsdec(self, keypath, videos, outname=None, ivs=None):
        if outname == None:
            outname = self.datename + ".ts"
        else:
            outname = outname
        videos = videos
        indexs = range(0, len(videos))
        if ivs == None:
            ivs = range(1, len(videos) + 1)
        else:
            ivs = ivs
        k = keypath
        # format key
        STkey = open(k, "rb").read()
        KEY = binascii.b2a_hex(STkey)
        videoin = self.__is_folder("encrypt")
        videoout = self.__is_folder("decrypt")
        new_videos = []
        # Decrypt the video
        for index in indexs:
            inputV = videos[index]
            iv = ivs[index]
            if self.__is_windows_system():
                outputV = videos[index].split("\\")[-1] + "_dec.ts"
            else:
                outputV = videos[index].split("/")[-1] + "_dec.ts"
            # format iv
            iv = '%032x' % iv
            inputVS = os.path.join(videoin, inputV)
            outputVS = os.path.join(videoout, outputV)
            os.system("openssl aes-128-cbc -d -in " + inputVS +
                      " -out " + outputVS + " -nosalt -iv " + iv + " -K " + KEY)
            new_videos.append(outputVS)
        self.hlsconcat(new_videos, outname)


def main():
    HLS = HLSVideo()
    playlist = raw_input("Enter Playlist url: ")
    keyvideo = HLS.hlsinfo(playlist)
    HLS.hlsdl(keyvideo)
    raw_input("Please press Enter to exit.")


if __name__ == '__main__':
    main()
