DEFAULT_LANGUAGE = "ko"

SUPPORTED_LANGUAGES = {
    "ko": "한국어",
    "en": "English",
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
    "ja": "日本語",
}

LANGUAGE_ALIASES = {
    "kr": "ko",
    "kor": "ko",
    "korean": "ko",
    "한국어": "ko",
    "en-us": "en",
    "en_us": "en",
    "english": "en",
    "zh": "zh-CN",
    "zh-cn": "zh-CN",
    "zh_cn": "zh-CN",
    "zh-hans": "zh-CN",
    "zh_hans": "zh-CN",
    "cn": "zh-CN",
    "simplified": "zh-CN",
    "简体中文": "zh-CN",
    "zh-tw": "zh-TW",
    "zh_tw": "zh-TW",
    "zh-hant": "zh-TW",
    "zh_hant": "zh-TW",
    "traditional": "zh-TW",
    "繁體中文": "zh-TW",
    "ja-jp": "ja",
    "ja_jp": "ja",
    "japanese": "ja",
    "日本語": "ja",
}


TRANSLATIONS = {
    "ko": {
        "common.enabled": "활성화",
        "common.disabled": "비활성화",
        "common.enabled_bracket": "[활성화]",
        "common.disabled_bracket": "[비활성화]",
        "common.on": "켜짐",
        "common.off": "꺼짐",
        "common.unknown": "알 수 없음",
        "common.not_available": "N/A",
        "common.split_disabled": "비활성화",
        "common.split_hours": "{count}시간",
        "common.split_minutes": "{count}분",
        "settings.config_saved": "설정이 config.json에 저장되었습니다.",
        "settings.config_save_error": "설정을 저장하는 중 오류가 발생했습니다: {error}",
        "settings.error_loading_config": (
            "config.json을 불러오는 중 오류가 발생했습니다: {error}. "
            "기본값/마이그레이션을 사용합니다."
        ),
        "settings.corrupt_config_backed_up": (
            "손상된 config.json을 {backup_path}에 보존했습니다."
        ),
        "settings.corrupt_config_backup_error": (
            "손상된 config.json을 백업하지 못해 안전을 위해 종료합니다. "
            "원본은 덮어쓰지 않았습니다: {error}"
        ),
        "settings.config_read_error": (
            "config.json을 읽지 못해 안전을 위해 종료합니다. "
            "파일을 덮어쓰지 않았습니다: {error}"
        ),
        "settings.migrating_old_settings": "이전 설정 파일에서 설정을 마이그레이션합니다...",
        "settings.invalid_channel_skipped": "잘못된 채널 ID를 건너뜁니다: {channel_id}",
        "settings.invalid_channels_reset": (
            "채널 목록 형식이 올바르지 않아 빈 목록으로 초기화합니다."
        ),
        "settings.duplicate_channel_skipped": (
            "중복 채널 ID의 이후 항목을 건너뜁니다: {channel_id}"
        ),
        "settings.try_again": "다시 시도해 주세요.\n",
        "settings.main_title": "치지직 자동 녹화 설정",
        "settings.main_menu": (
            "\n1. 채널 설정"
            "\n2. 녹화 설정"
            "\n3. HEVC 설정 (고효율 비디오 코딩)"
            "\n4. AV1 설정"
            "\n5. 네이버 쿠키 설정 (성인 인증, 멤버십 인증)"
            "\n6. DNS-over-HTTPS 설정"
            "\n7. 로그 켜기/끄기"
            "\n8. 언어 설정"
            "\n9. 종료"
        ),
        "settings.prompt_choice": "실행할 번호를 입력하세요: ",
        "settings.channel_menu": (
            "\n1. 채널 추가"
            "\n2. 채널 삭제"
            "\n3. 채널 녹화 켜기/끄기"
            "\n4. 뒤로 가기"
        ),
        "settings.prompt_channel_id": "추가할 스트리머 채널의 고유 ID를 입력하세요: ",
        "settings.invalid_channel_id": (
            "잘못된 채널 ID입니다. 영문, 숫자, '_' 또는 '-'만 사용할 수 있습니다."
        ),
        "settings.prompt_streamer_name": "스트리머 이름을 입력하세요: ",
        "settings.prompt_output_dir": (
            "저장 경로를 입력하세요. 프로그램과 같은 위치에 저장하려면 이름만 "
            "입력하세요: "
        ),
        "settings.confirm_channel": (
            "id: {channel_id}, 이름: {name}, 저장 경로: {output_dir} "
            "이 정보가 맞습니까? (Y/N): "
        ),
        "settings.channel_added": "채널을 추가하고 설정을 저장했습니다.",
        "settings.reenter": "다시 입력해 주세요.",
        "settings.no_channels_delete": "삭제할 채널이 없습니다.",
        "settings.current_channel_list": "현재 채널 목록:",
        "settings.channel_list_item": "{idx}. id: {channel_id}, 이름: {name}",
        "settings.prompt_delete_channel": "삭제할 채널 번호를 입력하세요: ",
        "settings.deleted_channel": (
            "삭제된 채널: id: {channel_id}, 이름: {name}"
        ),
        "settings.channel_deleted": "채널을 삭제하고 설정을 다시 정렬했습니다.",
        "settings.invalid_channel_number": "잘못된 채널 번호입니다.",
        "settings.invalid_number": "잘못된 입력입니다. 올바른 숫자를 입력하세요.",
        "settings.no_channels_toggle": "켜거나 끌 수 있는 채널이 없습니다.",
        "settings.channel_list_item_status": (
            "{idx}. id: {channel_id}, 이름: {name}, 녹화 상태: {status}"
        ),
        "settings.prompt_toggle_channel": "녹화 상태를 바꿀 채널 번호를 입력하세요: ",
        "settings.channel_status_changed": (
            "{name} 채널의 녹화 상태가 {status}(으)로 변경되었습니다."
        ),
        "settings.recording_menu": (
            "\n1. 녹화 스레드 수 설정"
            "\n2. 방송 재탐색 간격 설정"
            "\n3. 출력 형식 설정"
            "\n4. 녹화 파일 분할 간격 설정"
            "\n5. 뒤로 가기"
        ),
        "settings.current_threads": "현재 녹화 스레드 수는 {count}개입니다.",
        "settings.thread_recommendation": (
            "권장값은 2~4개입니다. 저사양 시스템은 2개, 고사양 시스템은 4개를 "
            "권장합니다."
        ),
        "settings.prompt_threads": "변경할 스레드 수를 입력하세요: ",
        "settings.threads_changed": "스레드 수가 변경되었습니다.",
        "settings.invalid_input": "잘못된 입력입니다.",
        "settings.current_timeout": "현재 방송 재탐색 간격은 {seconds}초입니다.",
        "settings.prompt_timeout": "변경할 재탐색 간격을 초 단위로 입력하세요: ",
        "settings.timeout_changed": "방송 재탐색 간격이 변경되었습니다.",
        "settings.current_output_format": "현재 출력 형식은 {format}입니다.",
        "settings.available_formats": "사용 가능한 형식: ts, mkv, webm",
        "settings.prompt_output_format": "변경할 출력 형식을 입력하세요: ",
        "settings.output_format_changed": "출력 형식이 {format}(으)로 변경되었습니다.",
        "settings.current_split": "현재 녹화 파일 분할 간격은 {interval}입니다.",
        "settings.choose_split_unit": "분할 간격 단위를 선택하세요:",
        "settings.unit_hours": "1. 시간",
        "settings.unit_minutes": "2. 분",
        "settings.unit_disable": "3. 분할 녹화 비활성화",
        "settings.prompt_split_hours": "변경할 분할 간격을 시간 단위로 입력하세요: ",
        "settings.prompt_split_minutes": "변경할 분할 간격을 분 단위로 입력하세요: ",
        "settings.split_disabled": "분할 녹화가 비활성화되었습니다.",
        "settings.split_changed": "녹화 파일 분할 간격이 {interval}(으)로 변경되었습니다.",
        "settings.codec_title": "--- {codec} 설정 ---",
        "settings.status": "상태: {status}",
        "settings.encoder": "인코더: {encoder}",
        "settings.target_bitrate": "목표 비트레이트: {bitrate}",
        "settings.max_bitrate": "최대 비트레이트: {bitrate}",
        "settings.preset": "프리셋: {preset}",
        "settings.hevc_menu": (
            "1. 활성화/비활성화 전환"
            "\n2. 인코더 설정 (libx265, hevc_nvenc, hevc_qsv 등)"
            "\n3. 목표 비트레이트 설정 (예: 6000k)"
            "\n4. 최대 비트레이트 설정 (예: 8000k)"
            "\n5. 프리셋 설정 (ultrafast, superfast 등)"
            "\n6. 뒤로 가기"
        ),
        "settings.av1_menu": (
            "1. 활성화/비활성화 전환"
            "\n2. 인코더 설정 (libsvtav1, libaom-av1, av1_nvenc 등)"
            "\n3. 목표 비트레이트 설정 (예: 6000k)"
            "\n4. 최대 비트레이트 설정 (예: 8000k)"
            "\n5. 프리셋 설정 (libsvtav1/libaom-av1: 0-13, NVENC: p1-p7)"
            "\n6. 뒤로 가기"
        ),
        "settings.encoding_toggled": "{codec} 인코딩이 {state}되었습니다.",
        "settings.available_encoders": "\n사용 가능한 인코더:",
        "settings.prompt_encoder": "인코더 이름을 입력하세요: ",
        "settings.invalid_encoder": "잘못된 인코더 이름입니다.",
        "settings.prompt_target_bitrate": "목표 비트레이트를 입력하세요 (예: 6000k): ",
        "settings.prompt_max_bitrate": "최대 비트레이트를 입력하세요 (예: 10000k): ",
        "settings.hevc_preset_options": (
            "옵션: ultrafast(권장), superfast, veryfast, faster, fast, medium"
        ),
        "settings.hevc_preset_note": (
            "참고: NVENC는 p1-p7을 사용하세요. QSV는 veryfast-veryslow를 "
            "사용하세요."
        ),
        "settings.prompt_preset": "프리셋 이름을 입력하세요: ",
        "settings.invalid_preset": "잘못된 프리셋 이름입니다.",
        "settings.prompt_ses": "SES를 입력하세요: ",
        "settings.prompt_aut": "AUT를 입력하세요: ",
        "settings.cookies_saved": "쿠키 정보가 저장되었습니다.",
        "settings.cookie_title": "--- 쿠키 설정 ---",
        "settings.cookie_status": "인증 쿠키 저장 상태: {status}",
        "settings.cookie_menu": (
            "1. 브라우저 로그인으로 가져오기"
            "\n2. 직접 입력"
            "\n3. 저장된 쿠키 삭제"
            "\n4. 뒤로 가기"
        ),
        "settings.browser_menu": (
            "\n1. Chrome"
            "\n2. Microsoft Edge"
            "\n3. Firefox"
            "\n4. 뒤로 가기"
        ),
        "settings.browser_login_notice": (
            "{browser} 새 창을 엽니다. 새 창에서 NAVER 계정에 직접 로그인하세요. "
            "이 프로그램은 아이디나 비밀번호를 입력받지 않습니다."
        ),
        "settings.browser_login_wait": (
            "브라우저에서 로그인을 완료한 뒤 여기로 돌아와 Enter를 누르세요: "
        ),
        "settings.browser_cookies_missing": (
            "브라우저에서 다음 인증 쿠키를 찾지 못했습니다: {cookies}. "
            "NAVER 로그인을 완료했는지 확인하세요."
        ),
        "settings.browser_cookies_saved": (
            "브라우저의 NID_AUT 및 NID_SES 쿠키를 저장했습니다."
        ),
        "settings.browser_login_error": (
            "브라우저 로그인을 시작하거나 쿠키를 가져오지 못했습니다: {error}"
        ),
        "settings.cookies_deleted": "저장된 인증 쿠키를 삭제했습니다.",
        "settings.dns_title": "--- DNS-over-HTTPS 설정 ---",
        "settings.doh_url": "DoH URL: {url}",
        "settings.dns_menu": (
            "1. 활성화/비활성화 전환"
            "\n2. DNS-over-HTTPS URL 설정"
            "\n3. 기본 URL로 초기화"
            "\n4. 뒤로 가기"
        ),
        "settings.dns_toggled": "DNS-over-HTTPS가 {state}되었습니다.",
        "settings.prompt_doh_url": "DNS-over-HTTPS URL을 입력하세요: ",
        "settings.doh_url_changed": "DNS-over-HTTPS URL이 {url}(으)로 변경되었습니다.",
        "settings.doh_url_reset": "DNS-over-HTTPS URL이 {url}(으)로 초기화되었습니다.",
        "settings.logging_toggled": "로그 기록이 {state}되었습니다.",
        "settings.language_title": "--- 언어 설정 ---",
        "settings.current_language": "현재 언어: {language}",
        "settings.prompt_language": "변경할 언어 번호 또는 언어 코드를 입력하세요: ",
        "settings.language_changed": "언어가 {language}(으)로 변경되었습니다.",
        "settings.invalid_language": "지원하지 않는 언어입니다.",
        "settings.exiting": "설정을 종료합니다.",
        "record.logging_toggled": "로그 기록이 {state}되었습니다.",
        "record.logging_toggle_error": "로그 설정을 변경하는 중 오류가 발생했습니다: {error}",
        "record.doh_using": "DNS-over-HTTPS 해석기를 사용합니다: {url}",
        "record.doh_install_failed": "DNS-over-HTTPS 해석기를 설치하지 못했습니다: {error}",
        "record.startup_banner": (
            "Chzzk Rekoda made by munsy0227\n"
            "버그나 에러가 발생하면 GitHub Issues에 제보해 주세요!"
        ),
        "record.unknown_hevc_encoder": (
            "알 수 없는 HEVC 인코더 '{encoder}'입니다. libx265로 대체합니다."
        ),
        "record.unknown_av1_encoder": (
            "알 수 없는 AV1 인코더 '{encoder}'입니다. libsvtav1로 대체합니다."
        ),
        "record.skip_invalid_channel_entry": (
            "{index}번째 잘못된 채널 항목을 건너뜁니다."
        ),
        "record.skip_invalid_channel_id": (
            "잘못된 ID를 가진 채널을 건너뜁니다: {channel_id!r}"
        ),
        "record.process_timeout_kill": (
            "{name}이(가) 제시간에 종료되지 않아 강제 종료합니다."
        ),
        "record.task_timeout": (
            "{name}이(가) {timeout:.0f}초 안에 종료되지 않았습니다."
        ),
        "record.pipe_closed": (
            "{channel_name}의 스트림을 전달하는 중 ffmpeg stdin이 닫혔습니다."
        ),
        "record.pipe_error": (
            "{channel_name}의 스트림을 ffmpeg로 전달하는 중 오류가 발생했습니다: "
            "{error}"
        ),
        "record.running_windows": "Windows에서 실행 중입니다.",
        "record.using_bundled_ffmpeg": "내장 ffmpeg를 사용합니다: {path}",
        "record.using_path_ffmpeg": "PATH의 ffmpeg를 사용합니다: {path}",
        "record.ffmpeg_not_found_windows": (
            "ffmpeg를 찾을 수 없습니다. install.bat을 실행하거나 ffmpeg를 "
            "PATH에 추가하세요."
        ),
        "record.running_os_ffmpeg_found": "{os_name}에서 실행 중입니다. ffmpeg 위치: {path}",
        "record.ffmpeg_not_found_path": "시스템 PATH에서 ffmpeg를 찾을 수 없습니다.",
        "record.json_decode_error": "{file_path}의 JSON 디코드 오류: {error}",
        "record.json_load_error": "{file_path}에서 JSON을 불러오는 중 오류: {error}",
        "record.channel_not_live": "'{channel_name}' 채널은 현재 방송 중이 아닙니다.",
        "record.channel_blocked": "'{channel_name}' 채널은 차단되어 있습니다.",
        "record.member_only_cookies_required": (
            "'{channel_name}' 채널은 멤버십 전용 방송입니다. 네이버플러스 멤버십 "
            "또는 치트키 구독 계정의 NID_AUT와 NID_SES 쿠키 값을 모두 지정해야 "
            "녹화할 수 있습니다."
        ),
        "record.member_only_access_required": (
            "'{channel_name}' 채널의 멤버십 재생 권한을 확인할 수 없습니다. "
            "네이버플러스 멤버십 또는 치트키 구독 계정의 올바른 NID_AUT와 "
            "NID_SES 쿠키 값인지 확인하세요."
        ),
        "record.http_live_info_error": (
            "{channel_name}의 라이브 정보를 가져오는 중 HTTP 오류가 발생했습니다: "
            "{error}"
        ),
        "record.live_info_failed": (
            "{channel_name}의 라이브 정보를 가져오지 못했습니다: {error}"
        ),
        "record.filename_too_long": (
            "파일 이름 '{filename}'이 너무 깁니다. '{shortened}'(으)로 줄입니다."
        ),
        "record.segment_template_too_long": (
            "분할 파일 이름 템플릿 {filename!r}이 너무 깁니다. "
            "{shortened!r}(으)로 줄입니다."
        ),
        "record.read_stream_error": (
            "{channel_id}의 스트림을 읽는 중 오류가 발생했습니다: {error}"
        ),
        "record.av1_unusable": (
            "현재 FFmpeg/하드웨어 환경에서 AV1 인코더 '{encoder}'를 사용할 수 "
            "없습니다: {message}"
        ),
        "record.av1_fallback": (
            "이번 녹화에서 AV1 인코더 '{selected}' 대신 '{fallback}'을 "
            "사용합니다."
        ),
        "record.av1_fallback_unusable": (
            "AV1 대체 인코더 '{encoder}'를 사용할 수 없습니다: {message}"
        ),
        "record.av1_no_encoder": (
            "사용 가능한 AV1 인코더가 없습니다. AV1 인코딩 없이 녹화합니다."
        ),
        "record.hevc_unusable": (
            "현재 FFmpeg/하드웨어 환경에서 HEVC 인코더 '{encoder}'를 사용할 수 "
            "없습니다: {message}"
        ),
        "record.hevc_fallback": (
            "이번 녹화에서 HEVC 인코더 '{selected}' 대신 '{fallback}'을 "
            "사용합니다."
        ),
        "record.hevc_fallback_unusable": (
            "HEVC 대체 인코더 '{encoder}'를 사용할 수 없습니다: {message}"
        ),
        "record.hevc_no_encoder": (
            "사용 가능한 HEVC 인코더가 없습니다. HEVC 인코딩 없이 녹화합니다."
        ),
        "record.attempting_channel": "{channel_name} 채널 녹화를 시도합니다.",
        "record.channel_inactive": "{channel_name} 채널은 비활성 상태입니다. 녹화를 건너뜁니다.",
        "record.waiting_live": "'{channel_name}' 채널의 방송 시작을 기다리는 중입니다...",
        "record.av1_ts_fallback": (
            "{channel_name}에서는 AV1 출력을 TS 형식으로 저장할 수 없습니다. "
            "MKV로 대체합니다."
        ),
        "record.split_enabled": (
            "{channel_name} 분할 녹화가 활성화되었습니다: {interval}마다 새 "
            "파일을 만듭니다."
        ),
        "record.hevc_ignored_webm": (
            "{channel_name}의 WebM 출력에서는 HEVC 설정이 무시됩니다."
        ),
        "record.recording_started": (
            "{channel_name} 녹화를 {current_time}에 시작했습니다."
        ),
        "record.ffmpeg_exited": (
            "{channel_name}의 ffmpeg 프로세스가 반환 코드 {returncode}(으)로 "
            "종료되었습니다."
        ),
        "record.stream_process_exited": (
            "{channel_name}의 스트림 녹화 프로세스가 반환 코드 {returncode}(으)로 "
            "종료되었습니다."
        ),
        "record.ffmpeg_failed": (
            "{channel_name}의 ffmpeg가 실패했습니다. 원인은 위의 ffmpeg stderr "
            "줄을 확인하세요."
        ),
        "record.streamlink_failed": (
            "{channel_name}의 streamlink가 실패했습니다. 원인은 위의 streamlink "
            "stderr 줄을 확인하세요."
        ),
        "record.recording_stopped": "{channel_name} 녹화가 중지되었습니다.",
        "record.empty_segment_discarded": (
            "{channel_name}의 빈 녹화 세그먼트를 삭제했습니다: {path}"
        ),
        "record.no_segments": "{channel_name}의 녹화 세그먼트 파일이 생성되지 않았습니다.",
        "record.split_left_incomplete": (
            "ffmpeg가 반환 코드 {returncode}(으)로 종료되어 분할 녹화 파일을 "
            "{output_dir}에 남겨 두었습니다. 마지막 세그먼트는 불완전할 수 "
            "있습니다."
        ),
        "record.segment_saved": "녹화 세그먼트를 저장했습니다: {path}",
        "record.empty_file_discarded": "{channel_name}의 빈 녹화 파일을 삭제했습니다.",
        "record.incomplete_file_left": (
            "ffmpeg가 반환 코드 {returncode}(으)로 종료되어 불완전한 녹화 파일을 "
            "{path}에 남겨 두었습니다."
        ),
        "record.saved": "녹화 파일을 저장했습니다: {path}",
        "record.task_cancelled": "{channel_name} 녹화 작업이 취소되었습니다.",
        "record.recording_error": "{channel_name} 녹화 중 오류가 발생했습니다: {error}",
        "record.no_stream_url": "{channel_name}에 사용할 스트림 URL이 없습니다.",
        "record.unfinished_file_left": "완료되지 않은 녹화 파일을 남겨 두었습니다: {path}",
        "record.ffmpeg_executable_missing": "ffmpeg 실행 파일을 찾을 수 없습니다. 종료합니다.",
        "record.cancelled_deactivated_id": (
            "비활성화된 채널의 녹화 작업을 취소했습니다: {channel_id}"
        ),
        "record.channel_id_missing": "설정에 채널 ID가 없습니다.",
        "record.started_new_active_channel": (
            "새 활성 채널의 녹화 작업을 시작했습니다: {channel_name}"
        ),
        "record.cancelled_deactivated_name": (
            "비활성화된 채널의 녹화 작업을 취소했습니다: {channel_name}"
        ),
        "record.all_inactive": "모든 채널이 비활성 상태입니다. 진행 중인 녹화가 없습니다.",
        "record.management_cancelled": "녹화 관리 작업이 취소되었습니다.",
        "record.shutdown_wait_timeout": (
            "녹화 작업 종료를 기다리는 시간이 초과되었습니다. 남은 작업을 "
            "취소합니다."
        ),
        "record.shutdown_signal": "종료 신호를 받았습니다. 종료 중입니다...",
        "record.no_active_recordings": "진행 중인 녹화가 없습니다.",
        "record.progress_title": "녹화 진행 상황",
        "record.logs_title": "로그",
        "record.table_channel": "채널",
        "record.table_bitrate": "비트레이트",
        "record.table_download_speed": "다운로드 속도",
        "record.table_total_size": "전체 크기",
        "record.table_out_time": "출력 시간",
        "record.table_start_time": "시작 시간",
        "record.keyboard_interrupt": "KeyboardInterrupt를 받았습니다. 종료 중입니다...",
        "record.main_cancelled": "메인 작업이 취소되었습니다.",
        "record.unhandled_error": "오류가 발생했습니다: {error}",
        "record.shutdown_complete": "녹화 프로그램이 종료되었습니다.",
    },
    "en": {
        "common.enabled": "enabled",
        "common.disabled": "disabled",
        "common.enabled_bracket": "[Enabled]",
        "common.disabled_bracket": "[Disabled]",
        "common.on": "On",
        "common.off": "Off",
        "common.unknown": "Unknown",
        "common.not_available": "N/A",
        "common.split_disabled": "disabled",
        "common.split_hours": "{count} hour(s)",
        "common.split_minutes": "{count} minute(s)",
        "settings.main_title": "Chzzk Auto-Recording Settings",
        "settings.main_menu": (
            "\n1. Channel Settings"
            "\n2. Recording Settings"
            "\n3. HEVC Settings (High Efficiency Video Coding)"
            "\n4. AV1 Settings"
            "\n5. NAVER Cookie Settings (adult and membership verification)"
            "\n6. DNS-over-HTTPS Settings"
            "\n7. Toggle Logging"
            "\n8. Language Settings"
            "\n9. Quit"
        ),
        "settings.prompt_choice": "Enter the number you want to execute: ",
        "settings.language_title": "--- Language Settings ---",
        "settings.current_language": "Current language: {language}",
        "settings.prompt_language": "Enter a language number or language code: ",
        "settings.language_changed": "Language has been changed to {language}.",
        "settings.invalid_language": "Unsupported language.",
    },
    "zh-CN": {
        "common.enabled": "启用",
        "common.disabled": "禁用",
        "common.enabled_bracket": "[已启用]",
        "common.disabled_bracket": "[已禁用]",
        "common.on": "开",
        "common.off": "关",
        "common.unknown": "未知",
        "common.not_available": "N/A",
        "common.split_disabled": "已禁用",
        "common.split_hours": "{count} 小时",
        "common.split_minutes": "{count} 分钟",
        "settings.main_title": "CHZZK 自动录制设置",
        "settings.main_menu": (
            "\n1. 频道设置"
            "\n2. 录制设置"
            "\n3. HEVC 设置（高效率视频编码）"
            "\n4. AV1 设置"
            "\n5. NAVER Cookie 设置（成人认证、会员认证）"
            "\n6. DNS-over-HTTPS 设置"
            "\n7. 开启/关闭日志"
            "\n8. 语言设置"
            "\n9. 退出"
        ),
        "settings.prompt_choice": "请输入要执行的编号：",
        "settings.language_title": "--- 语言设置 ---",
        "settings.current_language": "当前语言：{language}",
        "settings.prompt_language": "请输入语言编号或语言代码：",
        "settings.language_changed": "语言已更改为 {language}。",
        "settings.invalid_language": "不支持的语言。",
    },
    "zh-TW": {
        "common.enabled": "啟用",
        "common.disabled": "停用",
        "common.enabled_bracket": "[已啟用]",
        "common.disabled_bracket": "[已停用]",
        "common.on": "開啟",
        "common.off": "關閉",
        "common.unknown": "未知",
        "common.not_available": "N/A",
        "common.split_disabled": "已停用",
        "common.split_hours": "{count} 小時",
        "common.split_minutes": "{count} 分鐘",
        "settings.main_title": "CHZZK 自動錄製設定",
        "settings.main_menu": (
            "\n1. 頻道設定"
            "\n2. 錄製設定"
            "\n3. HEVC 設定（高效率視訊編碼）"
            "\n4. AV1 設定"
            "\n5. NAVER Cookie 設定（成人驗證、會員驗證）"
            "\n6. DNS-over-HTTPS 設定"
            "\n7. 開啟/關閉記錄"
            "\n8. 語言設定"
            "\n9. 離開"
        ),
        "settings.prompt_choice": "請輸入要執行的編號：",
        "settings.language_title": "--- 語言設定 ---",
        "settings.current_language": "目前語言：{language}",
        "settings.prompt_language": "請輸入語言編號或語言代碼：",
        "settings.language_changed": "語言已變更為 {language}。",
        "settings.invalid_language": "不支援的語言。",
    },
    "ja": {
        "common.enabled": "有効",
        "common.disabled": "無効",
        "common.enabled_bracket": "[有効]",
        "common.disabled_bracket": "[無効]",
        "common.on": "オン",
        "common.off": "オフ",
        "common.unknown": "不明",
        "common.not_available": "N/A",
        "common.split_disabled": "無効",
        "common.split_hours": "{count}時間",
        "common.split_minutes": "{count}分",
        "settings.main_title": "CHZZK 自動録画設定",
        "settings.main_menu": (
            "\n1. チャンネル設定"
            "\n2. 録画設定"
            "\n3. HEVC 設定（高効率ビデオ符号化）"
            "\n4. AV1 設定"
            "\n5. NAVER Cookie 設定（成人認証・メンバーシップ認証）"
            "\n6. DNS-over-HTTPS 設定"
            "\n7. ログのオン/オフ"
            "\n8. 言語設定"
            "\n9. 終了"
        ),
        "settings.prompt_choice": "実行する番号を入力してください: ",
        "settings.language_title": "--- 言語設定 ---",
        "settings.current_language": "現在の言語: {language}",
        "settings.prompt_language": "言語番号または言語コードを入力してください: ",
        "settings.language_changed": "言語を {language} に変更しました。",
        "settings.invalid_language": "対応していない言語です。",
    },
}


for _language in ("en", "zh-CN", "zh-TW", "ja"):
    for _key, _text in TRANSLATIONS["ko"].items():
        TRANSLATIONS[_language].setdefault(_key, _text)


def normalize_language(value):
    text = str(value or DEFAULT_LANGUAGE).strip()
    if text in SUPPORTED_LANGUAGES:
        return text
    return LANGUAGE_ALIASES.get(text.lower(), DEFAULT_LANGUAGE)


def language_display_name(language):
    language = normalize_language(language)
    return SUPPORTED_LANGUAGES[language]


def translate(locale, key, **kwargs):
    locale = normalize_language(locale)
    text = TRANSLATIONS.get(locale, {}).get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANGUAGE].get(key, key)
    return text.format(**kwargs)


def state_label(language, enabled):
    key = "common.enabled_bracket" if enabled else "common.disabled_bracket"
    return translate(language, key)


def enabled_word(language, enabled):
    key = "common.enabled" if enabled else "common.disabled"
    return translate(language, key)


def on_off_label(language, enabled):
    key = "common.on" if enabled else "common.off"
    return translate(language, key)


def format_split_interval(language, minutes):
    if minutes <= 0:
        return translate(language, "common.split_disabled")
    if minutes % 60 == 0:
        return translate(language, "common.split_hours", count=minutes // 60)
    return translate(language, "common.split_minutes", count=minutes)


def language_options():
    return list(SUPPORTED_LANGUAGES.items())


# Additional runtime translations filled after the base Korean table.
TRANSLATIONS["en"].update({
    "settings.config_saved": "Configuration saved to config.json.",
    "settings.config_save_error": "Error saving configuration: {error}",
    "settings.error_loading_config": "Error loading config.json: {error}. Using defaults/migration.",
    "settings.corrupt_config_backed_up": (
        "Preserved the invalid config.json at {backup_path}."
    ),
    "settings.corrupt_config_backup_error": (
        "Could not back up the invalid config.json, so setup is exiting "
        "without overwriting the original: {error}"
    ),
    "settings.config_read_error": (
        "Could not read config.json, so setup is exiting without "
        "overwriting it: {error}"
    ),
    "settings.migrating_old_settings": "Migrating settings from old files...",
    "settings.invalid_channel_skipped": "Skipping invalid channel ID: {channel_id}",
    "settings.invalid_channels_reset": (
        "The channel list is not valid, so it has been reset to an "
        "empty list."
    ),
    "settings.duplicate_channel_skipped": (
        "Skipping a later entry with the duplicate channel ID: "
        "{channel_id}"
    ),
    "settings.try_again": "Please try again.\n",
    "settings.channel_menu": "\n1. Add Channel\n2. Delete Channel\n3. Toggle Channel Recording\n4. Go Back",
    "settings.prompt_channel_id": "Enter the unique ID of the streamer channel you want to add: ",
    "settings.invalid_channel_id": "Invalid channel ID. Use only letters, numbers, '_' or '-'.",
    "settings.prompt_streamer_name": "Enter the streamer name: ",
    "settings.prompt_output_dir": "Specify the storage path. Type only a folder name to save it next to the program: ",
    "settings.confirm_channel": "id: {channel_id}, name: {name}, storage path: {output_dir} Is this correct? (Y/N): ",
    "settings.channel_added": "Channel added and config saved.",
    "settings.reenter": "Then please enter it again.",
    "settings.no_channels_delete": "No channels to delete.",
    "settings.current_channel_list": "Current channel list:",
    "settings.channel_list_item": "{idx}. id: {channel_id}, name: {name}",
    "settings.prompt_delete_channel": "Enter the number of the channel to delete: ",
    "settings.deleted_channel": "The deleted channel: id: {channel_id}, name: {name}",
    "settings.channel_deleted": "Channel deleted and config re-indexed.",
    "settings.invalid_channel_number": "Invalid channel number.",
    "settings.invalid_number": "Invalid input. Please enter a valid number.",
    "settings.no_channels_toggle": "No channels available to toggle.",
    "settings.channel_list_item_status": "{idx}. id: {channel_id}, name: {name}, recording status: {status}",
    "settings.prompt_toggle_channel": "Enter the number of the channel to toggle recording status: ",
    "settings.channel_status_changed": "The recording status of {name} channel has been changed to {status}.",
    "settings.recording_menu": "\n1. Set Recording Threads\n2. Set Broadcast Rescan Interval\n3. Set Output Format\n4. Set Recording Split Interval\n5. Go Back",
    "settings.current_threads": "The current number of recording threads is {count}.",
    "settings.thread_recommendation": "Recommended 2-4 threads: 2 for low-end systems, 4 for high-end systems.",
    "settings.prompt_threads": "Enter the number of threads to change: ",
    "settings.threads_changed": "The number of threads has been changed.",
    "settings.invalid_input": "Invalid input.",
    "settings.current_timeout": "The current broadcast rescan interval is {seconds} seconds.",
    "settings.prompt_timeout": "Enter the rescan interval to change (in seconds): ",
    "settings.timeout_changed": "The broadcast rescan interval has been changed.",
    "settings.current_output_format": "The current output format is {format}.",
    "settings.available_formats": "Available formats: ts, mkv, webm",
    "settings.prompt_output_format": "Enter the output format to change: ",
    "settings.output_format_changed": "The output format has been changed to {format}.",
    "settings.current_split": "The current recording split interval is {interval}.",
    "settings.choose_split_unit": "Choose split interval unit:",
    "settings.unit_hours": "1. Hours",
    "settings.unit_minutes": "2. Minutes",
    "settings.unit_disable": "3. Disable Split Recording",
    "settings.prompt_split_hours": "Enter the split interval to change (in hours): ",
    "settings.prompt_split_minutes": "Enter the split interval to change (in minutes): ",
    "settings.split_disabled": "Split recording has been disabled.",
    "settings.split_changed": "The recording split interval has been changed to {interval}.",
    "settings.codec_title": "--- {codec} Settings ---",
    "settings.status": "Status: {status}",
    "settings.encoder": "Encoder: {encoder}",
    "settings.target_bitrate": "Target Bitrate: {bitrate}",
    "settings.max_bitrate": "Max Bitrate: {bitrate}",
    "settings.preset": "Preset: {preset}",
    "settings.hevc_menu": "1. Toggle Enable/Disable\n2. Set Encoder (libx265, hevc_nvenc, hevc_qsv, etc.)\n3. Set Target Bitrate (e.g., 6000k)\n4. Set Max Bitrate (e.g., 8000k)\n5. Set Preset (ultrafast, superfast, etc.)\n6. Go Back",
    "settings.av1_menu": "1. Toggle Enable/Disable\n2. Set Encoder (libsvtav1, libaom-av1, av1_nvenc, etc.)\n3. Set Target Bitrate (e.g., 6000k)\n4. Set Max Bitrate (e.g., 8000k)\n5. Set Preset (libsvtav1/libaom-av1: 0-13, NVENC: p1-p7)\n6. Go Back",
    "settings.encoding_toggled": "{codec} encoding has been {state}.",
    "settings.available_encoders": "\nAvailable Encoders:",
    "settings.prompt_encoder": "Enter encoder name: ",
    "settings.invalid_encoder": "Invalid encoder name.",
    "settings.prompt_target_bitrate": "Enter target bitrate (e.g., 6000k): ",
    "settings.prompt_max_bitrate": "Enter max bitrate (e.g., 10000k): ",
    "settings.hevc_preset_options": "Options: ultrafast (rec), superfast, veryfast, faster, fast, medium",
    "settings.hevc_preset_note": "Note: For NVENC, use p1-p7. For QSV, use veryfast-veryslow.",
    "settings.prompt_preset": "Enter preset name: ",
    "settings.invalid_preset": "Invalid preset name.",
    "settings.prompt_ses": "Enter SES: ",
    "settings.prompt_aut": "Enter AUT: ",
    "settings.cookies_saved": "Cookie information has been successfully saved.",
    "settings.cookie_title": "--- Cookie Settings ---",
    "settings.cookie_status": "Authentication cookie status: {status}",
    "settings.cookie_menu": "1. Import via Browser Login\n2. Enter Manually\n3. Delete Saved Cookies\n4. Go Back",
    "settings.browser_menu": "\n1. Chrome\n2. Microsoft Edge\n3. Firefox\n4. Go Back",
    "settings.browser_login_notice": "A new {browser} window will open. Sign in to your NAVER account directly in that window. This program does not collect your ID or password.",
    "settings.browser_login_wait": "After completing the login in the browser, return here and press Enter: ",
    "settings.browser_cookies_missing": "The following authentication cookies were not found in the browser: {cookies}. Make sure you completed the NAVER login.",
    "settings.browser_cookies_saved": "Saved the browser NID_AUT and NID_SES cookies.",
    "settings.browser_login_error": "Could not start the browser login or import cookies: {error}",
    "settings.cookies_deleted": "Deleted the saved authentication cookies.",
    "settings.dns_title": "--- DNS-over-HTTPS Settings ---",
    "settings.doh_url": "DoH URL: {url}",
    "settings.dns_menu": "1. Toggle Enable/Disable\n2. Set DNS-over-HTTPS URL\n3. Reset to Default URL\n4. Go Back",
    "settings.dns_toggled": "DNS-over-HTTPS has been {state}.",
    "settings.prompt_doh_url": "Enter the DNS-over-HTTPS URL: ",
    "settings.doh_url_changed": "DNS-over-HTTPS URL has been changed to {url}.",
    "settings.doh_url_reset": "DNS-over-HTTPS URL has been reset to {url}.",
    "settings.logging_toggled": "Logging has been {state}.",
    "settings.exiting": "Exiting the settings.",
    "record.logging_toggled": "Logging has been {state}.",
    "record.logging_toggle_error": "Error toggling log: {error}",
    "record.doh_using": "Using DNS-over-HTTPS resolver: {url}",
    "record.doh_install_failed": "Failed to install DNS-over-HTTPS resolver: {error}",
    "record.startup_banner": "Chzzk Rekoda made by munsy0227\nIf you encounter any bugs or errors, please report them on GitHub Issues!",
    "record.unknown_hevc_encoder": "Unknown HEVC encoder '{encoder}'. Falling back to libx265.",
    "record.unknown_av1_encoder": "Unknown AV1 encoder '{encoder}'. Falling back to libsvtav1.",
    "record.skip_invalid_channel_entry": "Skipping invalid channel entry at index {index}.",
    "record.skip_invalid_channel_id": "Skipping channel with invalid ID: {channel_id!r}",
    "record.process_timeout_kill": "{name} did not terminate in time. Killing it.",
    "record.task_timeout": "{name} did not exit within {timeout:.0f} seconds.",
    "record.pipe_closed": "ffmpeg stdin closed while piping stream for {channel_name}.",
    "record.pipe_error": "Error piping stream to ffmpeg for {channel_name}: {error}",
    "record.running_windows": "Running on Windows.",
    "record.using_bundled_ffmpeg": "Using bundled ffmpeg at: {path}",
    "record.using_path_ffmpeg": "Using ffmpeg from PATH at: {path}",
    "record.ffmpeg_not_found_windows": "ffmpeg not found. Run install.bat or add ffmpeg to PATH.",
    "record.running_os_ffmpeg_found": "Running on {os_name}. ffmpeg found at: {path}",
    "record.ffmpeg_not_found_path": "ffmpeg not found on the system PATH.",
    "record.json_decode_error": "JSON decode error in {file_path}: {error}",
    "record.json_load_error": "Error loading JSON from {file_path}: {error}",
    "record.channel_not_live": "The channel '{channel_name}' is not currently live.",
    "record.channel_blocked": "The channel '{channel_name}' is blocked.",
    "record.member_only_cookies_required": (
        "'{channel_name}' is a membership-only stream. To record it, set both "
        "NID_AUT and NID_SES cookie values from an account with a Naver Plus "
        "Membership or Cheat Key subscription."
    ),
    "record.member_only_access_required": (
        "Membership playback access could not be verified for '{channel_name}'. "
        "Check that NID_AUT and NID_SES are valid for an account with a Naver "
        "Plus Membership or Cheat Key subscription."
    ),
    "record.http_live_info_error": "HTTP error occurred while fetching live info for {channel_name}: {error}",
    "record.live_info_failed": "Failed to fetch live info for {channel_name}: {error}",
    "record.filename_too_long": "Filename '{filename}' is too long. Shortening to '{shortened}'.",
    "record.segment_template_too_long": "Segment filename template {filename!r} is too long. Shortening to {shortened!r}.",
    "record.read_stream_error": "Error occurred while reading stream for {channel_id}: {error}",
    "record.av1_unusable": "AV1 encoder '{encoder}' is not usable with the current FFmpeg/hardware setup: {message}",
    "record.av1_fallback": "Using AV1 encoder '{fallback}' instead of '{selected}' for this recording.",
    "record.av1_fallback_unusable": "AV1 fallback encoder '{encoder}' is not usable: {message}",
    "record.av1_no_encoder": "No usable AV1 encoder found. Recording without AV1 encoding.",
    "record.hevc_unusable": "HEVC encoder '{encoder}' is not usable with the current FFmpeg/hardware setup: {message}",
    "record.hevc_fallback": "Using HEVC encoder '{fallback}' instead of '{selected}' for this recording.",
    "record.hevc_fallback_unusable": "HEVC fallback encoder '{encoder}' is not usable: {message}",
    "record.hevc_no_encoder": "No usable HEVC encoder found. Recording without HEVC encoding.",
    "record.attempting_channel": "Attempting to record stream for channel: {channel_name}",
    "record.channel_inactive": "{channel_name} channel is inactive. Skipping recording.",
    "record.waiting_live": "Waiting for the channel '{channel_name}' to go live...",
    "record.av1_ts_fallback": "AV1 output is not supported with TS for {channel_name}. Falling back to MKV.",
    "record.split_enabled": "Split recording enabled for {channel_name}: new file every {interval}.",
    "record.hevc_ignored_webm": "HEVC settings are ignored for WebM output on {channel_name}.",
    "record.recording_started": "Recording started for {channel_name} at {current_time}.",
    "record.ffmpeg_exited": "ffmpeg process for {channel_name} exited with return code {returncode}.",
    "record.stream_process_exited": "Stream recording process for {channel_name} exited with return code {returncode}.",
    "record.ffmpeg_failed": "ffmpeg failed for {channel_name}; see the ffmpeg stderr lines above for the root cause.",
    "record.streamlink_failed": "streamlink failed for {channel_name}; see the streamlink stderr lines above for the root cause.",
    "record.recording_stopped": "Recording stopped for {channel_name}.",
    "record.empty_segment_discarded": "Discarded empty recording segment for {channel_name}: {path}",
    "record.no_segments": "No recording segment files were created for {channel_name}.",
    "record.split_left_incomplete": "Split recording files were left at {output_dir} because ffmpeg exited with return code {returncode}. The last segment may be incomplete.",
    "record.segment_saved": "Recording segment saved to {path}",
    "record.empty_file_discarded": "Discarded empty recording file for {channel_name}.",
    "record.incomplete_file_left": "Leaving incomplete recording file at {path} because ffmpeg exited with return code {returncode}.",
    "record.saved": "Recording saved to {path}",
    "record.task_cancelled": "Recording task for {channel_name} was cancelled.",
    "record.recording_error": "Error occurred while recording {channel_name}: {error}",
    "record.no_stream_url": "No stream URL available for {channel_name}",
    "record.unfinished_file_left": "Leaving unfinished recording file at {path}.",
    "record.ffmpeg_executable_missing": "ffmpeg executable not found. Exiting.",
    "record.cancelled_deactivated_id": "Cancelled recording task for deactivated channel: {channel_id}",
    "record.channel_id_missing": "Channel ID is missing in configuration.",
    "record.started_new_active_channel": "Started recording task for new active channel: {channel_name}",
    "record.cancelled_deactivated_name": "Cancelled recording task for deactivated channel: {channel_name}",
    "record.all_inactive": "All channels are inactive. No active recordings.",
    "record.management_cancelled": "Recording management task was cancelled.",
    "record.shutdown_wait_timeout": "Timed out waiting for recording tasks to finalize. Cancelling remaining tasks.",
    "record.shutdown_signal": "Received shutdown signal. Shutting down...",
    "record.no_active_recordings": "No active recordings.",
    "record.progress_title": "Recording Progress",
    "record.logs_title": "Logs",
    "record.table_channel": "Channel",
    "record.table_bitrate": "Bitrate",
    "record.table_download_speed": "Download Speed",
    "record.table_total_size": "Total Size",
    "record.table_out_time": "Out Time",
    "record.table_start_time": "Start Time",
    "record.keyboard_interrupt": "Received KeyboardInterrupt. Shutting down...",
    "record.main_cancelled": "Main task was cancelled.",
    "record.unhandled_error": "An error occurred: {error}",
    "record.shutdown_complete": "Recorder has been shut down.",
})

TRANSLATIONS["zh-CN"].update({
    "settings.config_saved": "设置已保存到 config.json。",
    "settings.config_save_error": "保存设置时出错：{error}",
    "settings.error_loading_config": "加载 config.json 时出错：{error}。将使用默认值/迁移。",
    "settings.corrupt_config_backed_up": (
        "已将损坏的 config.json 保存在 {backup_path}。"
    ),
    "settings.corrupt_config_backup_error": (
        "无法备份损坏的 config.json。为避免覆盖原文件，"
        "设置程序将安全退出：{error}"
    ),
    "settings.config_read_error": (
        "无法读取 config.json。为避免覆盖该文件，设置程序将安全退出：{error}"
    ),
    "settings.migrating_old_settings": "正在从旧文件迁移设置...",
    "settings.invalid_channel_skipped": "跳过无效的频道 ID：{channel_id}",
    "settings.invalid_channels_reset": (
        "频道列表格式无效，已重置为空列表。"
    ),
    "settings.duplicate_channel_skipped": (
        "跳过频道 ID 重复的后续项目：{channel_id}"
    ),
    "settings.try_again": "请重试。\n",
    "settings.channel_menu": "\n1. 添加频道\n2. 删除频道\n3. 开启/关闭频道录制\n4. 返回",
    "settings.prompt_channel_id": "请输入要添加的主播频道唯一 ID：",
    "settings.invalid_channel_id": "频道 ID 无效。只能使用英文字母、数字、'_' 或 '-'。",
    "settings.prompt_streamer_name": "请输入主播名称：",
    "settings.prompt_output_dir": "请输入保存路径。若要保存在程序同一位置，只输入文件夹名即可：",
    "settings.confirm_channel": "id：{channel_id}，名称：{name}，保存路径：{output_dir}。这些信息正确吗？(Y/N)：",
    "settings.channel_added": "频道已添加，设置已保存。",
    "settings.reenter": "请重新输入。",
    "settings.no_channels_delete": "没有可删除的频道。",
    "settings.current_channel_list": "当前频道列表：",
    "settings.channel_list_item": "{idx}. id：{channel_id}，名称：{name}",
    "settings.prompt_delete_channel": "请输入要删除的频道编号：",
    "settings.deleted_channel": "已删除的频道：id：{channel_id}，名称：{name}",
    "settings.channel_deleted": "频道已删除，设置已重新编号。",
    "settings.invalid_channel_number": "频道编号无效。",
    "settings.invalid_number": "输入无效。请输入有效数字。",
    "settings.no_channels_toggle": "没有可切换的频道。",
    "settings.channel_list_item_status": "{idx}. id：{channel_id}，名称：{name}，录制状态：{status}",
    "settings.prompt_toggle_channel": "请输入要切换录制状态的频道编号：",
    "settings.channel_status_changed": "{name} 频道的录制状态已更改为 {status}。",
    "settings.recording_menu": "\n1. 设置录制线程数\n2. 设置直播重新扫描间隔\n3. 设置输出格式\n4. 设置录制文件分段间隔\n5. 返回",
    "settings.current_threads": "当前录制线程数为 {count}。",
    "settings.thread_recommendation": "建议使用 2-4 个线程：低配置系统建议 2 个，高配置系统建议 4 个。",
    "settings.prompt_threads": "请输入要更改的线程数：",
    "settings.threads_changed": "线程数已更改。",
    "settings.invalid_input": "输入无效。",
    "settings.current_timeout": "当前直播重新扫描间隔为 {seconds} 秒。",
    "settings.prompt_timeout": "请输入要更改的重新扫描间隔（秒）：",
    "settings.timeout_changed": "直播重新扫描间隔已更改。",
    "settings.current_output_format": "当前输出格式为 {format}。",
    "settings.available_formats": "可用格式：ts、mkv、webm",
    "settings.prompt_output_format": "请输入要更改的输出格式：",
    "settings.output_format_changed": "输出格式已更改为 {format}。",
    "settings.current_split": "当前录制文件分段间隔为 {interval}。",
    "settings.choose_split_unit": "请选择分段间隔单位：",
    "settings.unit_hours": "1. 小时",
    "settings.unit_minutes": "2. 分钟",
    "settings.unit_disable": "3. 禁用分段录制",
    "settings.prompt_split_hours": "请输入要更改的分段间隔（小时）：",
    "settings.prompt_split_minutes": "请输入要更改的分段间隔（分钟）：",
    "settings.split_disabled": "分段录制已禁用。",
    "settings.split_changed": "录制文件分段间隔已更改为 {interval}。",
    "settings.codec_title": "--- {codec} 设置 ---",
    "settings.status": "状态：{status}",
    "settings.encoder": "编码器：{encoder}",
    "settings.target_bitrate": "目标码率：{bitrate}",
    "settings.max_bitrate": "最大码率：{bitrate}",
    "settings.preset": "预设：{preset}",
    "settings.hevc_menu": "1. 切换启用/禁用\n2. 设置编码器（libx265、hevc_nvenc、hevc_qsv 等）\n3. 设置目标码率（例如 6000k）\n4. 设置最大码率（例如 8000k）\n5. 设置预设（ultrafast、superfast 等）\n6. 返回",
    "settings.av1_menu": "1. 切换启用/禁用\n2. 设置编码器（libsvtav1、libaom-av1、av1_nvenc 等）\n3. 设置目标码率（例如 6000k）\n4. 设置最大码率（例如 8000k）\n5. 设置预设（libsvtav1/libaom-av1：0-13，NVENC：p1-p7）\n6. 返回",
    "settings.encoding_toggled": "{codec} 编码已{state}。",
    "settings.available_encoders": "\n可用编码器：",
    "settings.prompt_encoder": "请输入编码器名称：",
    "settings.invalid_encoder": "编码器名称无效。",
    "settings.prompt_target_bitrate": "请输入目标码率（例如 6000k）：",
    "settings.prompt_max_bitrate": "请输入最大码率（例如 10000k）：",
    "settings.hevc_preset_options": "选项：ultrafast（推荐）、superfast、veryfast、faster、fast、medium",
    "settings.hevc_preset_note": "注意：NVENC 请使用 p1-p7。QSV 请使用 veryfast-veryslow。",
    "settings.prompt_preset": "请输入预设名称：",
    "settings.invalid_preset": "预设名称无效。",
    "settings.prompt_ses": "请输入 SES：",
    "settings.prompt_aut": "请输入 AUT：",
    "settings.cookies_saved": "Cookie 信息已成功保存。",
    "settings.cookie_title": "--- Cookie 设置 ---",
    "settings.cookie_status": "身份验证 Cookie 保存状态：{status}",
    "settings.cookie_menu": "1. 通过浏览器登录导入\n2. 手动输入\n3. 删除已保存的 Cookie\n4. 返回",
    "settings.browser_menu": "\n1. Chrome\n2. Microsoft Edge\n3. Firefox\n4. 返回",
    "settings.browser_login_notice": "将打开新的 {browser} 窗口。请直接在该窗口中登录 NAVER 账号。本程序不会收集您的账号或密码。",
    "settings.browser_login_wait": "在浏览器中完成登录后，请返回此处并按 Enter：",
    "settings.browser_cookies_missing": "在浏览器中找不到以下身份验证 Cookie：{cookies}。请确认已完成 NAVER 登录。",
    "settings.browser_cookies_saved": "已保存浏览器中的 NID_AUT 和 NID_SES Cookie。",
    "settings.browser_login_error": "无法启动浏览器登录或导入 Cookie：{error}",
    "settings.cookies_deleted": "已删除保存的身份验证 Cookie。",
    "settings.dns_title": "--- DNS-over-HTTPS 设置 ---",
    "settings.doh_url": "DoH URL：{url}",
    "settings.dns_menu": "1. 切换启用/禁用\n2. 设置 DNS-over-HTTPS URL\n3. 重置为默认 URL\n4. 返回",
    "settings.dns_toggled": "DNS-over-HTTPS 已{state}。",
    "settings.prompt_doh_url": "请输入 DNS-over-HTTPS URL：",
    "settings.doh_url_changed": "DNS-over-HTTPS URL 已更改为 {url}。",
    "settings.doh_url_reset": "DNS-over-HTTPS URL 已重置为 {url}。",
    "settings.logging_toggled": "日志已{state}。",
    "settings.exiting": "正在退出设置。",
    "record.startup_banner": "Chzzk Rekoda made by munsy0227\n如果遇到 bug 或错误，请在 GitHub Issues 中反馈！",
    "record.no_active_recordings": "没有正在进行的录制。",
    "record.progress_title": "录制进度",
    "record.logs_title": "日志",
    "record.table_channel": "频道",
    "record.table_bitrate": "码率",
    "record.table_download_speed": "下载速度",
    "record.table_total_size": "总大小",
    "record.table_out_time": "输出时间",
    "record.table_start_time": "开始时间",
})

TRANSLATIONS["zh-TW"].update({
    "settings.config_saved": "設定已儲存到 config.json。",
    "settings.config_save_error": "儲存設定時發生錯誤：{error}",
    "settings.error_loading_config": "載入 config.json 時發生錯誤：{error}。將使用預設值/遷移。",
    "settings.corrupt_config_backed_up": (
        "已將損壞的 config.json 保存在 {backup_path}。"
    ),
    "settings.corrupt_config_backup_error": (
        "無法備份損壞的 config.json。為避免覆寫原始檔案，"
        "設定程式將安全結束：{error}"
    ),
    "settings.config_read_error": (
        "無法讀取 config.json。為避免覆寫該檔案，設定程式將安全結束：{error}"
    ),
    "settings.migrating_old_settings": "正在從舊檔案遷移設定...",
    "settings.invalid_channel_skipped": "略過無效的頻道 ID：{channel_id}",
    "settings.invalid_channels_reset": (
        "頻道清單格式無效，已重設為空白清單。"
    ),
    "settings.duplicate_channel_skipped": (
        "略過頻道 ID 重複的後續項目：{channel_id}"
    ),
    "settings.try_again": "請再試一次。\n",
    "settings.channel_menu": "\n1. 新增頻道\n2. 刪除頻道\n3. 開啟/關閉頻道錄製\n4. 返回",
    "settings.prompt_channel_id": "請輸入要新增的實況主頻道唯一 ID：",
    "settings.invalid_channel_id": "頻道 ID 無效。只能使用英文字母、數字、'_' 或 '-'。",
    "settings.prompt_streamer_name": "請輸入實況主名稱：",
    "settings.prompt_output_dir": "請輸入儲存路徑。若要儲存在程式同一位置，只輸入資料夾名稱即可：",
    "settings.confirm_channel": "id：{channel_id}，名稱：{name}，儲存路徑：{output_dir}。這些資訊正確嗎？(Y/N)：",
    "settings.channel_added": "頻道已新增，設定已儲存。",
    "settings.reenter": "請重新輸入。",
    "settings.no_channels_delete": "沒有可刪除的頻道。",
    "settings.current_channel_list": "目前頻道清單：",
    "settings.channel_list_item": "{idx}. id：{channel_id}，名稱：{name}",
    "settings.prompt_delete_channel": "請輸入要刪除的頻道編號：",
    "settings.deleted_channel": "已刪除的頻道：id：{channel_id}，名稱：{name}",
    "settings.channel_deleted": "頻道已刪除，設定已重新編號。",
    "settings.invalid_channel_number": "頻道編號無效。",
    "settings.invalid_number": "輸入無效。請輸入有效數字。",
    "settings.no_channels_toggle": "沒有可切換的頻道。",
    "settings.channel_list_item_status": "{idx}. id：{channel_id}，名稱：{name}，錄製狀態：{status}",
    "settings.prompt_toggle_channel": "請輸入要切換錄製狀態的頻道編號：",
    "settings.channel_status_changed": "{name} 頻道的錄製狀態已變更為 {status}。",
    "settings.recording_menu": "\n1. 設定錄製執行緒數\n2. 設定直播重新掃描間隔\n3. 設定輸出格式\n4. 設定錄製檔案分段間隔\n5. 返回",
    "settings.current_threads": "目前錄製執行緒數為 {count}。",
    "settings.thread_recommendation": "建議使用 2-4 個執行緒：低階系統建議 2 個，高階系統建議 4 個。",
    "settings.prompt_threads": "請輸入要變更的執行緒數：",
    "settings.threads_changed": "執行緒數已變更。",
    "settings.invalid_input": "輸入無效。",
    "settings.current_timeout": "目前直播重新掃描間隔為 {seconds} 秒。",
    "settings.prompt_timeout": "請輸入要變更的重新掃描間隔（秒）：",
    "settings.timeout_changed": "直播重新掃描間隔已變更。",
    "settings.current_output_format": "目前輸出格式為 {format}。",
    "settings.available_formats": "可用格式：ts、mkv、webm",
    "settings.prompt_output_format": "請輸入要變更的輸出格式：",
    "settings.output_format_changed": "輸出格式已變更為 {format}。",
    "settings.current_split": "目前錄製檔案分段間隔為 {interval}。",
    "settings.choose_split_unit": "請選擇分段間隔單位：",
    "settings.unit_hours": "1. 小時",
    "settings.unit_minutes": "2. 分鐘",
    "settings.unit_disable": "3. 停用分段錄製",
    "settings.prompt_split_hours": "請輸入要變更的分段間隔（小時）：",
    "settings.prompt_split_minutes": "請輸入要變更的分段間隔（分鐘）：",
    "settings.split_disabled": "分段錄製已停用。",
    "settings.split_changed": "錄製檔案分段間隔已變更為 {interval}。",
    "settings.codec_title": "--- {codec} 設定 ---",
    "settings.status": "狀態：{status}",
    "settings.encoder": "編碼器：{encoder}",
    "settings.target_bitrate": "目標位元率：{bitrate}",
    "settings.max_bitrate": "最大位元率：{bitrate}",
    "settings.preset": "預設：{preset}",
    "settings.hevc_menu": "1. 切換啟用/停用\n2. 設定編碼器（libx265、hevc_nvenc、hevc_qsv 等）\n3. 設定目標位元率（例如 6000k）\n4. 設定最大位元率（例如 8000k）\n5. 設定預設（ultrafast、superfast 等）\n6. 返回",
    "settings.av1_menu": "1. 切換啟用/停用\n2. 設定編碼器（libsvtav1、libaom-av1、av1_nvenc 等）\n3. 設定目標位元率（例如 6000k）\n4. 設定最大位元率（例如 8000k）\n5. 設定預設（libsvtav1/libaom-av1：0-13，NVENC：p1-p7）\n6. 返回",
    "settings.encoding_toggled": "{codec} 編碼已{state}。",
    "settings.available_encoders": "\n可用編碼器：",
    "settings.prompt_encoder": "請輸入編碼器名稱：",
    "settings.invalid_encoder": "編碼器名稱無效。",
    "settings.prompt_target_bitrate": "請輸入目標位元率（例如 6000k）：",
    "settings.prompt_max_bitrate": "請輸入最大位元率（例如 10000k）：",
    "settings.hevc_preset_options": "選項：ultrafast（建議）、superfast、veryfast、faster、fast、medium",
    "settings.hevc_preset_note": "注意：NVENC 請使用 p1-p7。QSV 請使用 veryfast-veryslow。",
    "settings.prompt_preset": "請輸入預設名稱：",
    "settings.invalid_preset": "預設名稱無效。",
    "settings.prompt_ses": "請輸入 SES：",
    "settings.prompt_aut": "請輸入 AUT：",
    "settings.cookies_saved": "Cookie 資訊已成功儲存。",
    "settings.cookie_title": "--- Cookie 設定 ---",
    "settings.cookie_status": "驗證 Cookie 儲存狀態：{status}",
    "settings.cookie_menu": "1. 透過瀏覽器登入匯入\n2. 手動輸入\n3. 刪除已儲存的 Cookie\n4. 返回",
    "settings.browser_menu": "\n1. Chrome\n2. Microsoft Edge\n3. Firefox\n4. 返回",
    "settings.browser_login_notice": "將開啟新的 {browser} 視窗。請直接在該視窗中登入 NAVER 帳號。本程式不會收集您的帳號或密碼。",
    "settings.browser_login_wait": "在瀏覽器中完成登入後，請返回此處並按 Enter：",
    "settings.browser_cookies_missing": "在瀏覽器中找不到以下驗證 Cookie：{cookies}。請確認已完成 NAVER 登入。",
    "settings.browser_cookies_saved": "已儲存瀏覽器中的 NID_AUT 和 NID_SES Cookie。",
    "settings.browser_login_error": "無法啟動瀏覽器登入或匯入 Cookie：{error}",
    "settings.cookies_deleted": "已刪除儲存的驗證 Cookie。",
    "settings.dns_title": "--- DNS-over-HTTPS 設定 ---",
    "settings.doh_url": "DoH URL：{url}",
    "settings.dns_menu": "1. 切換啟用/停用\n2. 設定 DNS-over-HTTPS URL\n3. 重設為預設 URL\n4. 返回",
    "settings.dns_toggled": "DNS-over-HTTPS 已{state}。",
    "settings.prompt_doh_url": "請輸入 DNS-over-HTTPS URL：",
    "settings.doh_url_changed": "DNS-over-HTTPS URL 已變更為 {url}。",
    "settings.doh_url_reset": "DNS-over-HTTPS URL 已重設為 {url}。",
    "settings.logging_toggled": "記錄已{state}。",
    "settings.exiting": "正在離開設定。",
    "record.startup_banner": "Chzzk Rekoda made by munsy0227\n如果遇到 bug 或錯誤，請在 GitHub Issues 中回報！",
    "record.no_active_recordings": "沒有正在進行的錄製。",
    "record.progress_title": "錄製進度",
    "record.logs_title": "記錄",
    "record.table_channel": "頻道",
    "record.table_bitrate": "位元率",
    "record.table_download_speed": "下載速度",
    "record.table_total_size": "總大小",
    "record.table_out_time": "輸出時間",
    "record.table_start_time": "開始時間",
})

TRANSLATIONS["ja"].update({
    "settings.config_saved": "設定を config.json に保存しました。",
    "settings.config_save_error": "設定の保存中にエラーが発生しました: {error}",
    "settings.error_loading_config": "config.json の読み込み中にエラーが発生しました: {error}。既定値/移行を使用します。",
    "settings.corrupt_config_backed_up": (
        "破損した config.json を {backup_path} に保存しました。"
    ),
    "settings.corrupt_config_backup_error": (
        "破損した config.json をバックアップできなかったため、"
        "元のファイルを上書きせず安全に終了します: {error}"
    ),
    "settings.config_read_error": (
        "config.json を読み込めなかったため、ファイルを上書きせず"
        "安全に終了します: {error}"
    ),
    "settings.migrating_old_settings": "古いファイルから設定を移行しています...",
    "settings.invalid_channel_skipped": "無効なチャンネル ID をスキップします: {channel_id}",
    "settings.invalid_channels_reset": (
        "チャンネル一覧の形式が無効なため、空の一覧にリセットしました。"
    ),
    "settings.duplicate_channel_skipped": (
        "チャンネル ID が重複する後続の項目をスキップします: "
        "{channel_id}"
    ),
    "settings.try_again": "もう一度試してください。\n",
    "settings.channel_menu": "\n1. チャンネルを追加\n2. チャンネルを削除\n3. チャンネル録画のオン/オフ\n4. 戻る",
    "settings.prompt_channel_id": "追加する配信者チャンネルの固有 ID を入力してください: ",
    "settings.invalid_channel_id": "チャンネル ID が無効です。英字、数字、'_'、'-' のみ使用できます。",
    "settings.prompt_streamer_name": "配信者名を入力してください: ",
    "settings.prompt_output_dir": "保存先を入力してください。プログラムと同じ場所に保存する場合はフォルダー名だけ入力してください: ",
    "settings.confirm_channel": "id: {channel_id}, 名前: {name}, 保存先: {output_dir}。これで正しいですか？(Y/N): ",
    "settings.channel_added": "チャンネルを追加し、設定を保存しました。",
    "settings.reenter": "もう一度入力してください。",
    "settings.no_channels_delete": "削除できるチャンネルがありません。",
    "settings.current_channel_list": "現在のチャンネル一覧:",
    "settings.channel_list_item": "{idx}. id: {channel_id}, 名前: {name}",
    "settings.prompt_delete_channel": "削除するチャンネル番号を入力してください: ",
    "settings.deleted_channel": "削除したチャンネル: id: {channel_id}, 名前: {name}",
    "settings.channel_deleted": "チャンネルを削除し、設定を再採番しました。",
    "settings.invalid_channel_number": "チャンネル番号が無効です。",
    "settings.invalid_number": "入力が無効です。有効な数字を入力してください。",
    "settings.no_channels_toggle": "切り替えられるチャンネルがありません。",
    "settings.channel_list_item_status": "{idx}. id: {channel_id}, 名前: {name}, 録画状態: {status}",
    "settings.prompt_toggle_channel": "録画状態を切り替えるチャンネル番号を入力してください: ",
    "settings.channel_status_changed": "{name} チャンネルの録画状態を {status} に変更しました。",
    "settings.recording_menu": "\n1. 録画スレッド数を設定\n2. 配信再スキャン間隔を設定\n3. 出力形式を設定\n4. 録画ファイル分割間隔を設定\n5. 戻る",
    "settings.current_threads": "現在の録画スレッド数は {count} です。",
    "settings.thread_recommendation": "推奨は 2-4 スレッドです。低スペック環境は 2、高スペック環境は 4 を推奨します。",
    "settings.prompt_threads": "変更するスレッド数を入力してください: ",
    "settings.threads_changed": "スレッド数を変更しました。",
    "settings.invalid_input": "入力が無効です。",
    "settings.current_timeout": "現在の配信再スキャン間隔は {seconds} 秒です。",
    "settings.prompt_timeout": "変更する再スキャン間隔を秒単位で入力してください: ",
    "settings.timeout_changed": "配信再スキャン間隔を変更しました。",
    "settings.current_output_format": "現在の出力形式は {format} です。",
    "settings.available_formats": "使用可能な形式: ts, mkv, webm",
    "settings.prompt_output_format": "変更する出力形式を入力してください: ",
    "settings.output_format_changed": "出力形式を {format} に変更しました。",
    "settings.current_split": "現在の録画ファイル分割間隔は {interval} です。",
    "settings.choose_split_unit": "分割間隔の単位を選択してください:",
    "settings.unit_hours": "1. 時間",
    "settings.unit_minutes": "2. 分",
    "settings.unit_disable": "3. 分割録画を無効化",
    "settings.prompt_split_hours": "変更する分割間隔を時間単位で入力してください: ",
    "settings.prompt_split_minutes": "変更する分割間隔を分単位で入力してください: ",
    "settings.split_disabled": "分割録画を無効にしました。",
    "settings.split_changed": "録画ファイル分割間隔を {interval} に変更しました。",
    "settings.codec_title": "--- {codec} 設定 ---",
    "settings.status": "状態: {status}",
    "settings.encoder": "エンコーダー: {encoder}",
    "settings.target_bitrate": "目標ビットレート: {bitrate}",
    "settings.max_bitrate": "最大ビットレート: {bitrate}",
    "settings.preset": "プリセット: {preset}",
    "settings.hevc_menu": "1. 有効/無効を切り替え\n2. エンコーダーを設定 (libx265, hevc_nvenc, hevc_qsv など)\n3. 目標ビットレートを設定 (例: 6000k)\n4. 最大ビットレートを設定 (例: 8000k)\n5. プリセットを設定 (ultrafast, superfast など)\n6. 戻る",
    "settings.av1_menu": "1. 有効/無効を切り替え\n2. エンコーダーを設定 (libsvtav1, libaom-av1, av1_nvenc など)\n3. 目標ビットレートを設定 (例: 6000k)\n4. 最大ビットレートを設定 (例: 8000k)\n5. プリセットを設定 (libsvtav1/libaom-av1: 0-13, NVENC: p1-p7)\n6. 戻る",
    "settings.encoding_toggled": "{codec} エンコードを{state}にしました。",
    "settings.available_encoders": "\n使用可能なエンコーダー:",
    "settings.prompt_encoder": "エンコーダー名を入力してください: ",
    "settings.invalid_encoder": "エンコーダー名が無効です。",
    "settings.prompt_target_bitrate": "目標ビットレートを入力してください (例: 6000k): ",
    "settings.prompt_max_bitrate": "最大ビットレートを入力してください (例: 10000k): ",
    "settings.hevc_preset_options": "オプション: ultrafast（推奨）, superfast, veryfast, faster, fast, medium",
    "settings.hevc_preset_note": "注: NVENC は p1-p7 を使用してください。QSV は veryfast-veryslow を使用してください。",
    "settings.prompt_preset": "プリセット名を入力してください: ",
    "settings.invalid_preset": "プリセット名が無効です。",
    "settings.prompt_ses": "SES を入力してください: ",
    "settings.prompt_aut": "AUT を入力してください: ",
    "settings.cookies_saved": "Cookie 情報を保存しました。",
    "settings.cookie_title": "--- Cookie 設定 ---",
    "settings.cookie_status": "認証 Cookie の保存状態: {status}",
    "settings.cookie_menu": "1. ブラウザログインから取得\n2. 手動入力\n3. 保存済み Cookie を削除\n4. 戻る",
    "settings.browser_menu": "\n1. Chrome\n2. Microsoft Edge\n3. Firefox\n4. 戻る",
    "settings.browser_login_notice": "新しい {browser} ウィンドウを開きます。そのウィンドウで NAVER アカウントに直接ログインしてください。このプログラムは ID やパスワードを収集しません。",
    "settings.browser_login_wait": "ブラウザでログインを完了したら、ここに戻って Enter キーを押してください: ",
    "settings.browser_cookies_missing": "ブラウザで次の認証 Cookie が見つかりませんでした: {cookies}。NAVER へのログインが完了しているか確認してください。",
    "settings.browser_cookies_saved": "ブラウザの NID_AUT と NID_SES Cookie を保存しました。",
    "settings.browser_login_error": "ブラウザログインを開始できないか、Cookie を取得できませんでした: {error}",
    "settings.cookies_deleted": "保存済みの認証 Cookie を削除しました。",
    "settings.dns_title": "--- DNS-over-HTTPS 設定 ---",
    "settings.doh_url": "DoH URL: {url}",
    "settings.dns_menu": "1. 有効/無効を切り替え\n2. DNS-over-HTTPS URL を設定\n3. 既定 URL に戻す\n4. 戻る",
    "settings.dns_toggled": "DNS-over-HTTPS を{state}にしました。",
    "settings.prompt_doh_url": "DNS-over-HTTPS URL を入力してください: ",
    "settings.doh_url_changed": "DNS-over-HTTPS URL を {url} に変更しました。",
    "settings.doh_url_reset": "DNS-over-HTTPS URL を {url} に戻しました。",
    "settings.logging_toggled": "ログ記録を{state}にしました。",
    "settings.exiting": "設定を終了します。",
    "record.startup_banner": "Chzzk Rekoda made by munsy0227\nバグやエラーが発生した場合は GitHub Issues で報告してください！",
    "record.no_active_recordings": "進行中の録画はありません。",
    "record.progress_title": "録画進行状況",
    "record.logs_title": "ログ",
    "record.table_channel": "チャンネル",
    "record.table_bitrate": "ビットレート",
    "record.table_download_speed": "ダウンロード速度",
    "record.table_total_size": "合計サイズ",
    "record.table_out_time": "出力時間",
    "record.table_start_time": "開始時刻",
})

ADDITIONAL_TRANSLATIONS_APPLIED = True


TRANSLATIONS["zh-CN"].update({
    "record.logging_toggled": "日志已{state}。",
    "record.logging_toggle_error": "切换日志时出错：{error}",
    "record.doh_using": "正在使用 DNS-over-HTTPS 解析器：{url}",
    "record.doh_install_failed": "无法安装 DNS-over-HTTPS 解析器：{error}",
    "record.unknown_hevc_encoder": "未知的 HEVC 编码器 '{encoder}'。将回退到 libx265。",
    "record.unknown_av1_encoder": "未知的 AV1 编码器 '{encoder}'。将回退到 libsvtav1。",
    "record.skip_invalid_channel_entry": "跳过第 {index} 个无效频道项。",
    "record.skip_invalid_channel_id": "跳过 ID 无效的频道：{channel_id!r}",
    "record.process_timeout_kill": "{name} 未及时结束，正在强制终止。",
    "record.task_timeout": "{name} 未在 {timeout:.0f} 秒内退出。",
    "record.pipe_closed": "为 {channel_name} 传输流时，ffmpeg stdin 已关闭。",
    "record.pipe_error": "将 {channel_name} 的流传输到 ffmpeg 时出错：{error}",
    "record.running_windows": "正在 Windows 上运行。",
    "record.using_bundled_ffmpeg": "正在使用内置 ffmpeg：{path}",
    "record.using_path_ffmpeg": "正在使用 PATH 中的 ffmpeg：{path}",
    "record.ffmpeg_not_found_windows": "未找到 ffmpeg。请运行 install.bat，或将 ffmpeg 添加到 PATH。",
    "record.running_os_ffmpeg_found": "正在 {os_name} 上运行。ffmpeg 位置：{path}",
    "record.ffmpeg_not_found_path": "系统 PATH 中未找到 ffmpeg。",
    "record.json_decode_error": "{file_path} 中的 JSON 解码错误：{error}",
    "record.json_load_error": "从 {file_path} 加载 JSON 时出错：{error}",
    "record.channel_not_live": "'{channel_name}' 频道当前未开播。",
    "record.channel_blocked": "'{channel_name}' 频道已被阻止。",
    "record.member_only_cookies_required": (
        "'{channel_name}' 是会员专享直播。仅可使用已开通 Naver Plus 会员或 "
        "Cheat Key 订阅账号的 NID_AUT 和 NID_SES Cookie 值进行录制。"
    ),
    "record.member_only_access_required": (
        "无法验证 '{channel_name}' 的会员播放权限。请确认 NID_AUT 和 NID_SES "
        "是已开通 Naver Plus 会员或 Cheat Key 订阅账号的有效 Cookie 值。"
    ),
    "record.http_live_info_error": "获取 {channel_name} 的直播信息时发生 HTTP 错误：{error}",
    "record.live_info_failed": "无法获取 {channel_name} 的直播信息：{error}",
    "record.filename_too_long": "文件名 '{filename}' 过长。将缩短为 '{shortened}'。",
    "record.segment_template_too_long": "分段文件名模板 {filename!r} 过长。将缩短为 {shortened!r}。",
    "record.read_stream_error": "读取 {channel_id} 的流时发生错误：{error}",
    "record.av1_unusable": "当前 FFmpeg/硬件环境无法使用 AV1 编码器 '{encoder}'：{message}",
    "record.av1_fallback": "本次录制将使用 AV1 编码器 '{fallback}'，而不是 '{selected}'。",
    "record.av1_fallback_unusable": "AV1 备用编码器 '{encoder}' 不可用：{message}",
    "record.av1_no_encoder": "未找到可用的 AV1 编码器。将不使用 AV1 编码录制。",
    "record.hevc_unusable": "当前 FFmpeg/硬件环境无法使用 HEVC 编码器 '{encoder}'：{message}",
    "record.hevc_fallback": "本次录制将使用 HEVC 编码器 '{fallback}'，而不是 '{selected}'。",
    "record.hevc_fallback_unusable": "HEVC 备用编码器 '{encoder}' 不可用：{message}",
    "record.hevc_no_encoder": "未找到可用的 HEVC 编码器。将不使用 HEVC 编码录制。",
    "record.attempting_channel": "正在尝试录制频道：{channel_name}",
    "record.channel_inactive": "{channel_name} 频道未启用，跳过录制。",
    "record.waiting_live": "正在等待 '{channel_name}' 频道开播...",
    "record.av1_ts_fallback": "{channel_name} 不支持以 TS 保存 AV1 输出。将回退到 MKV。",
    "record.split_enabled": "{channel_name} 已启用分段录制：每 {interval} 创建一个新文件。",
    "record.hevc_ignored_webm": "{channel_name} 使用 WebM 输出时会忽略 HEVC 设置。",
    "record.recording_started": "{channel_name} 的录制已于 {current_time} 开始。",
    "record.ffmpeg_exited": "{channel_name} 的 ffmpeg 进程已退出，返回代码为 {returncode}。",
    "record.stream_process_exited": "{channel_name} 的流录制进程已退出，返回代码为 {returncode}。",
    "record.ffmpeg_failed": "{channel_name} 的 ffmpeg 失败；根本原因请查看上方 ffmpeg stderr 行。",
    "record.streamlink_failed": "{channel_name} 的 streamlink 失败；根本原因请查看上方 streamlink stderr 行。",
    "record.recording_stopped": "{channel_name} 的录制已停止。",
    "record.empty_segment_discarded": "已删除 {channel_name} 的空录制分段：{path}",
    "record.no_segments": "{channel_name} 没有生成录制分段文件。",
    "record.split_left_incomplete": "由于 ffmpeg 以返回代码 {returncode} 退出，分段录制文件已保留在 {output_dir}。最后一个分段可能不完整。",
    "record.segment_saved": "录制分段已保存到 {path}",
    "record.empty_file_discarded": "已删除 {channel_name} 的空录制文件。",
    "record.incomplete_file_left": "由于 ffmpeg 以返回代码 {returncode} 退出，未完成的录制文件保留在 {path}。",
    "record.saved": "录制文件已保存到 {path}",
    "record.task_cancelled": "{channel_name} 的录制任务已取消。",
    "record.recording_error": "录制 {channel_name} 时发生错误：{error}",
    "record.no_stream_url": "{channel_name} 没有可用的流 URL。",
    "record.unfinished_file_left": "未完成的录制文件已保留在 {path}。",
    "record.ffmpeg_executable_missing": "未找到 ffmpeg 可执行文件。正在退出。",
    "record.cancelled_deactivated_id": "已取消停用频道的录制任务：{channel_id}",
    "record.channel_id_missing": "配置中缺少频道 ID。",
    "record.started_new_active_channel": "已为新的启用频道启动录制任务：{channel_name}",
    "record.cancelled_deactivated_name": "已取消停用频道的录制任务：{channel_name}",
    "record.all_inactive": "所有频道均未启用。没有正在进行的录制。",
    "record.management_cancelled": "录制管理任务已取消。",
    "record.shutdown_wait_timeout": "等待录制任务结束超时。正在取消剩余任务。",
    "record.shutdown_signal": "收到关闭信号。正在关闭...",
    "record.keyboard_interrupt": "收到 KeyboardInterrupt。正在关闭...",
    "record.main_cancelled": "主任务已取消。",
    "record.unhandled_error": "发生错误：{error}",
    "record.shutdown_complete": "录制程序已关闭。",
})

TRANSLATIONS["zh-TW"].update({
    "record.logging_toggled": "記錄已{state}。",
    "record.logging_toggle_error": "切換記錄時發生錯誤：{error}",
    "record.doh_using": "正在使用 DNS-over-HTTPS 解析器：{url}",
    "record.doh_install_failed": "無法安裝 DNS-over-HTTPS 解析器：{error}",
    "record.unknown_hevc_encoder": "未知的 HEVC 編碼器 '{encoder}'。將回退到 libx265。",
    "record.unknown_av1_encoder": "未知的 AV1 編碼器 '{encoder}'。將回退到 libsvtav1。",
    "record.skip_invalid_channel_entry": "略過第 {index} 個無效頻道項目。",
    "record.skip_invalid_channel_id": "略過 ID 無效的頻道：{channel_id!r}",
    "record.process_timeout_kill": "{name} 未及時結束，正在強制終止。",
    "record.task_timeout": "{name} 未在 {timeout:.0f} 秒內結束。",
    "record.pipe_closed": "為 {channel_name} 傳輸串流時，ffmpeg stdin 已關閉。",
    "record.pipe_error": "將 {channel_name} 的串流傳輸到 ffmpeg 時發生錯誤：{error}",
    "record.running_windows": "正在 Windows 上執行。",
    "record.using_bundled_ffmpeg": "正在使用內建 ffmpeg：{path}",
    "record.using_path_ffmpeg": "正在使用 PATH 中的 ffmpeg：{path}",
    "record.ffmpeg_not_found_windows": "找不到 ffmpeg。請執行 install.bat，或將 ffmpeg 加入 PATH。",
    "record.running_os_ffmpeg_found": "正在 {os_name} 上執行。ffmpeg 位置：{path}",
    "record.ffmpeg_not_found_path": "系統 PATH 中找不到 ffmpeg。",
    "record.json_decode_error": "{file_path} 中的 JSON 解碼錯誤：{error}",
    "record.json_load_error": "從 {file_path} 載入 JSON 時發生錯誤：{error}",
    "record.channel_not_live": "'{channel_name}' 頻道目前未開播。",
    "record.channel_blocked": "'{channel_name}' 頻道已被封鎖。",
    "record.member_only_cookies_required": (
        "'{channel_name}' 是會員專屬直播。僅可使用已開通 Naver Plus 會員或 "
        "Cheat Key 訂閱帳號的 NID_AUT 和 NID_SES Cookie 值進行錄製。"
    ),
    "record.member_only_access_required": (
        "無法驗證 '{channel_name}' 的會員播放權限。請確認 NID_AUT 和 NID_SES "
        "是已開通 Naver Plus 會員或 Cheat Key 訂閱帳號的有效 Cookie 值。"
    ),
    "record.http_live_info_error": "取得 {channel_name} 的直播資訊時發生 HTTP 錯誤：{error}",
    "record.live_info_failed": "無法取得 {channel_name} 的直播資訊：{error}",
    "record.filename_too_long": "檔案名稱 '{filename}' 過長。將縮短為 '{shortened}'。",
    "record.segment_template_too_long": "分段檔案名稱範本 {filename!r} 過長。將縮短為 {shortened!r}。",
    "record.read_stream_error": "讀取 {channel_id} 的串流時發生錯誤：{error}",
    "record.av1_unusable": "目前 FFmpeg/硬體環境無法使用 AV1 編碼器 '{encoder}'：{message}",
    "record.av1_fallback": "本次錄製將使用 AV1 編碼器 '{fallback}'，而不是 '{selected}'。",
    "record.av1_fallback_unusable": "AV1 備用編碼器 '{encoder}' 不可用：{message}",
    "record.av1_no_encoder": "找不到可用的 AV1 編碼器。將不使用 AV1 編碼錄製。",
    "record.hevc_unusable": "目前 FFmpeg/硬體環境無法使用 HEVC 編碼器 '{encoder}'：{message}",
    "record.hevc_fallback": "本次錄製將使用 HEVC 編碼器 '{fallback}'，而不是 '{selected}'。",
    "record.hevc_fallback_unusable": "HEVC 備用編碼器 '{encoder}' 不可用：{message}",
    "record.hevc_no_encoder": "找不到可用的 HEVC 編碼器。將不使用 HEVC 編碼錄製。",
    "record.attempting_channel": "正在嘗試錄製頻道：{channel_name}",
    "record.channel_inactive": "{channel_name} 頻道未啟用，略過錄製。",
    "record.waiting_live": "正在等待 '{channel_name}' 頻道開播...",
    "record.av1_ts_fallback": "{channel_name} 不支援以 TS 儲存 AV1 輸出。將回退到 MKV。",
    "record.split_enabled": "{channel_name} 已啟用分段錄製：每 {interval} 建立一個新檔案。",
    "record.hevc_ignored_webm": "{channel_name} 使用 WebM 輸出時會忽略 HEVC 設定。",
    "record.recording_started": "{channel_name} 的錄製已於 {current_time} 開始。",
    "record.ffmpeg_exited": "{channel_name} 的 ffmpeg 程序已結束，返回碼為 {returncode}。",
    "record.stream_process_exited": "{channel_name} 的串流錄製程序已結束，返回碼為 {returncode}。",
    "record.ffmpeg_failed": "{channel_name} 的 ffmpeg 失敗；根本原因請查看上方 ffmpeg stderr 行。",
    "record.streamlink_failed": "{channel_name} 的 streamlink 失敗；根本原因請查看上方 streamlink stderr 行。",
    "record.recording_stopped": "{channel_name} 的錄製已停止。",
    "record.empty_segment_discarded": "已刪除 {channel_name} 的空錄製分段：{path}",
    "record.no_segments": "{channel_name} 沒有產生錄製分段檔案。",
    "record.split_left_incomplete": "由於 ffmpeg 以返回碼 {returncode} 結束，分段錄製檔案已保留在 {output_dir}。最後一個分段可能不完整。",
    "record.segment_saved": "錄製分段已儲存到 {path}",
    "record.empty_file_discarded": "已刪除 {channel_name} 的空錄製檔案。",
    "record.incomplete_file_left": "由於 ffmpeg 以返回碼 {returncode} 結束，未完成的錄製檔案保留在 {path}。",
    "record.saved": "錄製檔案已儲存到 {path}",
    "record.task_cancelled": "{channel_name} 的錄製工作已取消。",
    "record.recording_error": "錄製 {channel_name} 時發生錯誤：{error}",
    "record.no_stream_url": "{channel_name} 沒有可用的串流 URL。",
    "record.unfinished_file_left": "未完成的錄製檔案已保留在 {path}。",
    "record.ffmpeg_executable_missing": "找不到 ffmpeg 可執行檔。正在離開。",
    "record.cancelled_deactivated_id": "已取消停用頻道的錄製工作：{channel_id}",
    "record.channel_id_missing": "設定中缺少頻道 ID。",
    "record.started_new_active_channel": "已為新的啟用頻道啟動錄製工作：{channel_name}",
    "record.cancelled_deactivated_name": "已取消停用頻道的錄製工作：{channel_name}",
    "record.all_inactive": "所有頻道均未啟用。沒有正在進行的錄製。",
    "record.management_cancelled": "錄製管理工作已取消。",
    "record.shutdown_wait_timeout": "等待錄製工作結束逾時。正在取消剩餘工作。",
    "record.shutdown_signal": "收到關閉訊號。正在關閉...",
    "record.keyboard_interrupt": "收到 KeyboardInterrupt。正在關閉...",
    "record.main_cancelled": "主工作已取消。",
    "record.unhandled_error": "發生錯誤：{error}",
    "record.shutdown_complete": "錄製程式已關閉。",
})

TRANSLATIONS["ja"].update({
    "record.logging_toggled": "ログ記録を{state}にしました。",
    "record.logging_toggle_error": "ログ設定の切り替え中にエラーが発生しました: {error}",
    "record.doh_using": "DNS-over-HTTPS リゾルバーを使用します: {url}",
    "record.doh_install_failed": "DNS-over-HTTPS リゾルバーをインストールできませんでした: {error}",
    "record.unknown_hevc_encoder": "不明な HEVC エンコーダー '{encoder}' です。libx265 にフォールバックします。",
    "record.unknown_av1_encoder": "不明な AV1 エンコーダー '{encoder}' です。libsvtav1 にフォールバックします。",
    "record.skip_invalid_channel_entry": "インデックス {index} の無効なチャンネル項目をスキップします。",
    "record.skip_invalid_channel_id": "無効な ID のチャンネルをスキップします: {channel_id!r}",
    "record.process_timeout_kill": "{name} が時間内に終了しませんでした。強制終了します。",
    "record.task_timeout": "{name} が {timeout:.0f} 秒以内に終了しませんでした。",
    "record.pipe_closed": "{channel_name} のストリーム転送中に ffmpeg stdin が閉じられました。",
    "record.pipe_error": "{channel_name} のストリームを ffmpeg に転送中にエラーが発生しました: {error}",
    "record.running_windows": "Windows で実行中です。",
    "record.using_bundled_ffmpeg": "同梱 ffmpeg を使用します: {path}",
    "record.using_path_ffmpeg": "PATH の ffmpeg を使用します: {path}",
    "record.ffmpeg_not_found_windows": "ffmpeg が見つかりません。install.bat を実行するか、ffmpeg を PATH に追加してください。",
    "record.running_os_ffmpeg_found": "{os_name} で実行中です。ffmpeg の場所: {path}",
    "record.ffmpeg_not_found_path": "システム PATH に ffmpeg が見つかりません。",
    "record.json_decode_error": "{file_path} の JSON デコードエラー: {error}",
    "record.json_load_error": "{file_path} から JSON を読み込み中にエラー: {error}",
    "record.channel_not_live": "'{channel_name}' チャンネルは現在配信中ではありません。",
    "record.channel_blocked": "'{channel_name}' チャンネルはブロックされています。",
    "record.member_only_cookies_required": (
        "'{channel_name}' はメンバーシップ限定配信です。録画するには、"
        "Naver Plus メンバーシップまたはチートキーを購読しているアカウントの "
        "NID_AUT と NID_SES の Cookie 値を両方指定してください。"
    ),
    "record.member_only_access_required": (
        "'{channel_name}' のメンバーシップ再生権限を確認できませんでした。"
        "Naver Plus メンバーシップまたはチートキーを購読しているアカウントの "
        "有効な NID_AUT と NID_SES の Cookie 値か確認してください。"
    ),
    "record.http_live_info_error": "{channel_name} のライブ情報取得中に HTTP エラーが発生しました: {error}",
    "record.live_info_failed": "{channel_name} のライブ情報を取得できませんでした: {error}",
    "record.filename_too_long": "ファイル名 '{filename}' が長すぎます。'{shortened}' に短縮します。",
    "record.segment_template_too_long": "分割ファイル名テンプレート {filename!r} が長すぎます。{shortened!r} に短縮します。",
    "record.read_stream_error": "{channel_id} のストリーム読み取り中にエラーが発生しました: {error}",
    "record.av1_unusable": "現在の FFmpeg/ハードウェア環境では AV1 エンコーダー '{encoder}' を使用できません: {message}",
    "record.av1_fallback": "今回の録画では AV1 エンコーダー '{selected}' の代わりに '{fallback}' を使用します。",
    "record.av1_fallback_unusable": "AV1 代替エンコーダー '{encoder}' は使用できません: {message}",
    "record.av1_no_encoder": "使用可能な AV1 エンコーダーがありません。AV1 エンコードなしで録画します。",
    "record.hevc_unusable": "現在の FFmpeg/ハードウェア環境では HEVC エンコーダー '{encoder}' を使用できません: {message}",
    "record.hevc_fallback": "今回の録画では HEVC エンコーダー '{selected}' の代わりに '{fallback}' を使用します。",
    "record.hevc_fallback_unusable": "HEVC 代替エンコーダー '{encoder}' は使用できません: {message}",
    "record.hevc_no_encoder": "使用可能な HEVC エンコーダーがありません。HEVC エンコードなしで録画します。",
    "record.attempting_channel": "{channel_name} チャンネルの録画を試行します。",
    "record.channel_inactive": "{channel_name} チャンネルは無効です。録画をスキップします。",
    "record.waiting_live": "'{channel_name}' チャンネルの配信開始を待機しています...",
    "record.av1_ts_fallback": "{channel_name} では AV1 出力を TS 形式で保存できません。MKV にフォールバックします。",
    "record.split_enabled": "{channel_name} の分割録画が有効です: {interval} ごとに新しいファイルを作成します。",
    "record.hevc_ignored_webm": "{channel_name} の WebM 出力では HEVC 設定は無視されます。",
    "record.recording_started": "{channel_name} の録画を {current_time} に開始しました。",
    "record.ffmpeg_exited": "{channel_name} の ffmpeg プロセスは戻りコード {returncode} で終了しました。",
    "record.stream_process_exited": "{channel_name} のストリーム録画プロセスは戻りコード {returncode} で終了しました。",
    "record.ffmpeg_failed": "{channel_name} の ffmpeg が失敗しました。根本原因は上の ffmpeg stderr 行を確認してください。",
    "record.streamlink_failed": "{channel_name} の streamlink が失敗しました。根本原因は上の streamlink stderr 行を確認してください。",
    "record.recording_stopped": "{channel_name} の録画を停止しました。",
    "record.empty_segment_discarded": "{channel_name} の空の録画セグメントを削除しました: {path}",
    "record.no_segments": "{channel_name} の録画セグメントファイルは作成されませんでした。",
    "record.split_left_incomplete": "ffmpeg が戻りコード {returncode} で終了したため、分割録画ファイルを {output_dir} に残しました。最後のセグメントは不完全な可能性があります。",
    "record.segment_saved": "録画セグメントを {path} に保存しました",
    "record.empty_file_discarded": "{channel_name} の空の録画ファイルを削除しました。",
    "record.incomplete_file_left": "ffmpeg が戻りコード {returncode} で終了したため、不完全な録画ファイルを {path} に残しました。",
    "record.saved": "録画を {path} に保存しました",
    "record.task_cancelled": "{channel_name} の録画タスクはキャンセルされました。",
    "record.recording_error": "{channel_name} の録画中にエラーが発生しました: {error}",
    "record.no_stream_url": "{channel_name} に使用できるストリーム URL がありません。",
    "record.unfinished_file_left": "未完了の録画ファイルを {path} に残しました。",
    "record.ffmpeg_executable_missing": "ffmpeg 実行ファイルが見つかりません。終了します。",
    "record.cancelled_deactivated_id": "無効化されたチャンネルの録画タスクをキャンセルしました: {channel_id}",
    "record.channel_id_missing": "設定にチャンネル ID がありません。",
    "record.started_new_active_channel": "新しい有効なチャンネルの録画タスクを開始しました: {channel_name}",
    "record.cancelled_deactivated_name": "無効化されたチャンネルの録画タスクをキャンセルしました: {channel_name}",
    "record.all_inactive": "すべてのチャンネルが無効です。進行中の録画はありません。",
    "record.management_cancelled": "録画管理タスクはキャンセルされました。",
    "record.shutdown_wait_timeout": "録画タスクの終了待機がタイムアウトしました。残りのタスクをキャンセルします。",
    "record.shutdown_signal": "終了シグナルを受信しました。終了中です...",
    "record.keyboard_interrupt": "KeyboardInterrupt を受信しました。終了中です...",
    "record.main_cancelled": "メインタスクはキャンセルされました。",
    "record.unhandled_error": "エラーが発生しました: {error}",
    "record.shutdown_complete": "録画プログラムを終了しました。",
})

RECORD_PROCESS_TRANSLATIONS_APPLIED = True


# Channel discovery and duplicate-check messages.
TRANSLATIONS["ko"].update({
    "settings.add_channel_menu": "\n1. 채널 이름으로 검색\n2. 채널 ID로 직접 추가\n3. 뒤로 가기",
    "settings.prompt_search_keyword": "검색할 채널 이름을 입력하세요: ",
    "settings.empty_search_keyword": "검색어를 입력해야 합니다.",
    "settings.channel_search_failed": "채널 검색에 실패했습니다: {error}",
    "settings.no_search_results": "검색 결과가 없습니다.",
    "settings.channel_search_results": "채널 검색 결과:",
    "settings.already_registered_marker": "[이미 등록됨]",
    "settings.channel_search_result": "{index}. {name} (ID: {channel_id}) {status}",
    "settings.prompt_search_result": "추가할 채널 번호를 입력하세요 (취소: 0): ",
    "settings.channel_already_registered": "이미 등록된 채널입니다. ID: {channel_id}, 이름: {name}, 저장 경로: {output_dir}",
    "settings.channel_lookup_in_progress": "채널 ID로 공식 채널 이름을 조회하는 중입니다...",
    "settings.channel_lookup_failed": "채널 정보를 조회하지 못했습니다: {error}",
    "settings.channel_lookup_result": "조회한 채널: ID: {channel_id}, 이름: {name}",
    "settings.duplicate_channel_name_warning": "같은 이름 '{name}'을 사용하는 등록 채널이 있습니다. 기존 ID: {channel_ids}",
    "settings.prompt_output_dir": "저장 경로를 입력하세요 (기본값: 프로젝트 안의 '{default_output_dir}' 폴더): ",
    "settings.output_dir_create_error": "저장 폴더를 만들 수 없습니다: {error}",
    "settings.api_invalid_response": "CHZZK API 응답 형식이 올바르지 않습니다.",
    "settings.api_missing_content": "CHZZK API가 채널 데이터를 반환하지 않았습니다.",
    "settings.api_invalid_channel_data": "CHZZK API가 올바른 채널 정보를 반환하지 않았습니다.",
})

TRANSLATIONS["en"].update({
    "settings.add_channel_menu": "\n1. Search by channel name\n2. Add directly by channel ID\n3. Go back",
    "settings.prompt_search_keyword": "Enter a channel name to search for: ",
    "settings.empty_search_keyword": "A search term is required.",
    "settings.channel_search_failed": "Channel search failed: {error}",
    "settings.no_search_results": "No channels were found.",
    "settings.channel_search_results": "Channel search results:",
    "settings.already_registered_marker": "[Already registered]",
    "settings.channel_search_result": "{index}. {name} (ID: {channel_id}) {status}",
    "settings.prompt_search_result": "Enter the channel number to add (0 to cancel): ",
    "settings.channel_already_registered": "This channel is already registered. ID: {channel_id}, name: {name}, storage path: {output_dir}",
    "settings.channel_lookup_in_progress": "Looking up the official channel name from the channel ID...",
    "settings.channel_lookup_failed": "Could not retrieve channel information: {error}",
    "settings.channel_lookup_result": "Channel found: ID: {channel_id}, name: {name}",
    "settings.duplicate_channel_name_warning": "A registered channel already uses the name '{name}'. Existing ID(s): {channel_ids}",
    "settings.prompt_output_dir": "Enter a storage path (default: the '{default_output_dir}' folder inside the project): ",
    "settings.output_dir_create_error": "Could not create the storage folder: {error}",
    "settings.api_invalid_response": "The CHZZK API returned an invalid response.",
    "settings.api_missing_content": "The CHZZK API did not return channel data.",
    "settings.api_invalid_channel_data": "The CHZZK API did not return valid channel information.",
})

TRANSLATIONS["zh-CN"].update({
    "settings.add_channel_menu": "\n1. 按频道名称搜索\n2. 通过频道 ID 直接添加\n3. 返回",
    "settings.prompt_search_keyword": "请输入要搜索的频道名称：",
    "settings.empty_search_keyword": "必须输入搜索词。",
    "settings.channel_search_failed": "频道搜索失败：{error}",
    "settings.no_search_results": "没有搜索结果。",
    "settings.channel_search_results": "频道搜索结果：",
    "settings.already_registered_marker": "[已注册]",
    "settings.channel_search_result": "{index}. {name}（ID：{channel_id}）{status}",
    "settings.prompt_search_result": "请输入要添加的频道编号（取消：0）：",
    "settings.channel_already_registered": "该频道已注册。ID：{channel_id}，名称：{name}，保存路径：{output_dir}",
    "settings.channel_lookup_in_progress": "正在通过频道 ID 查询官方频道名称...",
    "settings.channel_lookup_failed": "无法获取频道信息：{error}",
    "settings.channel_lookup_result": "查询到的频道：ID：{channel_id}，名称：{name}",
    "settings.duplicate_channel_name_warning": "已有注册频道使用相同名称“{name}”。现有 ID：{channel_ids}",
    "settings.prompt_output_dir": "请输入保存路径（默认：项目内的“{default_output_dir}”文件夹）：",
    "settings.output_dir_create_error": "无法创建保存文件夹：{error}",
    "settings.api_invalid_response": "CHZZK API 返回了无效响应。",
    "settings.api_missing_content": "CHZZK API 未返回频道数据。",
    "settings.api_invalid_channel_data": "CHZZK API 未返回有效的频道信息。",
})

TRANSLATIONS["zh-TW"].update({
    "settings.add_channel_menu": "\n1. 依頻道名稱搜尋\n2. 透過頻道 ID 直接新增\n3. 返回",
    "settings.prompt_search_keyword": "請輸入要搜尋的頻道名稱：",
    "settings.empty_search_keyword": "必須輸入搜尋詞。",
    "settings.channel_search_failed": "頻道搜尋失敗：{error}",
    "settings.no_search_results": "沒有搜尋結果。",
    "settings.channel_search_results": "頻道搜尋結果：",
    "settings.already_registered_marker": "[已註冊]",
    "settings.channel_search_result": "{index}. {name}（ID：{channel_id}）{status}",
    "settings.prompt_search_result": "請輸入要新增的頻道編號（取消：0）：",
    "settings.channel_already_registered": "此頻道已註冊。ID：{channel_id}，名稱：{name}，儲存路徑：{output_dir}",
    "settings.channel_lookup_in_progress": "正在透過頻道 ID 查詢官方頻道名稱...",
    "settings.channel_lookup_failed": "無法取得頻道資訊：{error}",
    "settings.channel_lookup_result": "查詢到的頻道：ID：{channel_id}，名稱：{name}",
    "settings.duplicate_channel_name_warning": "已有註冊頻道使用相同名稱「{name}」。現有 ID：{channel_ids}",
    "settings.prompt_output_dir": "請輸入儲存路徑（預設：專案內的「{default_output_dir}」資料夾）：",
    "settings.output_dir_create_error": "無法建立儲存資料夾：{error}",
    "settings.api_invalid_response": "CHZZK API 傳回了無效回應。",
    "settings.api_missing_content": "CHZZK API 未傳回頻道資料。",
    "settings.api_invalid_channel_data": "CHZZK API 未傳回有效的頻道資訊。",
})

TRANSLATIONS["ja"].update({
    "settings.add_channel_menu": "\n1. チャンネル名で検索\n2. チャンネル ID で直接追加\n3. 戻る",
    "settings.prompt_search_keyword": "検索するチャンネル名を入力してください: ",
    "settings.empty_search_keyword": "検索語を入力してください。",
    "settings.channel_search_failed": "チャンネル検索に失敗しました: {error}",
    "settings.no_search_results": "検索結果がありません。",
    "settings.channel_search_results": "チャンネル検索結果:",
    "settings.already_registered_marker": "[登録済み]",
    "settings.channel_search_result": "{index}. {name} (ID: {channel_id}) {status}",
    "settings.prompt_search_result": "追加するチャンネル番号を入力してください (キャンセル: 0): ",
    "settings.channel_already_registered": "このチャンネルは登録済みです。ID: {channel_id}, 名前: {name}, 保存先: {output_dir}",
    "settings.channel_lookup_in_progress": "チャンネル ID から公式チャンネル名を照会しています...",
    "settings.channel_lookup_failed": "チャンネル情報を取得できませんでした: {error}",
    "settings.channel_lookup_result": "照会したチャンネル: ID: {channel_id}, 名前: {name}",
    "settings.duplicate_channel_name_warning": "同じ名前「{name}」を使用する登録済みチャンネルがあります。既存 ID: {channel_ids}",
    "settings.prompt_output_dir": "保存先を入力してください (既定値: プロジェクト内の「{default_output_dir}」フォルダー): ",
    "settings.output_dir_create_error": "保存フォルダーを作成できません: {error}",
    "settings.api_invalid_response": "CHZZK API から無効な応答が返されました。",
    "settings.api_missing_content": "CHZZK API からチャンネルデータが返されませんでした。",
    "settings.api_invalid_channel_data": "CHZZK API から有効なチャンネル情報が返されませんでした。",
})
