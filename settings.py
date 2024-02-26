import os
import time
import json

# 파일 경로 설정
script_directory = os.path.dirname(os.path.abspath(__name__))
channel_count_file_path = os.path.join(script_directory, 'channel_count.txt')
channels_file_path = os.path.join(script_directory, 'channels.json')
delays_file_path = os.path.join(script_directory, 'delays.json')

# channels 리스트 정의
channels = []

# 채널 수 불러오기
if os.path.exists(channels_file_path):
    with open(channels_file_path, "r") as f:
        channels = json.load(f)
    channel_count = len(channels)
else:
    channel_count = 0

# 기존 딜레이 정보 불러오기
if os.path.exists(delays_file_path):
    with open(delays_file_path, "r") as f:
        delays = json.load(f)
else:
    delays = {}

def 다시입력하기():
        print("다시 입력해주세요.\n")
        time.sleep(1)

while True:
    print("Chzzk 자동녹화 설정")
    print("\n1. 채널 설정\n2. 녹화 설정(미구현)\n3. 쿠키 설정(성인 인증 관련)(미구현)\n4. 나가기")
    값 = str(input("실행하고 싶은 번호를 입력해주세요: "))
    if 값 == "1":
        while True:
            print("\n1. 채널 추가\n2. 채널 삭제(약간 문제있음)\n3. 채널 on/off(미구현)\n4. 돌아가기")
            값1 = str(input("실행하고 싶은 번호를 입력해주세요: "))
            if 값1 == "1":
                while True:
                    id = str(input("원하시는 스트리머 채널의 고유 id를 적어주세요: "))
                    name = str(input("스트리머 이름을 적어주세요:  "))
                    output_dir = str(input("저장 경로를 지정해주세요(이름만 적으면 프로그램과 같은 위치에 저장 됩니다): "))
                    answer = str(input(f"id: {id}, 이름: {name}, 저장 경로: {output_dir} 가 맞나요? (Y/N): "))
                    if answer == "Y":
                        channel_count += 1
                        identifier = f"ch{channel_count}"
                        channels.append({
                            "id": id,
                            "name": name,
                            "output_dir": output_dir,
                            "identifier": identifier
                        })
                        delays[identifier] = channel_count - 1
                        
                        # 파일에 데이터 추가
                        with open(channels_file_path, "w") as f:
                            json.dump(channels, f, indent=2)
                            f.write('\n')  # 각 채널을 개별 줄로 저장하기 위해 개행 문자 추가
                        print("channels.json 파일이 수정되었습니다.")
                        with open(delays_file_path, "w") as f:
                            json.dump(delays, f, indent=2)
                        print("delays.json 파일이 수정되었습니다.")
                        with open(channel_count_file_path, "w") as f:
                            f.write(str(channel_count))
                        break
                    elif answer == "N":
                        print("그러면 다시 입력해 주세요")
                        time.sleep(1)
                    else:
                        print("다시 입력해주세요.\n")
                        time.sleep(1)
            elif 값1 == "2":
                # 채널 삭제
                print("현재 설정된 채널 목록:")
                for 채널 in channels:
                    print(f"id: {채널['id']}, 이름: {채널['name']}")

                삭제할_채널_ID = input("삭제할 채널의 ID를 입력하세요: ")
                삭제할_채널_인덱스 = -1
                for index, 채널 in enumerate(channels):
                    if 채널['id'] == 삭제할_채널_ID:
                        삭제할_채널_인덱스 = index
                        break
                if 삭제할_채널_인덱스 != -1:
                    del_채널 = channels.pop(삭제할_채널_인덱스)
                    print(f"삭제된 채널: id: {del_채널['id']}, 이름: {del_채널['name']}")
                    # 파일에 데이터 추가
                    with open(channels_file_path, "w") as f:
                        json.dump(channels, f, indent=2)
                        f.write('\n')  # 각 채널을 개별 줄로 저장하기 위해 개행 문자 추가
                    print("channels.json 파일이 수정되었습니다.")
                    # channel_count 수정
                    channel_count -= 1
                    with open(channel_count_file_path, "w") as f:
                        f.write(str(channel_count))
                    # delays 수정
                    delays.pop(삭제할_채널_ID, None)  # 삭제된 채널 ID에 해당하는 딕셔너리 항목 제거
                    for idx, 채널 in enumerate(channels):
                        채널['identifier'] = f'ch{idx + 1}'  # 채널 번호 다시 정렬
                    with open(delays_file_path, "w") as f:
                        delays_data = {f'ch{i+1}': i for i in range(len(channels))}
                        json.dump(delays_data, f, indent=2)
                    print("delays.json 파일이 수정되었습니다.")
                else:
                    print(f"{삭제할_채널_ID} ID를 가진 채널이 존재하지 않습니다.")
            elif 값1 == "4":
                break
            else:
                print("다시 입력해주세요.\n")
                time.sleep(1)

    elif 값 == "2":
        print("test")
    elif 값 == "3":
        print("test")
    elif 값 == "4":
        print("설정을 마침니다.")
        break
    else:
        print("다시 입력해주세요.\n")
        time.sleep(1)

