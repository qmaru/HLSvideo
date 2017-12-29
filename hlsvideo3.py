# -*- coding: UTF-8 -*-
# @author AoBeom
# @create date 2017-12-25 04:49:59
# @modify date 2017-12-25 04:49:59
# @desc [HLS downloader]
import argparse
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
    def __init__(self, debug=False):
        self.keyparts = 0
        self.iv = 0
        self.datename = time.strftime(
            '%y%m%d%H%M%S', time.localtime(time.time()))
        self.debug = debug
        self.dec = 0
        self.type = ""

    # requests处理
    def __requests(self, url, headers=None, cookies=None, timeout=30):
        if headers:
            headers = headers
        else:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36"
            }
        if cookies:
            response = requests.get(url, headers=headers,
                                    cookies=cookies, timeout=timeout)
        else:
            response = requests.get(url, headers=headers, timeout=timeout)
        return response

    # 错误处理 最多接收4个变量
    def __errorList(self, value, para1=None, para2=None, para3=None):
        infos = {
            "url_error": "Url is incorrect.",
            "key_error": "Wrong key. Please check url.",
            "total_error": "Video is not complete, please download again [Total: {} Present: {}]".format(para1, para2),
            "not_found": "Not Found {}.ts".format(para1),
            "dec_error": "Solve the problem, please run again [ hlsvideo -e {} -k {} ]".format(para1, para2),
        }
        available = "url_error, key_error, total_error"
        print(infos.get(value, "Keyword: " + available))
        input("Press Enter to exit.\r\n")
        sys.exit()

    # debug输出
    def __debugInfo(self, value, para1=None, para2=None, para3=None, status=None):
        if para1 == "" or para1 == 0:
            para1 = None
        infos = {
            "site": "DEBUG [VIDEOTYPE]: {}\nDEBUG [PLAYLIST]: {}".format(para1, para2),
            "m3u8url": "DEBUG [M3U8MAIN]: {}".format(para1),
            "m3u8": "DEBUG [M3U8HOST]: {}".format(para1),
            "videohost": "DEBUG [VIDEOHOST]: {}".format(para1),
            "keyurl": "DEBUG [KEYURL]: {}".format(para1),
            "videourls": "DEBUG [VIDEOURL]: {}".format(para1),
            "videoparts": "DEBUG [VIDEOPARTS]: {}".format(para1),
            "deccmd": "DEBUG [DECERROR]: {}".format(para1),
            "keyfolder": "DEBUG [KEYFOLDER]: {}".format(para1),
            "encfolder": "DEBUG [ENCVIDEO]: {}".format(para1),
            "decfolder": "DEBUG [DECVIDEO]: {}".format(para1),
        }
        available = "site,m3u8url,m3u8,videohost\nkeyurl,videourls,videoparts,deccmd\nkeyfolder,encfolder,decfolder"
        print(infos.get(value, "Keyword: \n" + available))

    # 检查外部应用程序
    def __execCheck(self, video_type):
        prog_openssl = subprocess.Popen(
            "openssl version", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        result_err = prog_openssl.stderr.read()
        if result_err:
            input("openssl NOT FOUND.\r\n")
            sys.exit()
        if video_type == "TVer":
            prog_ffmpeg = subprocess.Popen(
                "ffmpeg -version", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            result = prog_ffmpeg.stderr.read()
            if result:
                input("FFMPEG NOT FOUND.\r\n")
                sys.exit()

    # 检查是否地址合法性
    def __checkHost(self, types, url):
        if url.startswith("http"):
            hostdir = ""
        else:
            hostdir = input("Enter {types}: ".format(types))
            if hostdir.endswith("/"):
                hostdir = hostdir
            else:
                hostdir = hostdir + "/"
        return hostdir

    # 以当前时间创建文件夹
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
        except BaseException as e:
            raise e

    # 判断操作系统
    def __isWindows(self):
        return 'Windows' in platform.system()

    # 识别HLS的类型
    def hlsSite(self, playlist):
        type_dict = {
            "GYAO": "gyao",
            "TVer": "manifest.prod.boltdns.net",
            "Asahi": "tv-asahi",
            "STchannel": "aka-bitis-hls-vod.uliza.jp",
            "DMM": "dmm",
            "FOD": "fod",
            "MBS": "secure.brightcove.com"
        }
        # 通过关键字判断HLS的类型
        type_check = self.__requests(playlist).text
        for site, keyword in type_dict.items():
            if keyword in playlist:
                video_type = site
            if keyword in type_check:
                video_type = site
        try:
            video_type = video_type
        except BaseException:
            video_type = None
        self.type = video_type
        self.__execCheck(video_type)
        if self.debug:
            self.__debugInfo("site", video_type, playlist)
        return playlist, video_type

    # 根据类型做不同的处理 下载key并提取video列表
    def hlsInfo(self, site):
        playlist = site[0]
        video_type = site[1]
        key_video = []
        # key的下载需要playlist的cookies
        if video_type == "FOD":
            m3u8kurl = playlist
        else:
            response = self.__requests(playlist)
            m3u8_list_content = response.text
            cookies = response.cookies
            # 提取m3u8列表的最高分辨率的文件
            rule_m3u8 = r"^[\w\-\.\/\:\?\&\=\%]+"
            rule_px = r"RESOLUTION=[\w]+"
            # 根据分辨率匹配
            if "m3u8" in m3u8_list_content:
                m3u8urls = re.findall(
                    rule_m3u8, m3u8_list_content, re.S | re.M)
                px_sel_num = len(m3u8urls)
                # 根据码率匹配
                if px_sel_num != 1:
                    px_sels = re.findall(
                        rule_px, m3u8_list_content, re.S | re.M)
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
                    if video_type == "MBS":
                        m3u8kurl = m3u8urls[-1]
                    else:
                        m3u8kurl = m3u8urls[maxindex]
                else:
                    m3u8kurl = ''.join(m3u8urls)
            else:
                self.__errorList("url_error")

        if self.debug:
            self.__debugInfo("m3u8url", m3u8kurl)

        # clip
        if video_type == "GYAO" or video_type == "MBS":
            self.keyparts = 10

        # m3u8 host
        if video_type == "GYAO":
            m3u8host = "https://" + playlist.split("/")[2] + "/"
        elif video_type == "DMM":
            m3u8host = ""
            url_part = playlist.split("/")[1:-1]
            for url_p in url_part:
                m3u8host = m3u8host + url_p + "/"
            m3u8host = "http:/" + m3u8host
        elif video_type == "FOD":
            m3u8host = ""
        else:
            m3u8host = self.__checkHost("m3u8 host", m3u8kurl)

        m3u8main = m3u8host + m3u8kurl
        m3u8_content = self.__requests(m3u8main).text

        if self.debug:
            self.__debugInfo("m3u8", m3u8host)

        # video host
        rule_video = r'[^#\S+][\w\/\-\.\:\?\&\=]+'
        videourl = re.findall(rule_video, m3u8_content, re.S | re.M)
        videourl_check = videourl[0].strip()

        if video_type == "GYAO":
            videohost = m3u8host
        elif video_type == "DMM":
            videohost = m3u8host
        elif video_type == "FOD":
            videohost = ""
            url_part = playlist.split("/")[1:-1]
            for url_p in url_part:
                videohost = videohost + url_p + "/"
            videohost = "https:/" + videohost
        elif video_type == "Asahi" or video_type == "STchannel":
            hostlist = m3u8main.split("/")[1:-1]
            videohost = m3u8main.split("/")[0] + "//"
            for parts in hostlist:
                if parts:
                    videohost = videohost + parts + "/"
        else:
            videohost = self.__checkHost("video host", videourl_check)

        if self.debug:
            self.__debugInfo("videohost", videohost)

        # TVer audio rule [ Only need audio links ]
        if video_type == "TVer":
            audio_rule = r'TYPE=AUDIO(.*?)URI=\"(.*?)\"'
            audio_m3u8_url = re.findall(audio_rule, m3u8_list_content)[-1][-1]
            audio_content = self.__requests(audio_m3u8_url).text
            audiourl = re.findall(rule_video, audio_content, re.S | re.M)
            rule_iv = r'IV=[\w]+'
            iv_value = re.findall(rule_iv, m3u8_content)
            self.iv = ''.join(iv_value).split("=")[-1][2:]
            audiohost = ""
        if video_type == "FOD":
            rule_iv = r'IV=[\w]+'
            iv_value = re.findall(rule_iv, m3u8_content)
            self.iv = ''.join(iv_value).split("=")[-1][2:]

        # download key and save url
        rule_key = r'URI=\"(.*?)\"'
        keyurl = re.findall(rule_key, m3u8_content)
        if self.debug:
            self.__debugInfo("keyurl", keyurl)
        if keyurl:
            # tv-asahi分片数由m3u8文件决定
            if "tv-asahi" in m3u8main:
                if len(keyurl) > 1:
                    key_parts = keyurl[1].split("/")[-1].split("=")[-1]
                    self.keyparts = int(key_parts)
            if self.debug:
                self.__debugInfo("videoparts", self.keyparts)
            keyfolder = self.__isFolder("keys")
            if self.debug:
                self.__debugInfo("keyfolder", keyfolder)
            keylist = [] 
            print("(1)GET Key...[{}]".format(len(keyurl)))
            for i, k in enumerate(keyurl):
                # download key
                key_num = i + 1
                url = m3u8host + k
                if video_type == "DMM":
                    url = k
                # rename key
                keyname = str(key_num).zfill(4) + "_key"
                keypath = os.path.join(keyfolder, keyname)
                keylist.append(keypath)
                if video_type == "FOD":
                    r = self.__requests(url)
                else:
                    r = self.__requests(url, cookies=cookies)
                with open(keypath, "wb") as code:
                    for chunk in r.iter_content(chunk_size=1024):
                        code.write(chunk)
            if os.path.getsize(keypath) != 16:
                self.__errorList("key_error")
            key_video.append(keylist)
            # save urls
            videourls = [videohost + v.strip() for v in videourl]
            if self.debug:
                self.__debugInfo("videourls", videourls[0])
            key_video.append(videourls)
            # TVer audio url
            if video_type == "TVer":
                key_audio = []
                audiourls = [audiohost + a.strip() for a in audiourl]
                key_audio.append(keylist)
                key_audio.append(audiourls)
                try:
                    self.__tverdl(key_audio)
                except Exception as e:
                    raise e
        else:
            print("(1)No key.")
            keypath = ""
            videourls = []
            rule_video = r'[^#\S+][\w\/\-\.\:\?\&\=]+'
            # save urls
            videourl = re.findall(rule_video, m3u8_content, re.S | re.M)
            videourl_check = videourl[0].strip()
            videohost = self.__checkHost("video host", videourl_check)
            videourls = [videohost + v.strip() for v in videourl]
            if self.debug:
                self.__debugInfo("videourls", videourls[0])
            key_video.append(keypath)
            key_video.append(videourls)
        return key_video

    # 下载重试函数
    def __retry(self, urls, files):
        try:
            print("   Retrying...")
            r = self.__requests(urls)
            with open(files, "wb") as code:
                for chunk in r.iter_content(chunk_size=1024):
                    code.write(chunk)
        except BaseException:
            print("[%s] is failed." % urls)

    # 下载处理函数
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

    # 下载函数
    def hlsDL(self, key_video):
        key_video = key_video
        # Check the number of keys
        key_path = [''.join(kv) for kv in key_video[0]]
        key_num = len(key_path)
        video_urls = key_video[1]
        videos = []  # 视频保存路径列表
        video_folder = self.__isFolder("encrypt")
        if self.debug:
            self.__debugInfo("encfolder", video_folder)
        # Rename the video for sorting
        for i in range(0, len(video_urls)):
            video_num = i + 1
            video_name = str(video_num).zfill(4) + ".ts"
            video_encrypt = os.path.join(video_folder, video_name)
            videos.append(video_encrypt)
        total = len(video_urls)
        print("(2)GET Videos...[{}]".format(total))
        print("Please wait...")
        thread = total // 4
        # Multi-threaded configuration
        if thread > 100:
            thread = 20
        else:
            thread = 10
        pool = Pool(thread)
        pool.map(self.__download, zip(video_urls, videos))
        pool.close()
        pool.join()
        present = len(os.listdir(video_folder))
        # 比较总量和实际下载数
        if present != total:
            self.__errorList("total_error", total, present)
        # 有key则调用解密函数
        if key_path:
            # 只有1个key调用hlsDec
            if key_num == 1:
                key_path = ''.join(key_path)
                try:
                    self.hlsDec(key_path, videos)
                except Exception as e:
                    raise e
            # hlsPartition
            else:
                try:
                    self.hlsPartition(key_path, videos)
                except Exception as e:
                    raise e
        # 无key则直接合并视频
        else:
            try:
                self.hlsConcat(videos)
            except Exception as e:
                raise e

        # 后置处理 删除临时文件
        folder = "decrypt_" + self.datename
        video_name = os.path.join(folder, self.datename + ".ts")
        if os.path.exists(video_name):
            print("(3)Good!")
            if self.debug:
                print("(4)Please check [ {}/{}.ts ]".format(folder, self.datename))
            else:
                print("(4)Please check [ {}.ts ]".format(self.datename))
            # 清理临时文件
            if not self.debug:
                enpath = "encrypt_" + self.datename
                kpath = "keys_" + self.datename
                os.chmod(folder, 128)
                os.chmod(enpath, 128)
                if os.path.exists(kpath):
                    os.chmod(kpath, 128)
                    shutil.rmtree(kpath)
                shutil.rmtree(enpath)
                shutil.copy(video_name, os.getcwd())
                shutil.rmtree(folder)
                if self.type == "TVer":
                    self.__concat_audio_video()
        else:
            self.__errorList("not_fount", self.datename)

    # 视频解密函数
    def hlsDec(self, keypath, videos, outname=None, ivs=None, videoin=None):
        if outname is None:
            outname = self.datename + ".ts"
        else:
            outname = outname
        videos = videos
        indexs = range(0, len(videos))
        # 判断iv值，为空则序列化视频下标，否则用给定的iv值
        if ivs is None:
            ivs = range(1, len(videos) + 1)
        else:
            ivs = ivs
        k = keypath
        # format key
        STkey = open(k, "rb").read()
        KEY = binascii.b2a_hex(STkey)
        KEY = str(KEY, encoding="utf-8")
        if videoin:
            videoin = videoin
        else:
            videoin = self.__isFolder("encrypt")
        videoout = self.__isFolder("decrypt")
        if self.debug is True and self.dec == 0:
            self.dec = 1
            self.__debugInfo("decfolder", videoout)
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
            if self.iv != 0:
                iv = self.iv
            else:
                iv = '%032x' % iv
            inputVS = os.path.join(videoin, inputV)
            outputVS = os.path.join(videoout, outputV)
            # 解密命令 核心命令
            command = "openssl aes-128-cbc -d -in " + inputVS + \
                " -out " + outputVS + " -nosalt -iv " + iv + " -K " + KEY
            p = subprocess.Popen(command, stderr=subprocess.PIPE, shell=True)
            result = p.stderr.read()
            if result:
                if self.debug:
                    print("DEBUG [DECERROR]: VIDOE={}".format(inputV))
                    print("DEBUG [DECERROR]: IV={}".format(iv))
                    print("DEBUG [DECERROR]: KEY={}".format(KEY))
                    self.__debugInfo("deccmd", command)
                self.__errorList("dec_error", videoin, keypath)
            new_videos.append(outputVS)
        self.hlsConcat(new_videos, outname)

    # 合并处理函数
    def __concat(self, ostype, inputv, outputv):
        if ostype == "windows":
            os.system("copy /B " + inputv + " " + outputv + " >nul 2>nul")
        elif ostype == "linux":
            os.system("cat " + inputv + " >" + outputv)

    # windows特殊处理
    def __longcmd(self, videolist, videofolder, videoput):
        videolist = videolist
        totle = len(videolist)
        # 将cmd的命令切割
        cut = 50
        part = totle / cut
        parts = []
        temp = []
        for v in videolist:
            temp.append(v)
            if len(temp) == cut:
                parts.append(temp)
                temp = []
            if len(parts) == part:
                parts.append(temp)
        outputs = []
        for index, p in enumerate(parts):
            stream = ""
            outputname = "out_{}.ts".format(str(index + 1))
            outputpath = os.path.join(videofolder, outputname)
            outputs.append(outputpath)
            for i in p:
                stream += i + "+"
            videoin = stream[:-1]
            self.__concat("windows", videoin, outputpath)
        flag = ""
        for output in outputs:
            flag += output + "+"
        videoin_last = flag[:-1]
        self.__concat("windows", videoin_last, videoput)

    # 视频合并函数
    def hlsConcat(self, videolist, outname=None):
        if outname is None:
            outname = self.datename + ".ts"
        else:
            outname = outname
        videolist = videolist
        stream = ""
        # 解密视频路径
        video_folder = self.__isFolder("decrypt")
        videoput = os.path.join(video_folder, outname)
        # Windows的合并命令
        if self.__isWindows():
            self.__longcmd(videolist, video_folder, videoput)
        # Liunx的合并命令
        else:
            for v in videolist:
                stream += v + " "
            videoin = stream[:-1]
            self.__concat("linux", videoin, videoput)

    # 多key解密函数
    def hlsPartition(self, keypath, videos):
        keypath = keypath
        videos = videos
        key_num = len(keypath)
        video_num = len(videos)
        if self.keyparts > 0:
            parts_s = int(self.keyparts)
        else:
            # 根据视频数和key数分片
            parts_s = int(round((video_num) / float(key_num)))
        # ditc[key]=list[videos] 一个key对应多个video
        for i in range(0, key_num):
            out_num = i + 1
            key = keypath[i]
            outname = "video_" + str(out_num).zfill(4) + ".ts"
            index_s = i * parts_s
            index_e = index_s + parts_s
            ivs = range(index_s + 1, index_e + 1)
            video_mvs = videos[index_s:index_e]
            self.hlsDec(key, video_mvs, outname, ivs)
            time.sleep(0.1)
        folder = "decrypt_" + self.datename
        decvideos = os.listdir(folder)
        devs = [decv for decv in decvideos if decv.startswith("video_")]
        devs_path = [os.path.join(os.getcwd(), folder, dp) for dp in devs]
        try:
            self.hlsConcat(devs_path)
        except Exception as e:
            raise e

    # TVer audio 基本上和hlsDL一致
    def __tverdl(self, keyaudio):
        keyaudio = keyaudio
        keypath = keyaudio[0]
        audiourls = keyaudio[1]
        audio_folder = self.__isFolder("encrypt_audio")
        audios = []
        # Rename the video for sorting
        for i in range(0, len(audiourls)):
            audio_num = i + 1
            audio_name = str(audio_num).zfill(4) + ".ts"
            audio_encrypt = os.path.join(audio_folder, audio_name)
            audios.append(audio_encrypt)
        total = len(audiourls)
        print("(SP1)GET Audios...[{}]".format(total))
        print("Please wait...")
        thread = total // 2
        if thread > 100:
            thread = 100
        else:
            thread = thread
        pool = Pool(thread)
        pool.map(self.__download, zip(audiourls, audios))
        pool.close()
        pool.join()
        present = len(os.listdir(audio_folder))
        if present != total:
            self.__errorList("total_error", total, present)
        # Audio merge
        audio_file = self.datename + "_audio.ts"
        if keypath:
            keypath = ''.join(keypath)
            self.hlsDec(keypath, audios, audio_file)
        folder_audio = "decrypt_" + self.datename
        audioname = os.path.join(folder_audio, audio_file)
        if os.path.exists(folder_audio):
            print("(SP1)Good!")
        if not self.debug:
            enpath = "encrypt_audio_" + self.datename
            os.chmod(folder_audio, 128)
            os.chmod(enpath, 128)
            shutil.rmtree(enpath)
            shutil.copy(audioname, os.getcwd())
            shutil.rmtree(folder_audio)

    # TVer video/audio merge
    def __concat_audio_video(self):
        if self.iv != 0:
            # TVer音视频合并
            v = os.path.join(os.getcwd(), self.datename + ".ts")
            a = os.path.join(os.getcwd(), self.datename + "_audio.ts")
            try:
                os.system("ffmpeg -i " + v + " -i " + a +
                          " -c copy " + self.datename + "_all.ts")
                print()
                print("Please Check [ %s_all.ts ]" % self.datename)
            except BaseException:
                print("FFMPEG ERROR.")
                sys.exit()

    def hlsRedec(self, key, encfolder):
        videos = os.listdir(encfolder)
        videoin = encfolder
        self.hlsDec(key, videos, videoin=videoin)


def opts():
    paras = argparse.ArgumentParser(description="Download HLS video")
    paras.add_argument('-d', dest='debug', action="store_true",
                       default=False, help="DEBUG")
    paras.add_argument('-e', dest='encfolder', action="store",
                       default=None, help="Encrypt folder")
    paras.add_argument('-k', dest='key', action="store",
                       default=None, help="Key")
    args = paras.parse_args()
    return args


def main():
    para = opts()
    debug = para.debug
    key = para.key
    encfolder = para.encfolder

    if encfolder and key:
        HLS = HLSVideo(debug=debug)
        HLS.hlsRedec(key, encfolder)
    else:
        playlist = input("Enter Playlist URL: ")
        HLS = HLSVideo(debug=debug)
        site = HLS.hlsSite(playlist)
        keyvideo = HLS.hlsInfo(site)
        HLS.hlsDL(keyvideo)


if __name__ == "__main__":
    main()