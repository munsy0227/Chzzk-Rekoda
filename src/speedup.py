
import subprocess
from pathlib import Path
import os
import re

parent_dir = os.getcwd()
ffmpeg_dir = os.path.join(parent_dir, 'ffmpeg/bin/ffmpeg.exe')

speedup_dir = os.path.join( parent_dir, 'speed up')
os.makedirs(speedup_dir,exist_ok=True)

input_cmd = [f"{ffmpeg_dir}"]

def filter_complex():
    input_cmd.append("-filter_complex")


    

def speed_up() -> tuple:
    setpts = ""

    for i in range(index):
        setpts += f'[{i}:v]setpts=PTS/10[v{i}]; '

    return setpts

def concat() -> str:
    cat_src =""
    for i in range(index):
        cat_src += f"[v{i}]" 


    cat = f"{cat_src}concat=n={index}:v=1:a=0[v]"
    cat = f"{cat}"


    return cat





def checkdir(outputdir: str):
    path = os.path.join(speedup_dir, outputdir)
    print(path)
    if not os.path.exists(path):
        os.makedirs(path)

def isTsFile(file: str) -> bool:
    return True if '.ts' in file else False


def main():
    global index
    index = 0

    while True:
        user = input(f"Enter file {index} location (0 to stop): ")
        if (user == "0"):
            break
        file = user.strip('"')
        input_cmd.append("-i")
        input_cmd.append(file)

        index += 1
        
       

    output = os.path.basename(file)
    
    name_type = re.search(r'(.+)(\..+)$', output)

    fileName = name_type.group(1)
    fileType = name_type.group(2)

    output = output.replace(fileType, '.mp4')

         
        
    
    filter_complex()
    setpts = speed_up()
    cat = concat()

    matchStreamlinkFormat = re.search(r'\] (.*?)\.', output)
    if matchStreamlinkFormat is not None:
        matchStreamlinkFormat = matchStreamlinkFormat.group(1)
    else :
        matchStreamlinkFormat = 'dump'
    
    input_cmd.append(f'{setpts}{cat}')
    input_cmd.append("-map")
    input_cmd.append('[v]')
    input_cmd.append("-c:v")
    input_cmd.append("libx265")
    input_cmd.append("-r")
    input_cmd.append("60")
    checkdir(matchStreamlinkFormat)

    input_cmd.append(f'{speedup_dir}\\{matchStreamlinkFormat}\\{output}')
    print(input_cmd)
    subprocess.run(input_cmd, shell=True, text=True)


if __name__ == "__main__": 
    main()

