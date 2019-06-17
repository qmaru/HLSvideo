import os
import platform
import shutil
import subprocess

from utils.interrupt import interrupt


# 判断操作系统
def iswindows():
    return 'Windows' in platform.system()


# 检查 ffmpeg
def ffmpeg_check():
    prog_ffmpeg = subprocess.Popen(
        "ffmpeg -version", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    result = prog_ffmpeg.stderr.read()
    if result:
        msg = "FFMPEG NOT FOUND."
        if iswindows():
            interrupt("windows", msg)
        else:
            interrupt("linux", msg)


# 使用 ffmpeg 合并
def ffmpeg_concat(video, audio, output):
    cmd = "ffmpeg -v quiet -i {} -i {} -c copy {}".format(video, audio, output)
    os.system(cmd)


# 检查地址合法性
def check_host(types, url):
    if url.startswith("http"):
        return ""
    hostdir = input("Enter {}: ".format(types))
    if hostdir.endswith("/"):
        return hostdir
    return hostdir + "/"


# 以时间命名创建文件夹
def create_folder(path, datetag, filename):
    try:
        unique_name = filename + "_" + datetag
        video_path = os.path.join(path, unique_name)
        if os.path.exists(video_path):
            return video_path
        os.mkdir(video_path)
        return video_path
    except BaseException as e:
        raise e


def data_transfer(src_path, dst_path):
    shutil.copy(src_path, dst_path)


def clean_cache(encpath, decpath):
    os.chmod(encpath, 128)
    shutil.rmtree(encpath)
    if os.path.exists(decpath):
        os.chmod(decpath, 128)
        shutil.rmtree(decpath)
