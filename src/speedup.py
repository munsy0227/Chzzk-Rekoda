
import subprocess
from pathlib import Path
import os
import send2trash as st
import re
parent_dir = os.getcwd()
ffmpeg_dir = os.path.join(parent_dir, 'ffmpeg/bin/ffmpeg.exe')
speedup_dir = os.path.join( parent_dir, 'speed up')
ffprob_fir = os.path.join(parent_dir, 'ffmpeg\\bin\\ffprobe.exe')



    

def speed_up(video_to_edit: list, index: int) -> str:
    setpts = ""
    for i in range(index):
        video = next((v for v in video_to_edit if v["index"] == i), None)
        if video:
            setpts += build_trim_filter(i, video.get('start', ''), video.get('end', ''))
        else:
            setpts += f"[{i}:v]setpts=PTS/10[v{i}]; "
    return setpts


def concat(index: int) -> str:
    cat_src =""
    for i in range(index):
        cat_src += f"[v{i}]" 


    cat = f"{cat_src}concat=n={index}:v=1:a=0[v]"
    cat = f"{cat}"


    return cat




def checkdir(outputdir: str):
    path = os.path.join(speedup_dir, outputdir)
    if not os.path.exists(path):
        os.makedirs(path)

def isTsFile(file: str) -> bool:
    return True if '.ts' in file else False

def edit():
    video_to_edit = []
    prev_input = 'y'
    while prev_input == 'y': 
        video_index = int(input("video index: ")) - 1
        start = input("start (hh/mm/ss, enter to skip): ")
        end = input("end (hh/mm/ss): ")
        # Convert timestamps from 'hh/mm/ss' to 'hh\:mm\:ss'
        start_hms = start.replace('/', '\\:')
        end_hms = end.replace('/', '\\:')
        video_to_edit.append(dict(index= video_index,start= start_hms, end= end_hms))

        prev_input = input("Do u wanna continue trimming? (y/n): ")
    
    return video_to_edit


def get_length(filename):
    result = subprocess.run([ffprob_fir, "-v", "error", "-show_entries",
                             "format=duration", "-of",
                             "default=noprint_wrappers=1:nokey=1", filename], shell=False, text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)

    return float(result.stdout)

def compare_length(videos, speedup) -> bool:
    ori = 0
    for video in videos:
        ori += get_length(video)
    
    speed = get_length(speedup)
    if (speed - 120 <= ori//10 <= speed + 120):    
        print("speed up ok!")
        print(speed)
        print(ori)
        return True
    
    print("somthimg is wrong, check again")
    return False

def delete_video(videos):
    try:
        for video in videos:
            if os.path.exists(video):  # Check if the file exists
                st.send2trash(video)  # Delete the file
                print(f"File '{video}' has been deleted.")
            else:
                print(f"File '{video}' does not exist.")
    except Exception as e:
        print(f"An error occurred: {e}")

def build_trim_filter(index: int, start: str = '', end: str = '') -> str:
    if start and end:
        return f"[{index}:v]trim=start='{start}':end='{end}',setpts=PTS/10[v{index}]; "
    elif start:
        return f"[{index}:v]trim=start='{start}',setpts=PTS/10[v{index}]; "
    elif end:
        return f"[{index}:v]trim=end='{end}',setpts=PTS/10[v{index}]; "
    return f"[{index}:v]setpts=PTS/10[v{index}];"

    
def ask_delete(comp_result: bool, videos_dir: list):
    if comp_result:
        y_n = input("Do u wanna delete original videos? (y/n): ")
    if y_n == 'y':
        delete_video(videos_dir)

def construct_args(files: list, video_to_edit = []) -> tuple[list, list]:
    input_cmd = [f"{ffmpeg_dir}"]
    index = len(files)
    for video in files:
        input_cmd.extend(["-i", video])
        print(files)
            
    output = os.path.basename(files[0])
    
    name_type = re.search(r'(.+)(\..+)$', output)

    fileName = name_type.group(1)
    fileType = name_type.group(2)

    fileType = fileType.replace(fileType, '.ts')

    output = fileName + fileType
    
    input_cmd.append("-filter_complex")
    setpts = speed_up(video_to_edit, index)
    cat = concat(index)

    matchStreamlinkFormat = re.search(r'\] (.*?)\.', output)
    if matchStreamlinkFormat is not None:
        matchStreamlinkFormat = matchStreamlinkFormat.group(1)
    else :
        matchStreamlinkFormat = 'dump'
    
    input_cmd += [f'{setpts}{cat}',"-map", '[v]',  "-r", "60" ]
    # appendList = [ "-c:v", "hevc_nvenc",
    #          "-preset:v", "p7",
    #         #  "-cq:v", "28",
    #          "-profile:v", "main",
    #          "-tier", "high",
    #          "-tune:v", 'hq',
    #          '-pix_fmt', 'yuv420p',
    #           "-bf", "4",]
    # appendList += ["-rc", "vbr"]    
    # appendList += ["-b:v", "1.5M", "-maxrate", "3M", "-bufsize", "6M"]
    # appendList += ['-multipass', "fullres"]

    appendList = ["-c:v", "libx265"]
    appendList += ["-g", "120"]
    appendList += ["-rc-lookahead", "64"]
    appendList += ['-an']
    # appendList += ['-t', '600']


    input_cmd += appendList
    checkdir(matchStreamlinkFormat)

    output_dir = f'{speedup_dir}\\{matchStreamlinkFormat}\\{output}'
    input_cmd.append(output_dir)

    return [input_cmd, files] 
def main():

    waitlist = []
    confirm_delete = []
    continue_ask = 1

    while continue_ask:
        mode = int(input("Choose mode: 0 - normal 1 - bulk: "))
        if mode == 1: 
            playlist = []
            while True:
                user = input(f"Enter files : ")
                if user == "0":
                    break 
                video_path = user.strip('"')
                playlist.append(video_path)
         
            # playlist = re.findall(r'"(.)"', user_input)
            for video in playlist: 
                args = construct_args([video])
                waitlist.append(args)

        if mode == 0:
            index = 0
            files = []
            while True:
                user = input(f"Enter file {index+1} location (0 to stop, 1 to end n trim): ")
                if user == "0":
                    video_to_edit = []
                    break
                if user == "1":
                    video_to_edit = edit() 
                    break
                file = user.strip('"')
                files += [file]
            
            args = construct_args(files, video_to_edit)
            waitlist.append(args)

        continue_ask = int(input("Construct waitlist for other videos? (0/1): "))
            

  
    for task in waitlist:
        input_cmd = task[0]
        print(input_cmd)
        videos_dir = task[1]

        subprocess.run(input_cmd, shell=True, text=True)
        output_dir = input_cmd[-1]

    
        comp_result = compare_length(videos_dir,output_dir)
        confirm_delete.append([comp_result, videos_dir, output_dir])
    
    for delete_task in confirm_delete:
        comp_result, videos_dir, output_dir = delete_task
        print(delete_task)
        ask_delete(comp_result, videos_dir=videos_dir)

if __name__ == "__main__": 
    main()

