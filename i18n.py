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
            "\n5. 프리셋 설정 (인코더별 전체 옵션 안내)"
            "\n6. 뒤로 가기"
        ),
        "settings.av1_menu": (
            "1. 활성화/비활성화 전환"
            "\n2. 인코더 설정 (libsvtav1, libaom-av1, av1_nvenc 등)"
            "\n3. 목표 비트레이트 설정 (예: 6000k)"
            "\n4. 최대 비트레이트 설정 (예: 8000k)"
            "\n5. 프리셋 설정 (인코더별 전체 옵션 안내)"
            "\n6. 뒤로 가기"
        ),
        "settings.encoding_toggled": "{codec} 인코딩이 {state}되었습니다.",
        "settings.available_encoders": "\n사용 가능한 인코더:",
        "settings.prompt_encoder": "인코더 이름을 입력하세요: ",
        "settings.invalid_encoder": "잘못된 인코더 이름입니다.",
        "settings.prompt_target_bitrate": "목표 비트레이트를 입력하세요 (예: 6000k): ",
        "settings.prompt_max_bitrate": "최대 비트레이트를 입력하세요 (예: 10000k): ",
        "settings.preset_help_x265": (
            "libx265 프리셋 (빠름/낮은 압축 효율 → 느림/높은 압축 효율):\n"
            "ultrafast → superfast → veryfast → faster → fast → medium → "
            "slow → slower → veryslow → placebo\n"
            "placebo는 처리 비용이 매우 커서 일반적인 녹화에는 권장하지 않습니다."
        ),
        "settings.preset_help_hevc_nvenc": (
            "HEVC NVENC 권장 프리셋:\n"
            "p1(가장 빠름/가장 낮은 화질), p2(더 빠름/낮은 화질), "
            "p3(빠름), p4(균형/기본값), p5(느림/좋은 화질), "
            "p6(더 느림/더 좋은 화질), p7(가장 느림/가장 좋은 화질)\n"
            "FFmpeg 버전별 호환 별칭: default, slow, medium, fast, hp, hq, "
            "bd, ll, llhq, llhp, lossless, losslesshp"
        ),
        "settings.preset_help_av1_nvenc": (
            "AV1 NVENC 권장 프리셋:\n"
            "p1(가장 빠름/가장 낮은 화질), p2(더 빠름/낮은 화질), "
            "p3(빠름), p4(균형/기본값), p5(느림/좋은 화질), "
            "p6(더 느림/더 좋은 화질), p7(가장 느림/가장 좋은 화질)\n"
            "FFmpeg 버전별 호환 별칭: default, slow, medium, fast"
        ),
        "settings.preset_help_qsv": (
            "QSV 프리셋 (빠름 → 고화질):\n"
            "veryfast, faster, fast, medium(기본값), slow, slower, veryslow\n"
            "숫자형 옵션: 7, 6, 5, 4, 3, 2, 1 (위 이름과 같은 순서), "
            "0(FFmpeg 자동값)"
        ),
        "settings.preset_help_hevc_amf": (
            "HEVC AMF 프리셋 (빠름 → 고화질):\n"
            "speed, balanced(기본값), quality"
        ),
        "settings.preset_help_av1_amf": (
            "AV1 AMF 프리셋 (빠름 → 고화질):\n"
            "speed, balanced(기본값), quality, high_quality\n"
            "high_quality는 최신 FFmpeg와 AMF 드라이버에서만 지원될 수 있습니다."
        ),
        "settings.preset_help_svtav1": (
            "SVT-AV1 프리셋: -2(FFmpeg/라이브러리 자동값), "
            "-1(품질 참조용·매우 느림), 0(가장 높은 압축 효율)부터 "
            "13(가장 빠름/가장 낮은 압축 효율)까지\n"
            "전체 옵션: -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8(기본값), "
            "9, 10, 11, 12, 13\n"
            "지원되는 최댓값과 특수값 동작은 FFmpeg/SVT-AV1 버전에 따라 다릅니다."
        ),
        "settings.preset_help_libaom": (
            "libaom-AV1 프리셋(cpu-used): 0(가장 느림/가장 높은 압축 효율)부터 "
            "8(가장 빠름/가장 낮은 압축 효율)까지\n"
            "전체 옵션: 0, 1, 2, 3, 4, 5, 6(기본값), 7, 8"
        ),
        "settings.preset_unsupported": (
            "{encoder}는 이 메뉴에서 사용할 FFmpeg -preset 옵션을 "
            "제공하지 않습니다."
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
        "record.config_reload_kept": (
            "{file_path}의 설정을 다시 불러오지 못해 현재 설정을 유지합니다."
        ),
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
        "record.streamlink_reconnect": (
            "{channel_name} 스트림에 {delay}초 후 다시 연결합니다 "
            "(연속 실패 {attempt}회)."
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
    "settings.hevc_menu": "1. Toggle Enable/Disable\n2. Set Encoder (libx265, hevc_nvenc, hevc_qsv, etc.)\n3. Set Target Bitrate (e.g., 6000k)\n4. Set Max Bitrate (e.g., 8000k)\n5. Set Preset (shows every option for the encoder)\n6. Go Back",
    "settings.av1_menu": "1. Toggle Enable/Disable\n2. Set Encoder (libsvtav1, libaom-av1, av1_nvenc, etc.)\n3. Set Target Bitrate (e.g., 6000k)\n4. Set Max Bitrate (e.g., 8000k)\n5. Set Preset (shows every option for the encoder)\n6. Go Back",
    "settings.encoding_toggled": "{codec} encoding has been {state}.",
    "settings.available_encoders": "\nAvailable Encoders:",
    "settings.prompt_encoder": "Enter encoder name: ",
    "settings.invalid_encoder": "Invalid encoder name.",
    "settings.prompt_target_bitrate": "Enter target bitrate (e.g., 6000k): ",
    "settings.prompt_max_bitrate": "Enter max bitrate (e.g., 10000k): ",
    "settings.preset_help_x265": "libx265 presets (fast/lower compression efficiency → slow/higher compression efficiency):\nultrafast → superfast → veryfast → faster → fast → medium → slow → slower → veryslow → placebo\nplacebo has an extreme processing cost and is not recommended for normal recording.",
    "settings.preset_help_hevc_nvenc": "HEVC NVENC recommended presets:\np1 (fastest/lowest quality), p2 (faster/lower quality), p3 (fast), p4 (balanced/default), p5 (slow/good quality), p6 (slower/better quality), p7 (slowest/best quality)\nFFmpeg version-dependent compatibility aliases: default, slow, medium, fast, hp, hq, bd, ll, llhq, llhp, lossless, losslesshp",
    "settings.preset_help_av1_nvenc": "AV1 NVENC recommended presets:\np1 (fastest/lowest quality), p2 (faster/lower quality), p3 (fast), p4 (balanced/default), p5 (slow/good quality), p6 (slower/better quality), p7 (slowest/best quality)\nFFmpeg version-dependent compatibility aliases: default, slow, medium, fast",
    "settings.preset_help_qsv": "QSV presets (speed → quality):\nveryfast, faster, fast, medium (default), slow, slower, veryslow\nNumeric options: 7, 6, 5, 4, 3, 2, 1 (same order as the names above), and 0 (FFmpeg automatic)",
    "settings.preset_help_hevc_amf": "HEVC AMF presets (speed → quality):\nspeed, balanced (default), quality",
    "settings.preset_help_av1_amf": "AV1 AMF presets (speed → quality):\nspeed, balanced (default), quality, high_quality\nhigh_quality may require a recent FFmpeg build and AMF driver.",
    "settings.preset_help_svtav1": "SVT-AV1 presets: -2 (FFmpeg/library automatic), -1 (quality-reference/very slow), and 0 (highest compression efficiency) through 13 (fastest/lowest compression efficiency)\nAll options: -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8 (default), 9, 10, 11, 12, 13\nThe maximum and special-value behavior depend on the FFmpeg/SVT-AV1 version.",
    "settings.preset_help_libaom": "libaom-AV1 presets (cpu-used): 0 (slowest/highest compression efficiency) through 8 (fastest/lowest compression efficiency)\nAll options: 0, 1, 2, 3, 4, 5, 6 (default), 7, 8",
    "settings.preset_unsupported": "{encoder} does not provide an FFmpeg -preset option that can be used from this menu.",
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
    "record.config_reload_kept": "Could not reload settings from {file_path}. Keeping the current settings.",
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
    "record.streamlink_reconnect": "Reconnecting to {channel_name} in {delay} seconds (consecutive failure {attempt}).",
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
    "settings.hevc_menu": "1. 切换启用/禁用\n2. 设置编码器（libx265、hevc_nvenc、hevc_qsv 等）\n3. 设置目标码率（例如 6000k）\n4. 设置最大码率（例如 8000k）\n5. 设置预设（显示该编码器的全部选项）\n6. 返回",
    "settings.av1_menu": "1. 切换启用/禁用\n2. 设置编码器（libsvtav1、libaom-av1、av1_nvenc 等）\n3. 设置目标码率（例如 6000k）\n4. 设置最大码率（例如 8000k）\n5. 设置预设（显示该编码器的全部选项）\n6. 返回",
    "settings.encoding_toggled": "{codec} 编码已{state}。",
    "settings.available_encoders": "\n可用编码器：",
    "settings.prompt_encoder": "请输入编码器名称：",
    "settings.invalid_encoder": "编码器名称无效。",
    "settings.prompt_target_bitrate": "请输入目标码率（例如 6000k）：",
    "settings.prompt_max_bitrate": "请输入最大码率（例如 10000k）：",
    "settings.preset_help_x265": "libx265 预设（速度快/压缩效率低 → 速度慢/压缩效率高）：\nultrafast → superfast → veryfast → faster → fast → medium → slow → slower → veryslow → placebo\nplacebo 的处理开销极高，不建议用于普通录制。",
    "settings.preset_help_hevc_nvenc": "HEVC NVENC 推荐预设：\np1（最快/画质最低）、p2（较快/画质较低）、p3（快速）、p4（均衡/默认）、p5（较慢/画质良好）、p6（更慢/画质更好）、p7（最慢/画质最佳）\n因 FFmpeg 版本而异的兼容别名：default、slow、medium、fast、hp、hq、bd、ll、llhq、llhp、lossless、losslesshp",
    "settings.preset_help_av1_nvenc": "AV1 NVENC 推荐预设：\np1（最快/画质最低）、p2（较快/画质较低）、p3（快速）、p4（均衡/默认）、p5（较慢/画质良好）、p6（更慢/画质更好）、p7（最慢/画质最佳）\n因 FFmpeg 版本而异的兼容别名：default、slow、medium、fast",
    "settings.preset_help_qsv": "QSV 预设（速度 → 画质）：\nveryfast、faster、fast、medium（默认）、slow、slower、veryslow\n数字选项：7、6、5、4、3、2、1（与上述名称顺序相同），以及 0（FFmpeg 自动值）",
    "settings.preset_help_hevc_amf": "HEVC AMF 预设（速度 → 画质）：\nspeed、balanced（默认）、quality",
    "settings.preset_help_av1_amf": "AV1 AMF 预设（速度 → 画质）：\nspeed、balanced（默认）、quality、high_quality\nhigh_quality 可能需要较新的 FFmpeg 版本和 AMF 驱动程序。",
    "settings.preset_help_svtav1": "SVT-AV1 预设：-2（FFmpeg/编码库自动值）、-1（画质参考/速度极慢），以及从 0（压缩效率最高）至 13（最快/压缩效率最低）\n全部选项：-2、-1、0、1、2、3、4、5、6、7、8（默认）、9、10、11、12、13\n最大值及特殊值的行为取决于 FFmpeg/SVT-AV1 版本。",
    "settings.preset_help_libaom": "libaom-AV1 预设（cpu-used）：0（最慢/压缩效率最高）至 8（最快/压缩效率最低）\n全部选项：0、1、2、3、4、5、6（默认）、7、8",
    "settings.preset_unsupported": "{encoder} 不提供可在此菜单中使用的 FFmpeg -preset 选项。",
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
    "settings.hevc_menu": "1. 切換啟用/停用\n2. 設定編碼器（libx265、hevc_nvenc、hevc_qsv 等）\n3. 設定目標位元率（例如 6000k）\n4. 設定最大位元率（例如 8000k）\n5. 設定預設（顯示該編碼器的全部選項）\n6. 返回",
    "settings.av1_menu": "1. 切換啟用/停用\n2. 設定編碼器（libsvtav1、libaom-av1、av1_nvenc 等）\n3. 設定目標位元率（例如 6000k）\n4. 設定最大位元率（例如 8000k）\n5. 設定預設（顯示該編碼器的全部選項）\n6. 返回",
    "settings.encoding_toggled": "{codec} 編碼已{state}。",
    "settings.available_encoders": "\n可用編碼器：",
    "settings.prompt_encoder": "請輸入編碼器名稱：",
    "settings.invalid_encoder": "編碼器名稱無效。",
    "settings.prompt_target_bitrate": "請輸入目標位元率（例如 6000k）：",
    "settings.prompt_max_bitrate": "請輸入最大位元率（例如 10000k）：",
    "settings.preset_help_x265": "libx265 預設（速度快/壓縮效率低 → 速度慢/壓縮效率高）：\nultrafast → superfast → veryfast → faster → fast → medium → slow → slower → veryslow → placebo\nplacebo 的處理成本極高，不建議用於一般錄製。",
    "settings.preset_help_hevc_nvenc": "HEVC NVENC 建議預設：\np1（最快/畫質最低）、p2（較快/畫質較低）、p3（快速）、p4（均衡/預設）、p5（較慢/畫質良好）、p6（更慢/畫質更好）、p7（最慢/畫質最佳）\n依 FFmpeg 版本而異的相容別名：default、slow、medium、fast、hp、hq、bd、ll、llhq、llhp、lossless、losslesshp",
    "settings.preset_help_av1_nvenc": "AV1 NVENC 建議預設：\np1（最快/畫質最低）、p2（較快/畫質較低）、p3（快速）、p4（均衡/預設）、p5（較慢/畫質良好）、p6（更慢/畫質更好）、p7（最慢/畫質最佳）\n依 FFmpeg 版本而異的相容別名：default、slow、medium、fast",
    "settings.preset_help_qsv": "QSV 預設（速度 → 畫質）：\nveryfast、faster、fast、medium（預設）、slow、slower、veryslow\n數字選項：7、6、5、4、3、2、1（與上述名稱順序相同），以及 0（FFmpeg 自動值）",
    "settings.preset_help_hevc_amf": "HEVC AMF 預設（速度 → 畫質）：\nspeed、balanced（預設）、quality",
    "settings.preset_help_av1_amf": "AV1 AMF 預設（速度 → 畫質）：\nspeed、balanced（預設）、quality、high_quality\nhigh_quality 可能需要較新的 FFmpeg 版本與 AMF 驅動程式。",
    "settings.preset_help_svtav1": "SVT-AV1 預設：-2（FFmpeg/編碼庫自動值）、-1（畫質參考/速度極慢），以及從 0（壓縮效率最高）至 13（最快/壓縮效率最低）\n全部選項：-2、-1、0、1、2、3、4、5、6、7、8（預設）、9、10、11、12、13\n最大值及特殊值的行為取決於 FFmpeg/SVT-AV1 版本。",
    "settings.preset_help_libaom": "libaom-AV1 預設（cpu-used）：0（最慢/壓縮效率最高）至 8（最快/壓縮效率最低）\n全部選項：0、1、2、3、4、5、6（預設）、7、8",
    "settings.preset_unsupported": "{encoder} 不提供可在此選單中使用的 FFmpeg -preset 選項。",
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
    "settings.hevc_menu": "1. 有効/無効を切り替え\n2. エンコーダーを設定 (libx265, hevc_nvenc, hevc_qsv など)\n3. 目標ビットレートを設定 (例: 6000k)\n4. 最大ビットレートを設定 (例: 8000k)\n5. プリセットを設定 (エンコーダーごとの全オプションを表示)\n6. 戻る",
    "settings.av1_menu": "1. 有効/無効を切り替え\n2. エンコーダーを設定 (libsvtav1, libaom-av1, av1_nvenc など)\n3. 目標ビットレートを設定 (例: 6000k)\n4. 最大ビットレートを設定 (例: 8000k)\n5. プリセットを設定 (エンコーダーごとの全オプションを表示)\n6. 戻る",
    "settings.encoding_toggled": "{codec} エンコードを{state}にしました。",
    "settings.available_encoders": "\n使用可能なエンコーダー:",
    "settings.prompt_encoder": "エンコーダー名を入力してください: ",
    "settings.invalid_encoder": "エンコーダー名が無効です。",
    "settings.prompt_target_bitrate": "目標ビットレートを入力してください (例: 6000k): ",
    "settings.prompt_max_bitrate": "最大ビットレートを入力してください (例: 10000k): ",
    "settings.preset_help_x265": "libx265 プリセット（高速/低圧縮効率 → 低速/高圧縮効率）：\nultrafast → superfast → veryfast → faster → fast → medium → slow → slower → veryslow → placebo\nplacebo は処理負荷が非常に高いため、通常の録画には推奨しません。",
    "settings.preset_help_hevc_nvenc": "HEVC NVENC 推奨プリセット：\np1（最速/最低画質）、p2（より高速/低画質）、p3（高速）、p4（バランス/既定値）、p5（低速/高画質）、p6（より低速/より高画質）、p7（最低速/最高画質）\nFFmpeg のバージョンによって異なる互換エイリアス：default、slow、medium、fast、hp、hq、bd、ll、llhq、llhp、lossless、losslesshp",
    "settings.preset_help_av1_nvenc": "AV1 NVENC 推奨プリセット：\np1（最速/最低画質）、p2（より高速/低画質）、p3（高速）、p4（バランス/既定値）、p5（低速/高画質）、p6（より低速/より高画質）、p7（最低速/最高画質）\nFFmpeg のバージョンによって異なる互換エイリアス：default、slow、medium、fast",
    "settings.preset_help_qsv": "QSV プリセット（速度 → 画質）：\nveryfast、faster、fast、medium（既定値）、slow、slower、veryslow\n数値オプション：7、6、5、4、3、2、1（上記の名前と同じ順序）、および 0（FFmpeg の自動値）",
    "settings.preset_help_hevc_amf": "HEVC AMF プリセット（速度 → 画質）：\nspeed、balanced（既定値）、quality",
    "settings.preset_help_av1_amf": "AV1 AMF プリセット（速度 → 画質）：\nspeed、balanced（既定値）、quality、high_quality\nhigh_quality には新しい FFmpeg ビルドと AMF ドライバーが必要な場合があります。",
    "settings.preset_help_svtav1": "SVT-AV1 プリセット：-2（FFmpeg/ライブラリの自動値）、-1（画質リファレンス/非常に低速）、および 0（最高圧縮効率）から 13（最速/最低圧縮効率）まで\n全オプション：-2、-1、0、1、2、3、4、5、6、7、8（既定値）、9、10、11、12、13\n最大値と特殊値の動作は FFmpeg/SVT-AV1 のバージョンによって異なります。",
    "settings.preset_help_libaom": "libaom-AV1 プリセット（cpu-used）：0（最低速/最高圧縮効率）から 8（最速/最低圧縮効率）まで\n全オプション：0、1、2、3、4、5、6（既定値）、7、8",
    "settings.preset_unsupported": "{encoder} には、このメニューで使用できる FFmpeg の -preset オプションがありません。",
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
    "record.config_reload_kept": "无法从 {file_path} 重新加载设置。将保留当前设置。",
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
    "record.streamlink_reconnect": "将在 {delay} 秒后重新连接 {channel_name}（连续失败 {attempt} 次）。",
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
    "record.config_reload_kept": "無法從 {file_path} 重新載入設定。將保留目前設定。",
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
    "record.streamlink_reconnect": "將在 {delay} 秒後重新連線 {channel_name}（連續失敗 {attempt} 次）。",
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
    "record.config_reload_kept": "{file_path} から設定を再読み込みできませんでした。現在の設定を維持します。",
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
    "record.streamlink_reconnect": "{delay} 秒後に {channel_name} へ再接続します（連続失敗 {attempt} 回）。",
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

# GUI labels and help are kept together so every supported locale stays complete.
_GUI_TEXT = {
    "title": ("치지직 레코다", "CHZZK Rekoda", "CHZZK 录制器", "CHZZK 錄製器", "CHZZK レコーダー"),
    "home": ("홈", "Home", "主页", "首頁", "ホーム"),
    "channels": ("채널", "Channels", "频道", "頻道", "チャンネル"),
    "settings": ("녹화 설정", "Recording settings", "录制设置", "錄製設定", "録画設定"),
    "help": ("도움말", "Help", "帮助", "說明", "ヘルプ"),
    "start": ("자동 녹화 시작", "Start recording", "开始自动录制", "開始自動錄製", "自動録画開始"),
    "stop": ("안전한 중지", "Stop safely", "安全停止", "安全停止", "安全に停止"),
    "add": ("채널 추가", "Add channel", "添加频道", "新增頻道", "チャンネル追加"),
    "edit": ("채널 편집", "Edit channel", "编辑频道", "編輯頻道", "チャンネル編集"),
    "remove": ("등록 해제", "Unregister", "取消注册", "取消註冊", "登録解除"),
    "folder": ("저장 폴더 열기", "Open storage folder", "打开保存文件夹", "開啟儲存資料夾", "保存フォルダーを開く"),
    "browse": ("폴더 선택", "Choose folder", "选择文件夹", "選擇資料夾", "フォルダーを選択"),
    "refresh": ("채널 정보 갱신", "Refresh channels", "刷新频道信息", "更新頻道資訊", "チャンネル情報を更新"),
    "search": ("검색", "Search", "搜索", "搜尋", "検索"),
    "by_name": ("채널 이름 검색", "Search by name", "按名称搜索", "依名稱搜尋", "名前で検索"),
    "by_id": ("채널 ID 조회", "Look up channel ID", "查询频道 ID", "查詢頻道 ID", "ID で照会"),
    "query": ("이름 또는 채널 ID", "Name or channel ID", "名称或频道 ID", "名稱或頻道 ID", "名前またはチャンネル ID"),
    "name": ("표시 이름", "Display name", "显示名称", "顯示名稱", "表示名"),
    "id": ("채널 ID", "Channel ID", "频道 ID", "頻道 ID", "チャンネル ID"),
    "path": ("저장 폴더", "Storage folder", "保存文件夹", "儲存資料夾", "保存フォルダー"),
    "delay": ("시작 지연 (초)", "Start delay (seconds)", "启动延迟（秒）", "啟動延遲（秒）", "開始遅延（秒）"),
    "active": ("자동 녹화 사용", "Enable automatic recording", "启用自动录制", "啟用自動錄製", "自動録画を有効にする"),
    "status": ("상태", "Status", "状态", "狀態", "状態"),
    "waiting": ("방송 대기", "Waiting for broadcast", "等待直播", "等待直播", "配信待機"),
    "recording": ("녹화 중", "Recording", "正在录制", "錄製中", "録画中"),
    "stopping": ("파일 저장 후 종료 중…", "Finishing files and stopping…", "正在保存文件并停止…", "正在儲存檔案並停止…", "ファイルを保存して終了中…"),
    "inactive": ("자동 녹화 꺼짐", "Automatic recording off", "自动录制已关闭", "自動錄製已關閉", "自動録画オフ"),
    "idle": ("중지됨", "Stopped", "已停止", "已停止", "停止中"),
    "starting": ("시작 중…", "Starting…", "正在启动…", "正在啟動…", "起動中…"),
    "running": ("자동 녹화 실행 중", "Automatic recording running", "自动录制运行中", "自動錄製執行中", "自動録画実行中"),
    "duration": ("녹화 시간", "Duration", "录制时间", "錄製時間", "録画時間"),
    "size": ("용량", "Size", "大小", "大小", "サイズ"),
    "speed": ("다운로드 속도", "Download speed", "下载速度", "下載速度", "ダウンロード速度"),
    "preview": ("녹화 영상 미리보기", "Recording preview", "录制画面预览", "錄製畫面預覽", "録画プレビュー"),
    "preview_enabled": ("미리보기 사용", "Enable preview", "启用预览", "啟用預覽", "プレビューを有効にする"),
    "preview_hint": ("녹화 중인 파일의 화면을 5초마다 갱신합니다. 소리는 재생하지 않습니다.", "Updates a frame from the recording file every 5 seconds. Audio is not played.", "每 5 秒更新正在录制的文件画面，不播放声音。", "每 5 秒更新正在錄製的檔案畫面，不播放聲音。", "録画中のファイルから5秒ごとに画像を更新します。音声は再生しません。"),
    "preview_wait": ("녹화 데이터가 쌓이면 미리보기가 표시됩니다.", "The preview appears when recorded data is available.", "录制数据可用后将显示预览。", "錄製資料可用後將顯示預覽。", "録画データが蓄積されると表示されます。"),
    "preview_select": ("녹화 중인 채널을 선택하세요.", "Select a recording channel.", "请选择正在录制的频道。", "請選擇正在錄製的頻道。", "録画中のチャンネルを選択してください。"),
    "preview_updated": ("마지막 화면 갱신: {time}", "Last frame update: {time}", "最后画面更新：{time}", "最後畫面更新：{time}", "最終画像更新: {time}"),
    "preview_failed": ("현재 프레임을 읽지 못했습니다. 다음 갱신 때 다시 시도합니다.", "Cannot read the current frame. Retrying on the next update.", "无法读取当前帧，将在下次更新时重试。", "無法讀取目前影格，將於下次更新時重試。", "現在のフレームを取得できません。次の更新で再試行します。"),
    "empty": ("채널을 추가하고 저장 위치를 확인한 뒤 자동 녹화를 시작하세요.", "Add a channel, choose a folder, then start automatic recording.", "添加频道并确认保存位置，然后开始自动录制。", "新增頻道並確認儲存位置，然後開始自動錄製。", "チャンネルを追加し保存先を確認してから自動録画を開始してください。"),
    "icons_hint": ("CHZZK 프로필 이미지가 있으면 표시합니다. 조회할 수 없으면 이름의 첫 글자를 표시합니다.", "Shows the CHZZK profile image when available, otherwise the first character of the name.", "显示可用的 CHZZK 头像，否则显示名称首字。", "顯示可用的 CHZZK 頭像，否則顯示名稱首字。", "CHZZK のプロフィール画像を表示し、取得できない場合は名前の先頭文字を表示します。"),
    "fetching": ("채널 정보를 조회하는 중…", "Looking up channel information…", "正在查询频道信息…", "正在查詢頻道資訊…", "チャンネル情報を取得中…"),
    "icon_unavailable": ("프로필 이미지를 조회하지 못한 채널은 기본 아이콘으로 표시합니다.", "Channels without an available profile image use a fallback icon.", "无法获取头像的频道显示默认图标。", "無法取得頭像的頻道顯示預設圖示。", "プロフィール画像を取得できないチャンネルは代替アイコンを表示します。"),
    "save": ("설정 저장", "Save settings", "保存设置", "儲存設定", "設定を保存"),
    "cancel": ("취소", "Cancel", "取消", "取消", "キャンセル"),
    "close": ("닫기", "Close", "关闭", "關閉", "閉じる"),
    "discard": ("변경 버리기", "Discard changes", "放弃更改", "捨棄變更", "変更を破棄"),
    "unsaved": ("저장하지 않은 설정 변경을 버릴까요?", "Discard unsaved settings changes?", "放弃未保存的设置更改吗？", "要捨棄未儲存的設定變更嗎？", "未保存の設定変更を破棄しますか？"),
    "saved": ("설정을 저장했습니다.", "Settings saved.", "设置已保存。", "設定已儲存。", "設定を保存しました。"),
    "error": ("확인이 필요합니다", "Attention required", "需要确认", "需要確認", "確認が必要です"),
    "config_conflict": ("다른 창이나 CLI에서 설정을 변경했습니다. 다시 열어 최신 설정을 불러온 뒤 수정하세요.", "Another window or CLI changed the settings. Reopen settings to load the latest version before editing.", "其他窗口或 CLI 已更改设置。请重新打开设置加载最新版本后再编辑。", "其他視窗或 CLI 已變更設定。請重新開啟設定載入最新版本後再編輯。", "別のウィンドウや CLI が設定を変更しました。設定を開き直して最新版を読み込んでください。"),
    "recorder_busy": ("이 프로젝트의 녹화기가 이미 실행 중입니다. 기존 CLI 또는 GUI 녹화를 먼저 중지하세요.", "A recorder is already running for this project. Stop the existing CLI or GUI recorder first.", "此项目的录制器已在运行，请先停止现有 CLI 或 GUI 录制。", "此專案的錄製器已在執行，請先停止現有 CLI 或 GUI 錄製。", "このプロジェクトの録画が実行中です。既存の CLI または GUI 録画を先に停止してください。"),
    "protocol_error": ("녹화기 상태 응답을 읽지 못했습니다.", "Cannot read the recorder status response.", "无法读取录制器状态响应。", "無法讀取錄製器狀態回應。", "録画プロセスの状態応答を読み取れません。"),
    "start_failed": ("녹화기를 시작하지 못했습니다. 설치 상태를 확인하세요.", "Could not start the recorder. Check the installation.", "无法启动录制器，请检查安装。", "無法啟動錄製器，請檢查安裝。", "録画プロセスを起動できません。インストールを確認してください。"),
    "recorder_failed": ("녹화기가 오류로 종료되었습니다. 활동 로그를 확인하세요.", "The recorder exited with an error. Check the activity log.", "录制器因错误退出，请检查活动日志。", "錄製器因錯誤結束，請檢查活動記錄。", "録画プロセスがエラーで終了しました。ログを確認してください。"),
    "remove_confirm": ("{name} 채널의 등록을 해제할까요? 녹화 파일은 유지됩니다. 진행 중인 녹화는 안전하게 종료됩니다.", "Unregister {name}? Recorded files are kept. Any current recording will stop safely.", "取消注册 {name} 吗？已录制文件会保留，当前录制将安全停止。", "取消註冊 {name} 嗎？已錄製檔案會保留，目前錄製將安全停止。", "{name} の登録を解除しますか？録画ファイルは残り、録画中の場合は安全に終了します。"),
    "required": ("이름과 저장 폴더를 입력하세요.", "Enter a name and storage folder.", "请输入名称和保存文件夹。", "請輸入名稱和儲存資料夾。", "名前と保存フォルダーを入力してください。"),
    "select_channel": ("채널을 선택하세요.", "Select a channel.", "请选择频道。", "請選擇頻道。", "チャンネルを選択してください。"),
    "basic": ("기본 녹화", "Basic recording", "基本录制", "基本錄製", "基本録画"),
    "hevc": ("HEVC (H.265)", "HEVC (H.265)", "HEVC (H.265)", "HEVC (H.265)", "HEVC (H.265)"),
    "av1": ("AV1", "AV1", "AV1", "AV1", "AV1"),
    "auth": ("네이버 로그인", "NAVER login", "NAVER 登录", "NAVER 登入", "NAVER ログイン"),
    "network": ("네트워크", "Network", "网络", "網路", "ネットワーク"),
    "app": ("언어 · 로그", "Language · logs", "语言 · 日志", "語言 · 記錄", "言語・ログ"),
    "format": ("파일 형식", "File format", "文件格式", "檔案格式", "ファイル形式"),
    "split": ("파일 분할 간격", "File split interval", "文件分割间隔", "檔案分割間隔", "ファイル分割間隔"),
    "off": ("사용 안 함", "Off", "不使用", "不使用", "使用しない"),
    "minutes": ("분", "Minutes", "分钟", "分鐘", "分"),
    "hours": ("시간", "Hours", "小时", "小時", "時間"),
    "timeout": ("방송 확인 간격 (초)", "Broadcast check interval (seconds)", "直播检查间隔（秒）", "直播檢查間隔（秒）", "配信確認間隔（秒）"),
    "threads": ("다운로드 스레드 수", "Download threads", "下载线程数", "下載執行緒數", "ダウンロードスレッド数"),
    "enabled": ("인코딩 사용", "Enable encoding", "启用编码", "啟用編碼", "エンコードを有効にする"),
    "encoder": ("사용할 인코더", "Encoder", "编码器", "編碼器", "エンコーダー"),
    "preset": ("속도 · 품질 프리셋", "Speed · quality preset", "速度 · 质量预设", "速度 · 品質預設", "速度・品質プリセット"),
    "auto": ("자동 (직접 선택 없음)", "Automatic (no manual preset)", "自动（无手动预设）", "自動（無手動預設）", "自動（手動選択なし）"),
    "bitrate": ("목표 비트레이트", "Target bitrate", "目标码率", "目標位元率", "目標ビットレート"),
    "max_bitrate": ("최대 비트레이트", "Maximum bitrate", "最大码率", "最大位元率", "最大ビットレート"),
    "browser": ("브라우저", "Browser", "浏览器", "瀏覽器", "ブラウザー"),
    "login": ("브라우저로 로그인", "Log in using browser", "使用浏览器登录", "使用瀏覽器登入", "ブラウザーでログイン"),
    "login_wait": ("열린 브라우저에서 3분 이내에 로그인하세요. 쿠키를 확인하면 자동으로 가져옵니다.", "Log in in the new browser within 3 minutes. Cookies are imported automatically when found.", "请在新打开的浏览器中于 3 分钟内登录，检测到 Cookie 后将自动导入。", "請在新開啟的瀏覽器中於 3 分鐘內登入，偵測到 Cookie 後將自動匯入。", "開いたブラウザーで3分以内にログインしてください。Cookie を検出すると自動で取得します。"),
    "login_failed": ("로그인 쿠키를 가져오지 못했습니다. 브라우저 설치와 로그인 상태를 확인하거나 직접 입력하세요.", "Could not import login cookies. Check the browser and login, or enter them manually.", "无法导入登录 Cookie，请检查浏览器和登录状态或手动输入。", "無法匯入登入 Cookie，請檢查瀏覽器和登入狀態或手動輸入。", "ログイン Cookie を取得できません。ブラウザーとログイン状態を確認するか手動で入力してください。"),
    "login_received": ("쿠키를 가져왔습니다. 설정 저장을 눌러 적용하세요.", "Cookies imported. Save settings to apply them.", "Cookie 已导入，请保存设置以应用。", "Cookie 已匯入，請儲存設定以套用。", "Cookie を取得しました。設定を保存して適用してください。"),
    "login_cancel": ("로그인 취소", "Cancel login", "取消登录", "取消登入", "ログインをキャンセル"),
    "show_cookies": ("쿠키 표시", "Show cookies", "显示 Cookie", "顯示 Cookie", "Cookie を表示"),
    "clear_cookies": ("쿠키 삭제", "Clear cookies", "清除 Cookie", "清除 Cookie", "Cookie を削除"),
    "doh_enabled": ("DNS-over-HTTPS 사용", "Use DNS-over-HTTPS", "使用 DNS-over-HTTPS", "使用 DNS-over-HTTPS", "DNS-over-HTTPS を使用"),
    "doh_url": ("DNS-over-HTTPS 주소", "DNS-over-HTTPS URL", "DNS-over-HTTPS 地址", "DNS-over-HTTPS 位址", "DNS-over-HTTPS URL"),
    "restore": ("기본 주소로 복원", "Restore default URL", "恢复默认地址", "還原預設位址", "既定の URL に戻す"),
    "language": ("프로그램 언어", "Application language", "程序语言", "程式語言", "表示言語"),
    "log_enabled": ("로그 파일 저장", "Save log file", "保存日志文件", "儲存記錄檔", "ログファイルを保存"),
    "logs": ("활동 로그", "Activity log", "活动日志", "活動記錄", "アクティビティログ"),
    "copy": ("로그 복사", "Copy log", "复制日志", "複製記錄", "ログをコピー"),
    "clear": ("화면 로그 비우기", "Clear displayed log", "清空显示日志", "清空顯示記錄", "表示ログを消去"),
    "apply_hint": ("저장한 녹화 옵션은 다음 녹화 작업부터 적용됩니다. 실행 중인 녹화기의 DNS·로그 설정은 중지 후 다시 시작하면 적용됩니다.", "Recording options apply to new recording tasks. Restart the recorder to apply DNS and file logging changes.", "录制选项将应用于新的录制任务。DNS 和文件日志更改需重新启动录制器。", "錄製選項將套用至新的錄製工作。DNS 與檔案記錄變更需重新啟動錄製器。", "録画設定は新しい録画タスクに適用されます。DNS とログ保存の変更は録画プロセスの再起動後に適用されます。"),
    "format_help": ("TS·MKV·WebM을 지원합니다. AV1을 TS로 저장하도록 선택하면 실제 녹화 시 MKV로 전환합니다.", "Supports TS, MKV and WebM. AV1 recording uses MKV when TS is selected.", "支持 TS、MKV 和 WebM。AV1 在选择 TS 时会使用 MKV。", "支援 TS、MKV 與 WebM。AV1 在選擇 TS 時會使用 MKV。", "TS・MKV・WebM に対応します。AV1 で TS を選ぶと MKV に切り替わります。"),
    "split_help": ("긴 녹화를 정해진 간격으로 나눕니다. 최대 10080분(168시간). 분할 안 함은 한 파일로 저장합니다.", "Splits recordings at the chosen interval, up to 10080 minutes (168 hours). Off saves a single file.", "按指定间隔分割录制，最多 10080 分钟（168 小时）。关闭时保存为单个文件。", "依指定間隔分割錄製，最多 10080 分鐘（168 小時）。關閉時儲存為單一檔案。", "指定間隔で録画を分割します。最大10080分（168時間）。オフでは1つのファイルに保存します。"),
    "timeout_help": ("방송 시작 여부를 다시 확인하는 간격입니다. 1~3600초, 기본 60초입니다.", "Interval for checking whether a broadcast has started: 1–3600 seconds, default 60.", "检查直播是否开始的间隔：1–3600 秒，默认 60 秒。", "檢查直播是否開始的間隔：1–3600 秒，預設 60 秒。", "配信開始を再確認する間隔です。1～3600秒、既定値60秒。"),
    "threads_help": ("영상 조각을 동시에 받는 작업 수입니다. 1~16, 기본 2이며 녹화 채널 수와는 다릅니다.", "Concurrent video-segment downloads: 1–16, default 2. This is not the channel count.", "并发下载视频分片的数量：1–16，默认 2，并非频道数量。", "同時下載影片片段的數量：1–16，預設 2，並非頻道數量。", "動画セグメントを同時に取得する数です。1～16、既定値2。録画チャンネル数ではありません。"),
    "enabled_help": ("HEVC와 AV1 중 한 가지만 켤 수 있습니다. 한쪽을 켜면 다른 쪽이 꺼집니다.", "Only one of HEVC and AV1 can be enabled. Enabling one disables the other.", "HEVC 和 AV1 只能启用一个，启用其中一个将关闭另一个。", "HEVC 與 AV1 只能啟用一個，啟用其中一個將關閉另一個。", "HEVC と AV1 はどちらか一方のみ有効にできます。片方を有効にすると他方は無効になります。"),
    "encoder_help": ("CPU 또는 그래픽 장치에 맞게 선택합니다. 녹화기는 실제 사용 가능 여부를 검사하고 필요하면 소프트웨어로 전환합니다.", "Choose a CPU or GPU encoder. The recorder probes availability and falls back to software when needed.", "选择 CPU 或 GPU 编码器。录制器会检测可用性，并在需要时回退到软件编码。", "選擇 CPU 或 GPU 編碼器。錄製器會檢測可用性，並於需要時改用軟體編碼。", "CPU または GPU のエンコーダーを選びます。利用可否を検査し、必要に応じてソフトウェアに切り替えます。"),
    "preset_help": ("인코더가 지원하는 속도·품질 단계입니다. VAAPI와 VideoToolbox는 직접 프리셋을 선택하지 않습니다.", "Encoder-specific speed and quality levels. VAAPI and VideoToolbox have no manual preset.", "编码器支持的速度和质量等级。VAAPI 和 VideoToolbox 无手动预设。", "編碼器支援的速度與品質等級。VAAPI 與 VideoToolbox 無手動預設。", "エンコーダーごとの速度・品質設定です。VAAPI と VideoToolbox には手動プリセットがありません。"),
    "bitrate_help": ("예: 2500k, 5m. 숫자만 입력하면 k 단위를 사용합니다. 기본 목표 2500k, 최대 10000k입니다.", "Examples: 2500k, 5m. Numbers without a unit use k. Defaults: target 2500k, maximum 10000k.", "示例：2500k、5m。仅数字使用 k 单位。默认目标 2500k，最大 10000k。", "範例：2500k、5m。僅數字使用 k 單位。預設目標 2500k，最大 10000k。", "例: 2500k、5m。数字のみなら k 単位です。既定値は目標2500k、最大10000k。"),
    "cookie_help": ("네이버 인증 쿠키입니다. 직접 입력하거나 새 브라우저에서 로그인해 가져올 수 있습니다. 다른 사람에게 공유하지 마세요.", "NAVER authentication cookies. Enter manually or import by logging in through a new browser. Do not share them.", "NAVER 身份验证 Cookie，可手动输入或通过新浏览器登录导入，请勿共享。", "NAVER 驗證 Cookie，可手動輸入或透過新瀏覽器登入匯入，請勿分享。", "NAVER 認証 Cookie です。手動入力または新しいブラウザーでログインして取得できます。他人と共有しないでください。"),
    "dns_help": ("DNS 요청을 HTTPS로 전송합니다. 유효한 HTTPS 주소가 필요하며 변경 후 녹화기를 다시 시작하세요.", "Sends DNS requests over HTTPS. Requires a valid HTTPS URL. Restart the recorder after changing this.", "通过 HTTPS 发送 DNS 请求，需要有效的 HTTPS 地址。更改后请重启录制器。", "透過 HTTPS 傳送 DNS 請求，需要有效的 HTTPS 位址。變更後請重新啟動錄製器。", "DNS を HTTPS で送信します。有効な HTTPS URL が必要です。変更後は録画プロセスを再起動してください。"),
    "language_help": ("한국어·영어·중국어 간체/정체·일본어를 지원합니다. 저장하면 화면 언어가 바뀝니다.", "Supports Korean, English, Simplified and Traditional Chinese, and Japanese. Save to change the interface language.", "支持韩语、英语、简繁中文和日语，保存后切换界面语言。", "支援韓語、英語、簡繁中文與日語，儲存後切換介面語言。", "韓国語・英語・簡体字中国語・繁体字中国語・日本語に対応。保存すると表示言語が変わります。"),
    "log_help": ("녹화 작업과 오류를 로그 파일에 저장합니다. 변경 후 녹화기를 다시 시작하세요. 화면 로그는 계속 표시됩니다.", "Saves recording activity and errors to a file. Restart the recorder after changing this. On-screen logs remain available.", "将录制活动和错误保存至文件，更改后重启录制器。屏幕日志仍会显示。", "將錄製活動與錯誤儲存至檔案，變更後重新啟動錄製器。畫面記錄仍會顯示。", "録画処理とエラーをファイルに保存します。変更後は再起動してください。画面ログは引き続き表示されます。"),
    "channel_help": ("채널별 이름·저장 폴더·자동 녹화·시작 지연(0~3600초)을 설정합니다. ID는 등록 후 바뀌지 않습니다.", "Set each channel's name, folder, automatic recording and start delay (0–3600 seconds). The ID is fixed after registration.", "设置频道名称、文件夹、自动录制和启动延迟（0–3600 秒）。注册后 ID 不变。", "設定頻道名稱、資料夾、自動錄製與啟動遲延（0–3600 秒）。註冊後 ID 不變。", "名前・保存先・自動録画・開始遅延（0～3600秒）を設定します。登録後の ID は変更できません。"),
    "quick_help": ("채널 추가 → 저장 위치 확인 → 자동 녹화 시작 순서로 사용하세요. 중지 또는 창 닫기는 녹화 파일을 정리한 뒤 완료됩니다. 설정 위에 잠시 포인터를 두거나 F1을 누르면 설명을 볼 수 있습니다.", "Add a channel, choose a folder, then start recording. Stopping or closing the window waits for recording files to finish. Hover over a setting or press F1 for help.", "添加频道、确认保存位置，然后开始录制。停止或关闭窗口会等待文件整理完成。悬停设置或按 F1 查看帮助。", "新增頻道、確認儲存位置，然後開始錄製。停止或關閉視窗會等待檔案整理完成。將游標停留於設定或按 F1 查看說明。", "チャンネル追加、保存先確認、自動録画開始の順に使います。停止やウィンドウを閉じる操作ではファイルの保存完了を待ちます。設定にポインターを置くか F1 を押すと説明を表示します。"),
    "invalid_bitrate": ("비트레이트를 2500k 또는 5m 형식으로 입력하세요.", "Enter a bitrate such as 2500k or 5m.", "请以 2500k 或 5m 格式输入码率。", "請以 2500k 或 5m 格式輸入位元率。", "2500k や 5m の形式でビットレートを入力してください。"),
    "invalid_doh": ("유효한 HTTPS 주소를 입력하세요.", "Enter a valid HTTPS URL.", "请输入有效的 HTTPS 地址。", "請輸入有效的 HTTPS 位址。", "有効な HTTPS URL を入力してください。"),
    "missing_qt": ("GUI 의존성이 필요합니다: uv sync --extra gui 실행 후 다시 시작하세요.", "GUI dependencies are required. Run uv sync --extra gui, then try again.", "需要 GUI 依赖项，请运行 uv sync --extra gui 后重试。", "需要 GUI 相依套件，請執行 uv sync --extra gui 後重試。", "GUI の依存関係が必要です。uv sync --extra gui を実行して再起動してください。"),
    "config_path": ("공유 설정 파일 경로", "Shared configuration file path", "共享设置文件路径", "共用設定檔路徑", "共有設定ファイルのパス"),
}

_GUI_TEXT.update({
    "broadcast_title": ("방송 제목", "Broadcast title", "直播标题", "直播標題", "配信タイトル"),
    "h264": ("H.264", "H.264", "H.264", "H.264", "H.264"),
    "quality": ("화질", "Quality", "画质", "畫質", "画質"),
    "quality_best": ("원본 최고 화질", "Best available", "最佳原始画质", "最佳原始畫質", "利用可能な最高画質"),
    "quality_custom": ("사용자 지정 해상도", "Custom resolution", "自定义分辨率", "自訂解析度", "解像度を指定"),
    "quality_original": ("원본 유지", "Keep original", "保持原始值", "保留原始值", "元のまま"),
    "width": ("가로 (픽셀)", "Width (pixels)", "宽度（像素）", "寬度（像素）", "幅（ピクセル）"),
    "height": ("세로 (픽셀)", "Height (pixels)", "高度（像素）", "高度（像素）", "高さ（ピクセル）"),
    "fps": ("프레임 속도 (FPS)", "Frame rate (FPS)", "帧率（FPS）", "影格率（FPS）", "フレームレート（FPS）"),
    "aspect_auto": ("원본 비율", "Original aspect ratio", "原始比例", "原始比例", "元の縦横比"),
    "inherit": ("전체 설정 사용", "Use global settings", "使用全局设置", "使用全域設定", "全体設定を使用"),
    "channel_split_help": ("채널마다 분할 간격을 설정합니다. 전체 설정 사용은 공통 간격을 따르고, 사용 안 함은 이 채널만 한 파일로 저장합니다. 새 녹화 작업부터 적용됩니다.", "Set a split interval per channel. Global follows the common interval; Off saves this channel in one file. Applies to new recording tasks.", "为每个频道设置分割间隔。全局选项使用公共间隔，关闭则此频道保存为单个文件。应用于新录制任务。", "為每個頻道設定分割間隔。全域選項使用共同間隔，關閉則此頻道儲存為單一檔案。套用至新的錄製工作。", "チャンネルごとに分割間隔を指定します。全体設定は共通間隔、オフは1ファイルに保存します。新しい録画タスクから適用されます。"),
    "quality_help": ("제공되는 화질은 직접 받습니다. 없는 해상도나 다른 FPS는 인코딩합니다. 같은 해상도가 있으면 그 영상을 받아 FPS만 변환합니다. 변환 시 선택한 인코더를 사용하며, 미선택 시 H.264(WebM은 VP9)를 사용합니다. 사용자 해상도는 짝수, FPS는 1~120 또는 원본 유지입니다.", "Available qualities are downloaded directly. Other resolutions or frame rates require encoding. Use the matching resolution when changing only FPS. Conversion uses the selected encoder, or H.264 by default (VP9 for WebM). Custom dimensions must be even; FPS is 1–120 or original.", "优先直接下载可用画质。其他分辨率或帧率需要编码，仅改变 FPS 时使用相同分辨率的视频。转换使用所选编码器，未选择时使用 H.264（WebM 为 VP9）。自定义尺寸须为偶数，FPS 为 1–120 或原始值。", "優先直接下載可用畫質。其他解析度或影格率需要編碼，僅變更 FPS 時使用相同解析度的影片。轉換使用所選編碼器，未選擇時使用 H.264（WebM 為 VP9）。自訂尺寸須為偶數，FPS 為 1–120 或原始值。", "提供される画質を直接取得します。別の解像度や FPS はエンコードします。FPS のみ変更する場合は同じ解像度を使用します。選択したエンコーダー、未選択なら H.264（WebM は VP9）を使います。寸法は偶数、FPS は1～120または元の値です。"),
    "invalid_quality": ("사용자 해상도는 짝수로, FPS는 1~120 또는 0(원본 유지)으로 입력하세요.", "Use even dimensions and FPS 1–120 or 0 to keep the original.", "请输入偶数尺寸，FPS 为 1–120 或 0（保持原始值）。", "請輸入偶數尺寸，FPS 為 1–120 或 0（保留原始值）。", "寸法は偶数、FPS は1～120または0（元のまま）を指定してください。"),
    "quality_unavailable": ("방송의 제공 화질을 확인하지 못했습니다. 잠시 후 다시 시도합니다.", "Could not determine available stream qualities. Retrying shortly.", "无法确定可用画质，稍后重试。", "無法確認可用畫質，稍後重試。", "提供画質を確認できません。しばらくして再試行します。"),
    "quality_selected": ("{channel_name}: 수신 화질 {quality}, 영상 처리: {filters}", "{channel_name}: source {quality}, video processing: {filters}", "{channel_name}：接收画质 {quality}，视频处理：{filters}", "{channel_name}：接收畫質 {quality}，影片處理：{filters}", "{channel_name}: 取得画質 {quality}、映像処理: {filters}"),
    "h264_fallback": ("{encoder}를 사용할 수 없어 H.264 소프트웨어 인코더로 전환합니다.", "{encoder} is unavailable; using the H.264 software encoder.", "{encoder} 不可用，改用 H.264 软件编码器。", "{encoder} 無法使用，改用 H.264 軟體編碼器。", "{encoder} を使用できないため H.264 ソフトウェアエンコーダーに切り替えます。"),
    "h264_unavailable": ("사용 가능한 H.264 인코더가 없습니다. FFmpeg 설치를 확인하세요.", "No usable H.264 encoder. Check the FFmpeg installation.", "没有可用的 H.264 编码器，请检查 FFmpeg 安装。", "沒有可用的 H.264 編碼器，請檢查 FFmpeg 安裝。", "使用可能な H.264 エンコーダーがありません。FFmpeg を確認してください。"),
    "h264_webm_fallback": ("H.264는 WebM에 저장할 수 없어 MKV로 저장합니다.", "H.264 cannot be stored in WebM; using MKV.", "WebM 不支持 H.264，使用 MKV 保存。", "WebM 不支援 H.264，使用 MKV 儲存。", "WebM は H.264 に対応しないため MKV に保存します。"),
    "title_save_failed": ("원본 방송 제목 TXT 저장 실패: {error}", "Could not save original title TXT: {error}", "原始标题 TXT 保存失败：{error}", "原始標題 TXT 儲存失敗：{error}", "元の配信タイトル TXT を保存できません: {error}"),
    "background": ("백그라운드로", "Background", "后台运行", "背景執行", "バックグラウンド"),
    "close_to_tray": ("창을 닫으면 백그라운드에서 계속 실행", "Keep running when the window closes", "关闭窗口后继续在后台运行", "關閉視窗後繼續在背景執行", "ウィンドウを閉じても実行を続ける"),
    "tray_help": ("창을 닫아도 녹화를 계속합니다. 시스템 트레이 아이콘으로 창을 다시 열거나 안전 종료할 수 있습니다. 트레이가 없는 환경에서는 창 닫기로 종료합니다.", "Recording continues when closing the window. Restore or safely quit from the system tray icon. Without a system tray, closing exits.", "关闭窗口后继续录制，可通过系统托盘图标恢复窗口或安全退出。无系统托盘时关闭窗口会退出。", "關閉視窗後繼續錄製，可透過系統匣圖示還原視窗或安全結束。無系統匣時關閉視窗會結束。", "閉じても録画を続けます。トレイアイコンから表示や安全終了ができます。トレイのない環境では閉じると終了します。"),
    "tray_unavailable": ("이 데스크톱에서 시스템 트레이를 사용할 수 없습니다. 창을 최소화하면 녹화를 계속할 수 있습니다.", "No system tray is available. Minimize the window to continue recording.", "此桌面不支持系统托盘，可最小化窗口继续录制。", "此桌面不支援系統匣，可最小化視窗繼續錄製。", "システムトレイを使用できません。ウィンドウを最小化すると録画を続けられます。"),
    "show_window": ("창 열기", "Show window", "显示窗口", "顯示視窗", "ウィンドウを表示"),
    "quit": ("안전 종료", "Quit safely", "安全退出", "安全結束", "安全に終了"),
    "login_driver_missing": ("브라우저 드라이버를 준비하지 못했습니다. 브라우저 설치와 인터넷 연결을 확인하세요.", "Could not prepare the browser driver. Check browser installation and internet access.", "无法准备浏览器驱动，请检查浏览器安装和网络。", "無法準備瀏覽器驅動，請檢查瀏覽器安裝與網路。", "ブラウザードライバーを準備できません。インストールとネット接続を確認してください。"),
    "login_browser_failed": ("브라우저를 시작하지 못했습니다. 선택한 브라우저와 드라이버 버전을 확인하세요.", "Could not start the browser. Check the selected browser and driver versions.", "无法启动浏览器，请检查所选浏览器及驱动版本。", "無法啟動瀏覽器，請檢查所選瀏覽器及驅動版本。", "ブラウザーを起動できません。ブラウザーとドライバーのバージョンを確認してください。"),
    "login_window_closed": ("쿠키를 가져오기 전에 로그인 창이 닫혔습니다. 다시 시도하세요.", "The login window closed before cookies were imported. Try again.", "导入 Cookie 前登录窗口已关闭，请重试。", "匯入 Cookie 前登入視窗已關閉，請重試。", "Cookie 取得前にログイン画面が閉じられました。再試行してください。"),
    "login_timeout": ("3분 안에 인증 쿠키를 확인하지 못했습니다. 로그인을 완료한 뒤 다시 시도하세요.", "Authentication cookies were not found within 3 minutes. Complete login and try again.", "3 分钟内未找到认证 Cookie，请完成登录后重试。", "3 分鐘內未找到驗證 Cookie，請完成登入後重試。", "3分以内に認証 Cookie を確認できませんでした。ログインを完了して再試行してください。"),
    "login_cancelled": ("로그인을 취소했습니다.", "Login cancelled.", "已取消登录。", "已取消登入。", "ログインをキャンセルしました。"),
    "enabled_help": ("H.264·HEVC·AV1 중 한 가지만 켤 수 있습니다. 다른 코덱을 켜면 기존 선택은 꺼집니다.", "Enable only one of H.264, HEVC and AV1. Selecting another codec disables the previous one.", "H.264、HEVC 和 AV1 只能启用一个，选择其他编码将关闭原选择。", "H.264、HEVC 與 AV1 只能啟用一個，選擇其他編碼將關閉原選擇。", "H.264・HEVC・AV1 の1つだけ有効にできます。別のコーデックを有効にすると前の選択は無効になります。"),
    "format_help": ("TS·MKV·WebM을 지원합니다. AV1+TS 또는 H.264+WebM은 MKV로 저장합니다.", "Supports TS, MKV and WebM. AV1 with TS or H.264 with WebM uses MKV.", "支持 TS、MKV 和 WebM。AV1+TS 或 H.264+WebM 将保存为 MKV。", "支援 TS、MKV 與 WebM。AV1+TS 或 H.264+WebM 將儲存為 MKV。", "TS・MKV・WebM に対応。AV1+TS または H.264+WebM は MKV で保存します。"),
    "app": ("앱 · 백그라운드", "App · background", "应用 · 后台", "應用程式 · 背景", "アプリ・バックグラウンド"),
    "quick_help": ("채널 추가 → 설정 → 자동 녹화 시작 순서로 사용하세요. 채널 우클릭으로 설정·삭제·폴더·활성화를 조정합니다. 백그라운드 실행 중에는 트레이 아이콘에서 안전 종료하세요. 설정 위에 포인터를 두거나 F1을 누르면 설명을 볼 수 있습니다.", "Add a channel, configure it, then start recording. Right-click a channel for settings, removal, folder and activation. Quit safely from the tray while in background. Hover or press F1 for help.", "添加频道、设置后开始录制。右键频道可设置、移除、打开文件夹或启停。后台运行时从托盘安全退出。悬停或按 F1 查看帮助。", "新增頻道、設定後開始錄製。右鍵頻道可設定、移除、開啟資料夾或啟停。背景執行時從系統匣安全結束。停留游標或按 F1 查看說明。", "チャンネル追加、設定、自動録画開始の順に使用します。右クリックで設定・削除・フォルダー・有効化を操作できます。バックグラウンドではトレイから安全終了します。ホバーまたは F1 で説明を表示します。"),
    "cli_extra_menu": ("10. H.264 인코딩\n11. 화질 설정", "10. H.264 encoding\n11. Quality settings", "10. H.264 编码\n11. 画质设置", "10. H.264 編碼\n11. 畫質設定", "10. H.264 エンコード\n11. 画質設定"),
    "cli_channel_options": ("5. 채널별 분할·화질 설정", "5. Per-channel split and quality", "5. 频道分割及画质", "5. 頻道分割及畫質", "5. チャンネル別の分割・画質"),
    "cli_split_prompt": ("분할 간격(분), 0=분할 안 함, -1=전체 설정: ", "Split minutes, 0=off, -1=global: ", "分割分钟数，0=关闭，-1=全局：", "分割分鐘數，0=關閉，-1=全域：", "分割間隔（分）、0=オフ、-1=全体設定: "),
    "cli_quality_prompt": ("화질(best/144p/360p/480p/720p60/1080p60/custom), 빈 입력=유지: ", "Quality (best/144p/360p/480p/720p60/1080p60/custom), blank=keep: ", "画质(best/144p/360p/480p/720p60/1080p60/custom)，留空保持：", "畫質(best/144p/360p/480p/720p60/1080p60/custom)，留空保留：", "画質(best/144p/360p/480p/720p60/1080p60/custom)、空欄=維持: "),
    "cli_quality_inherit": ("채널 화질: 1=전체 설정 사용, 2=별도 설정: ", "Channel quality: 1=global, 2=custom settings: ", "频道画质：1=全局，2=独立设置：", "頻道畫質：1=全域，2=獨立設定：", "チャンネル画質: 1=全体設定、2=個別設定: "),
})

_GUI_TEXT.update({
    "stop": ("녹화 중지", "Stop recording", "停止录制", "停止錄製", "録画を停止"),
    "quit": ("종료", "Quit", "退出", "結束", "終了"),
    "back": ("뒤로", "Back", "返回", "返回", "戻る"),
    "next": ("다음", "Next", "下一步", "下一步", "次へ"),
    "finish": ("완료", "Finish", "完成", "完成", "完了"),
    "setup": ("처음 설정", "Getting started", "初始设置", "初始設定", "初期設定"),
    "setup_language": ("사용할 언어를 선택하세요", "Choose your language", "选择使用语言", "選擇使用語言", "言語を選択してください"),
    "setup_language_help": ("언어와 녹화할 채널을 순서대로 설정합니다. 나중에 설정에서 변경할 수 있습니다.", "Set your language and recording channels. You can change them later in Settings.", "依次设置语言和录制频道，以后可在设置中修改。", "依序設定語言及錄製頻道，之後可在設定中變更。", "言語と録画するチャンネルを順に設定します。後から設定で変更できます。"),
    "setup_channels": ("녹화할 채널을 추가하세요", "Add recording channels", "添加录制频道", "新增錄製頻道", "録画するチャンネルを追加"),
    "setup_channels_help": ("채널 이름이나 ID로 검색하고 저장 폴더를 확인하세요. 완료 전까지 변경 사항은 저장되지 않습니다.", "Search by name or ID and check the storage folder. Changes are saved only when you finish.", "按名称或 ID 搜索并确认保存文件夹。完成前不会保存更改。", "以名稱或 ID 搜尋並確認儲存資料夾。完成前不會儲存變更。", "名前や ID で検索し、保存先を確認してください。完了するまで変更は保存されません。"),
    "setup_ready": ("설정이 준비되었습니다", "Ready to finish", "设置已就绪", "設定已就緒", "設定の準備ができました"),
    "setup_ready_help": ("완료를 누르면 설정을 저장하고 메인 화면으로 이동합니다.", "Finish to save your settings and open the main window.", "点击完成以保存设置并打开主窗口。", "按下完成以儲存設定並開啟主視窗。", "完了を押すと設定を保存し、メイン画面に移動します。"),
    "setup_folder": ("새 채널의 기본 저장 위치", "Default location for new channels", "新频道的默认保存位置", "新頻道的預設儲存位置", "新規チャンネルの既定の保存先"),
    "setup_folder_help": ("새 채널은 이 위치 아래 채널별 폴더에 저장합니다. 이미 등록한 채널의 폴더는 바뀌지 않습니다.", "New channels use individual folders below this location. Existing channel folders stay unchanged.", "新频道使用此位置下各自的文件夹，已有频道的文件夹不变。", "新頻道使用此位置下各自的資料夾，既有頻道的資料夾不變。", "新しいチャンネルはこの場所の下に個別のフォルダーを作ります。既存の保存先は変更しません。"),
    "setup_skip": ("채널은 나중에 추가할게요", "I'll add channels later", "稍后添加频道", "稍後新增頻道", "チャンネルは後で追加する"),
    "setup_summary": ("언어: {language}\n등록 채널: {count}개\n\n메인 화면에서 ‘자동 녹화 시작’을 누르면 방송을 확인하고 녹화를 시작합니다. 이 마법사는 도움말 → 처음 설정에서 다시 열 수 있습니다.", "Language: {language}\nChannels: {count}\n\nSelect Start recording in the main window to begin watching for broadcasts. Reopen this wizard from Help → Getting started.", "语言：{language}\n频道：{count}\n\n在主窗口点击开始录制以监测直播。可从帮助 → 初始设置重新打开向导。", "語言：{language}\n頻道：{count}\n\n在主視窗按開始錄製以監測直播。可從說明 → 初始設定重新開啟精靈。", "言語: {language}\nチャンネル数: {count}\n\nメイン画面で自動録画を開始すると配信の確認を始めます。ヘルプ → 初期設定から再度開けます。"),
    "login": ("로그인 창 열기", "Open login window", "打开登录窗口", "開啟登入視窗", "ログイン画面を開く"),
    "login_wait": ("열린 CLI 창의 안내에 따라 브라우저에서 로그인한 뒤 Enter를 누르세요. 완료되면 쿠키를 이 화면으로 가져옵니다.", "Follow the separate CLI window: log in using the browser, then press Enter. The cookies will return to this screen.", "按独立 CLI 窗口的提示在浏览器登录，再按 Enter。Cookie 将返回此界面。", "依獨立 CLI 視窗的指示在瀏覽器登入，再按 Enter。Cookie 將返回此畫面。", "別の CLI 画面の案内に従ってブラウザーでログインし、Enter を押してください。Cookie がこの画面に戻ります。"),
    "login_terminal_missing": ("로그인할 터미널을 찾지 못했습니다. 터미널에서 settings.py의 네이버 로그인 메뉴를 사용하세요.", "No terminal is available. Use NAVER login in settings.py from a terminal.", "找不到终端，请在终端中使用 settings.py 的 NAVER 登录菜单。", "找不到終端機，請在終端機中使用 settings.py 的 NAVER 登入選單。", "ターミナルが見つかりません。ターミナルから settings.py の NAVER ログインを使用してください。"),
    "tray_help": ("창을 닫아도 녹화를 계속합니다. 트레이 아이콘에서 창을 다시 열거나 종료할 수 있습니다. 종료할 때는 녹화 파일 정리를 기다립니다.", "Keep recording when the window closes. Reopen or quit from the tray; quitting waits for recording files to finish.", "关闭窗口后继续录制，可从托盘重新打开或退出。退出时会等待录制文件完成。", "關閉視窗後繼續錄製，可從系統匣重新開啟或結束。結束時會等待錄製檔案完成。", "画面を閉じても録画を続けます。トレイから再表示や終了ができます。終了時は録画ファイルの処理を待ちます。"),
    "quick_help": ("처음 설정 → 채널 추가 → 자동 녹화 시작 순서로 사용하세요. 채널 우클릭으로 설정·삭제·폴더·활성화를 조정합니다. 백그라운드에서는 트레이 메뉴의 종료를 사용하세요. 설정에 포인터를 두거나 F1을 누르면 설명을 볼 수 있습니다.", "Use Getting started, add channels, then start recording. Right-click channels for settings, removal, folders and activation. Quit from the tray when in background. Hover or press F1 for help.", "完成初始设置、添加频道后开始录制。右键频道可设置、移除、打开文件夹或启停。后台运行时从托盘退出。悬停或按 F1 查看帮助。", "完成初始設定、新增頻道後開始錄製。右鍵頻道可設定、移除、開啟資料夾或啟停。背景執行時從系統匣結束。停留游標或按 F1 查看說明。", "初期設定、チャンネル追加、自動録画開始の順に使用します。右クリックで設定・削除・フォルダー・有効化を操作できます。バックグラウンドではトレイから終了します。ホバーまたは F1 で説明を表示します。"),
    "install_mode": ("사용할 화면을 선택하세요.\n1. GUI — 창과 버튼으로 사용\n2. CLI — 터미널 메뉴로 사용", "Choose your interface.\n1. GUI — windows and buttons\n2. CLI — terminal menus", "选择操作界面。\n1. GUI — 窗口和按钮\n2. CLI — 终端菜单", "選擇操作介面。\n1. GUI — 視窗和按鈕\n2. CLI — 終端機選單", "使用する画面を選んでください。\n1. GUI — ウィンドウとボタン\n2. CLI — ターミナルのメニュー"),
    "install_mode_prompt": ("번호 [기본값: 1]: ", "Number [default: 1]: ", "编号 [默认：1]：", "編號 [預設：1]：", "番号 [既定: 1]: "),
    "install_gui_ready": ("설치가 완료되었습니다. GUI를 엽니다. 처음 실행하면 설정 마법사가 표시됩니다.", "Installation complete. Opening the GUI; the setup wizard appears on first launch.", "安装完成。正在打开 GUI，首次启动将显示设置向导。", "安裝完成。正在開啟 GUI，首次啟動會顯示設定精靈。", "インストールが完了しました。GUI を開きます。初回は設定ウィザードが表示されます。"),
    "install_failed": ("설치를 완료하지 못했습니다: {error}", "Installation could not finish: {error}", "无法完成安装：{error}", "無法完成安裝：{error}", "インストールを完了できませんでした: {error}"),
    "cli_main_menu": ("1. 채널 관리\n2. 녹화 · 화질\n3. 인코딩\n4. 네이버 로그인\n5. 네트워크\n6. 언어 · 로그\n0. 종료", "1. Channels\n2. Recording and quality\n3. Encoding\n4. NAVER login\n5. Network\n6. Language and logs\n0. Exit", "1. 频道管理\n2. 录制与画质\n3. 编码\n4. NAVER 登录\n5. 网络\n6. 语言与日志\n0. 退出", "1. 頻道管理\n2. 錄製與畫質\n3. 編碼\n4. NAVER 登入\n5. 網路\n6. 語言與記錄\n0. 結束", "1. チャンネル管理\n2. 録画・画質\n3. エンコード\n4. NAVER ログイン\n5. ネットワーク\n6. 言語・ログ\n0. 終了"),
    "cli_channel_menu": ("1. 채널 추가\n2. 채널 삭제\n3. 녹화 사용 여부\n4. 채널별 분할 · 화질\n0. 뒤로", "1. Add channel\n2. Remove channel\n3. Enable recording\n4. Channel split and quality\n0. Back", "1. 添加频道\n2. 删除频道\n3. 启用录制\n4. 频道分割与画质\n0. 返回", "1. 新增頻道\n2. 刪除頻道\n3. 啟用錄製\n4. 頻道分割與畫質\n0. 返回", "1. チャンネル追加\n2. チャンネル削除\n3. 録画の有効化\n4. チャンネル別の分割・画質\n0. 戻る"),
    "cli_recording_menu": ("1. 다운로드 스레드\n2. 방송 확인 간격\n3. 파일 형식\n4. 기본 분할 간격\n5. 기본 화질 · FPS\n0. 뒤로", "1. Download threads\n2. Broadcast check interval\n3. File format\n4. Default split interval\n5. Default quality and FPS\n0. Back", "1. 下载线程\n2. 直播检查间隔\n3. 文件格式\n4. 默认分割间隔\n5. 默认画质与 FPS\n0. 返回", "1. 下載執行緒\n2. 直播檢查間隔\n3. 檔案格式\n4. 預設分割間隔\n5. 預設畫質與 FPS\n0. 返回", "1. ダウンロードスレッド\n2. 配信確認間隔\n3. ファイル形式\n4. 既定の分割間隔\n5. 既定の画質・FPS\n0. 戻る"),
    "cli_encoding_menu": ("1. H.264\n2. HEVC (H.265)\n3. AV1\n0. 뒤로", "1. H.264\n2. HEVC (H.265)\n3. AV1\n0. Back", "1. H.264\n2. HEVC (H.265)\n3. AV1\n0. 返回", "1. H.264\n2. HEVC (H.265)\n3. AV1\n0. 返回", "1. H.264\n2. HEVC (H.265)\n3. AV1\n0. 戻る"),
    "cli_auth_menu": ("1. 브라우저로 로그인\n2. 쿠키 직접 입력\n3. 쿠키 삭제\n0. 뒤로", "1. Browser login\n2. Enter cookies\n3. Delete cookies\n0. Back", "1. 浏览器登录\n2. 输入 Cookie\n3. 删除 Cookie\n0. 返回", "1. 瀏覽器登入\n2. 輸入 Cookie\n3. 刪除 Cookie\n0. 返回", "1. ブラウザーでログイン\n2. Cookie を入力\n3. Cookie を削除\n0. 戻る"),
    "cli_browser_menu": ("1. Chrome\n2. Microsoft Edge\n3. Firefox\n0. 뒤로", "1. Chrome\n2. Microsoft Edge\n3. Firefox\n0. Back", "1. Chrome\n2. Microsoft Edge\n3. Firefox\n0. 返回", "1. Chrome\n2. Microsoft Edge\n3. Firefox\n0. 返回", "1. Chrome\n2. Microsoft Edge\n3. Firefox\n0. 戻る"),
    "cli_network_menu": ("1. DNS-over-HTTPS 사용 여부\n2. DoH 주소 변경\n3. 기본 주소 복원\n0. 뒤로", "1. Toggle DNS-over-HTTPS\n2. Change DoH URL\n3. Restore default URL\n0. Back", "1. 启用 DNS-over-HTTPS\n2. 修改 DoH 地址\n3. 恢复默认地址\n0. 返回", "1. 啟用 DNS-over-HTTPS\n2. 變更 DoH 位址\n3. 還原預設位址\n0. 返回", "1. DNS-over-HTTPS の有効化\n2. DoH URL の変更\n3. 既定の URL に戻す\n0. 戻る"),
    "cli_app_menu": ("1. 언어 변경\n2. 파일 로그 사용 여부\n0. 뒤로", "1. Change language\n2. Toggle file logging\n0. Back", "1. 修改语言\n2. 文件日志开关\n0. 返回", "1. 變更語言\n2. 檔案記錄開關\n0. 返回", "1. 言語変更\n2. ファイルログの有効化\n0. 戻る"),
    "cli_add_menu": ("1. 이름으로 검색\n2. 채널 ID 입력\n0. 뒤로", "1. Search by name\n2. Enter channel ID\n0. Back", "1. 按名称搜索\n2. 输入频道 ID\n0. 返回", "1. 以名稱搜尋\n2. 輸入頻道 ID\n0. 返回", "1. 名前で検索\n2. チャンネル ID を入力\n0. 戻る"),
    "login_timeout": ("로그인 대기 시간이 지났습니다. 로그인 창을 다시 열어 진행하세요.", "The login wait timed out. Open the login window again to continue.", "登录等待已超时，请重新打开登录窗口。", "登入等待已逾時，請重新開啟登入視窗。", "ログインの待機時間を超えました。ログイン画面を開き直してください。"),
})

_GUI_TEXT.update({
    "quit_app": ("프로그램 완전 종료", "Quit application", "完全退出程序", "完全結束程式", "アプリを完全に終了"),
    "quit_app_help": ("진행 중인 녹화를 마무리한 뒤 프로그램과 트레이 아이콘을 모두 종료합니다.", "Finish active recordings, then close the application and its tray icon.", "完成当前录制后关闭程序和托盘图标。", "完成目前錄製後關閉程式及系統匣圖示。", "録画ファイルの処理を終えてから、アプリとトレイアイコンを終了します。"),
})

_GUI_TEXT.update({
    "recorder_stop_reason": ("녹화기 종료 원인: {reason} [{code}]{detail}", "Recorder shutdown reason: {reason} [{code}]{detail}", "录制器停止原因：{reason} [{code}]{detail}", "錄製器停止原因：{reason} [{code}]{detail}", "録画プロセスの終了理由: {reason} [{code}]{detail}"),
    "control_user_stop": ("GUI에서 녹화 중지를 요청했습니다.", "The GUI requested recording to stop.", "GUI 请求停止录制。", "GUI 要求停止錄製。", "GUI から録画停止が要求されました。"),
    "control_app_exit": ("GUI에서 프로그램 종료를 요청했습니다.", "The GUI requested application exit.", "GUI 请求退出程序。", "GUI 要求結束程式。", "GUI からアプリの終了が要求されました。"),
    "control_protocol_error": ("GUI가 잘못된 상태 응답을 감지해 중지를 요청했습니다.", "The GUI requested a stop after receiving an invalid status response.", "GUI 检测到无效状态响应并请求停止。", "GUI 偵測到無效狀態回應並要求停止。", "GUI が不正な状態応答を検出し、停止を要求しました。"),
    "control_closed": ("GUI 제어 연결이 닫혔습니다.", "The GUI control connection closed.", "GUI 控制连接已关闭。", "GUI 控制連線已關閉。", "GUI の制御接続が閉じられました。"),
    "control_invalid": ("GUI 제어 명령의 길이가 허용 범위를 초과했습니다.", "A GUI control command exceeded the size limit.", "GUI 控制命令超出长度限制。", "GUI 控制命令超出長度限制。", "GUI の制御コマンドが長さの上限を超えました。"),
    "control_read_failed": ("GUI 제어 연결을 읽는 중 오류가 발생했습니다.", "Reading the GUI control connection failed.", "读取 GUI 控制连接时发生错误。", "讀取 GUI 控制連線時發生錯誤。", "GUI の制御接続の読み取りに失敗しました。"),
    "events_write_failed": ("GUI에 녹화 상태를 보내는 중 오류가 발생했습니다.", "Sending recording status to the GUI failed.", "向 GUI 发送录制状态时发生错误。", "向 GUI 傳送錄製狀態時發生錯誤。", "GUI への録画状態の送信に失敗しました。"),
    "stopped_before_input": ("{channel_name}: 영상 데이터 수신 전에 녹화가 중지되어 FFmpeg 입력이 비어 있습니다.", "{channel_name}: recording stopped before video data arrived, leaving FFmpeg input empty.", "{channel_name}：收到视频数据前录制已停止，FFmpeg 输入为空。", "{channel_name}：收到影片資料前錄製已停止，FFmpeg 輸入為空。", "{channel_name}: 映像データを受信する前に録画が停止したため、FFmpeg の入力は空です。"),
})

_GUI_TEXT.update({
    "more_actions": ("명령 더보기", "More actions", "更多操作", "更多操作", "その他の操作"),
})

for _key, _texts in _GUI_TEXT.items():
    for _language, _text in zip(SUPPORTED_LANGUAGES, _texts, strict=True):
        TRANSLATIONS[_language]["gui." + _key] = _text
