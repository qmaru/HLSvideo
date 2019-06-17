import os


def windows_long_cmd(input_videolist, output_folder, input_total):
    element = 50
    output_video_index = 1
    input_videos = []
    for i in range(0, input_total, element):
        output_video = "out_{}.ts".format(str(output_video_index))
        output_path = os.path.join(output_folder, output_video)
        input_video_parts = "+".join(input_videolist[i: i + element])
        cmd = "copy /B {} {} >nul 2>nul".format(input_video_parts, output_path)
        os.system(cmd)
        output_video_index = output_video_index + 1
        input_videos.append(output_path)
    return "+".join(input_videos)


def concat(input_videolist, output_folder, output_video, ostype):
    if ostype == "windows":
        input_total = len(input_videolist)
        if input_total >= 50:
            input_videos = windows_long_cmd(input_videolist, output_folder, input_total)
        else:
            input_videos = "+".join(input_videolist)
        cmd = "copy /B {} {} >nul 2>nul".format(input_videos, output_video)
    elif ostype == "linux":
        input_videos = " ".join(input_videolist)
        cmd = "cat {} > {}".format(input_videos, output_video)
    os.system(cmd)
