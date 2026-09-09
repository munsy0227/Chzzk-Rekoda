import os
from copy import deepcopy

from channel_service import (
    channels_with_name,
    fetch_chzzk_channel,
    find_channel_by_id,
    safe_channel_folder_name,
    search_chzzk_channels,
)
from config_store import (
    ALLOWED_AV1_ENCODERS,
    ALLOWED_ENCODERS,
    AUTH_COOKIE_NAMES,
    BROWSER_LOGIN_OPTIONS,
    DEFAULT_DOH_URL,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_RECORDING_SPLIT_MINUTES,
    DEFAULT_RESCAN_INTERVAL_SECONDS,
    ENCODER_PRESETS,
    MAX_RECORDING_SPLIT_MINUTES,
    MAX_RESCAN_INTERVAL_SECONDS,
    MIN_RESCAN_INTERVAL_SECONDS,
    SAFE_CHANNEL_ID,
    ConfigError,
    ConfigStore,
    clamp_int,
    default_config,
    format_split_interval,
    normalize_bitrate,
    normalize_channel_identifier,
    normalize_doh_url,
    normalize_encoder_preset,
    normalize_output_format,
    sanitize_cookie,
    script_directory,
)
from i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    enabled_word,
    language_display_name,
    language_options,
    normalize_language,
    on_off_label,
    state_label,
    translate,
)
from recording_options import DIRECT_QUALITIES, H264_ENCODERS, normalize_quality


def print_preset_help(encoder, t):
    help_keys = {
        "libx265": "settings.preset_help_x265",
        "hevc_nvenc": "settings.preset_help_hevc_nvenc",
        "hevc_qsv": "settings.preset_help_qsv",
        "hevc_amf": "settings.preset_help_hevc_amf",
        "libsvtav1": "settings.preset_help_svtav1",
        "libaom-av1": "settings.preset_help_libaom",
        "av1_nvenc": "settings.preset_help_av1_nvenc",
        "av1_qsv": "settings.preset_help_qsv",
        "av1_amf": "settings.preset_help_av1_amf",
    }
    key = help_keys.get(encoder)
    if key is None:
        print(t("settings.preset_unsupported", encoder=encoder))
        return False
    print(t(key))
    return True


def create_output_directory(output_dir):
    expanded_path = os.path.expanduser(output_dir)
    if not os.path.isabs(expanded_path):
        expanded_path = os.path.join(script_directory, expanded_path)
    try:
        os.makedirs(expanded_path, exist_ok=True)
    except OSError as error:
        print(t("settings.output_dir_create_error", error=error))
        return False
    return True


# Initialized by main() only.
config = deepcopy(default_config)
_store = None


def save_config(value):
    try:
        _store.save(value)
    except (ConfigError, OSError) as error:
        print(t("settings.config_save_error", error=error))
        raise SystemExit(1) from error


def current_language():
    return normalize_language(config.get("language"))


def t(key, **kwargs):
    return translate(current_language(), key, **kwargs)


def try_again():
    print(t("settings.try_again"))


def print_codec_settings(codec, settings):
    print("\n" + t("settings.codec_title", codec=codec))
    print(
        t("settings.status", status=state_label(current_language(), settings["enable"]))
    )
    print(t("settings.encoder", encoder=settings.get("encoder", "libx265")))
    print(t("settings.target_bitrate", bitrate=settings["bitrate"]))
    print(t("settings.max_bitrate", bitrate=settings["max_bitrate"]))
    print(t("settings.preset", preset=settings["preset"]))
    print("-" * 30)


def print_language_menu():
    print("\n" + t("settings.language_title"))
    print(
        t(
            "settings.current_language",
            language=language_display_name(current_language()),
        )
    )
    for idx, (code, name) in enumerate(language_options(), start=1):
        print(f"{idx}. {name} ({code})")


def import_cookies_from_browser(browser):
    from browser_login import collect_browser_cookies

    try:
        browser_cookies = collect_browser_cookies(
            browser, lambda driver: input(t("settings.browser_login_wait"))
        )
        missing = [name for name in AUTH_COOKIE_NAMES if not browser_cookies.get(name)]
        if missing:
            print(t("settings.browser_cookies_missing", cookies=", ".join(missing)))
            return False
        config["cookies"] = {name: browser_cookies[name] for name in AUTH_COOKIE_NAMES}
        save_config(config)
        print(t("settings.browser_cookies_saved"))
        return True
    except Exception as error:
        # Selenium exceptions may contain authenticated URLs; expose no values.
        print(t("settings.browser_login_error", error=type(error).__name__))
        return False


def select_language(value):
    text = value.strip()
    options = language_options()
    if text.isdigit():
        index = int(text) - 1
        if 0 <= index < len(options):
            return options[index][0]
        return None
    if text in SUPPORTED_LANGUAGES:
        return text
    normalized = normalize_language(text)
    if normalized != DEFAULT_LANGUAGE or text.lower() in {
        "ko",
        "kr",
        "kor",
        "korean",
        "한국어",
    }:
        return normalized
    return None


def print_duplicate_channel(channel):
    print(
        t(
            "settings.channel_already_registered",
            channel_id=channel["id"],
            name=channel["name"],
            output_dir=channel["output_dir"],
        )
    )


def choose_channel_by_search():
    keyword = str(input(t("settings.prompt_search_keyword"))).strip()
    if not keyword:
        print(t("settings.empty_search_keyword"))
        return None

    results, error = search_chzzk_channels(keyword, current_language())
    if error:
        print(t("settings.channel_search_failed", error=error))
        return None
    if not results:
        print(t("settings.no_search_results"))
        return None

    print(t("settings.channel_search_results"))
    for index, channel in enumerate(results, start=1):
        registered = find_channel_by_id(config["channels"], channel["id"])
        status = t("settings.already_registered_marker") if registered else ""
        print(
            t(
                "settings.channel_search_result",
                index=index,
                name=channel["name"],
                channel_id=channel["id"],
                status=status,
            )
        )

    selection = str(input(t("settings.prompt_search_result"))).strip()
    if selection == "0":
        return None
    try:
        selected_index = int(selection)
    except ValueError:
        print(t("settings.invalid_channel_number"))
        return None
    if not 1 <= selected_index <= len(results):
        print(t("settings.invalid_channel_number"))
        return None
    selected = results[selected_index - 1]

    duplicate = find_channel_by_id(config["channels"], selected["id"])
    if duplicate:
        print_duplicate_channel(duplicate)
        return None
    return selected


def choose_channel_by_id():
    channel_id = str(input(t("settings.prompt_channel_id"))).strip()
    if not SAFE_CHANNEL_ID.fullmatch(channel_id):
        print(t("settings.invalid_channel_id"))
        return None

    duplicate = find_channel_by_id(config["channels"], channel_id)
    if duplicate:
        print_duplicate_channel(duplicate)
        return None

    print(t("settings.channel_lookup_in_progress"))
    channel, error = fetch_chzzk_channel(channel_id, current_language())
    if error:
        print(t("settings.channel_lookup_failed", error=error))
        return None
    print(
        t(
            "settings.channel_lookup_result",
            channel_id=channel["id"],
            name=channel["name"],
        )
    )
    return channel


def add_selected_channel(channel):
    channel_id = channel["id"]
    name = channel["name"]
    duplicate_names = channels_with_name(
        config["channels"], name, exclude_id=channel_id
    )
    if duplicate_names:
        duplicate_ids = ", ".join(item["id"] for item in duplicate_names)
        print(
            t(
                "settings.duplicate_channel_name_warning",
                name=name,
                channel_ids=duplicate_ids,
            )
        )

    default_output_dir = safe_channel_folder_name(name, channel_id)
    output_dir = (
        str(
            input(
                t(
                    "settings.prompt_output_dir",
                    default_output_dir=default_output_dir,
                )
            )
        ).strip()
        or default_output_dir
    )

    while True:
        answer = str(
            input(
                t(
                    "settings.confirm_channel",
                    channel_id=channel_id,
                    name=name,
                    output_dir=output_dir,
                )
            )
        ).strip()
        if answer.lower() == "y":
            duplicate = find_channel_by_id(config["channels"], channel_id)
            if duplicate:
                print_duplicate_channel(duplicate)
                return
            if not create_output_directory(output_dir):
                return

            current_count = len(config["channels"])
            used_identifiers = {item.get("identifier") for item in config["channels"]}
            identifier = normalize_channel_identifier(
                f"ch{current_count + 1}",
                current_count + 1,
                used_identifiers,
            )
            config["channels"].append(
                {
                    "id": channel_id,
                    "name": name,
                    "output_dir": output_dir,
                    "identifier": identifier,
                    "active": "on",
                }
            )
            config["delays"][identifier] = current_count
            save_config(config)
            print(t("settings.channel_added"))
            return
        if answer.lower() == "n":
            print(t("settings.reenter"))
            return
        try_again()


def edit_quality(value):
    result = normalize_quality(value)
    mode = input(t("gui.cli_quality_prompt")).strip()
    if not mode:
        return result
    if mode not in ("best", "custom", *DIRECT_QUALITIES):
        raise ValueError(t("gui.invalid_quality"))
    result["mode"] = mode
    if mode == "custom":
        for key in ("width", "height"):
            text = input(t("gui." + key) + f" [{result[key]}]: ").strip()
            if text:
                result[key] = int(text)
    text = input(t("gui.fps") + f" [{result['fps']}], 0: ").strip()
    if text:
        result["fps"] = float(text)
    if normalize_quality(result) != result:
        raise ValueError(t("gui.invalid_quality"))
    return result


def edit_h264():
    while True:
        codec = config["h264_settings"]
        print_codec_settings("H.264", codec)
        keys = ("enabled", "encoder", "bitrate", "max_bitrate", "preset", "close")
        print("\n".join(f"{i}. {t('gui.' + key)}" for i, key in enumerate(keys, 1)))
        choice = input(t("settings.prompt_choice")).strip()
        if choice == "1":
            codec["enable"] = not codec["enable"]
            if codec["enable"]:
                config["hevc_settings"]["enable"] = config["av1_settings"]["enable"] = (
                    False
                )
        elif choice == "2":
            print(", ".join(sorted(H264_ENCODERS)))
            encoder = input(t("settings.prompt_encoder")).strip()
            if encoder not in H264_ENCODERS:
                print(t("settings.invalid_encoder"))
                continue
            codec["encoder"] = encoder
            codec["preset"] = normalize_encoder_preset(encoder, None)
        elif choice in ("3", "4"):
            key = "bitrate" if choice == "3" else "max_bitrate"
            codec[key] = normalize_bitrate(input(t("gui." + key) + ": "), codec[key])
        elif choice == "5":
            presets = ENCODER_PRESETS.get(codec["encoder"])
            if not presets:
                print(t("settings.preset_unsupported", encoder=codec["encoder"]))
                continue
            print(", ".join(sorted(presets)))
            preset = input(t("settings.prompt_preset")).strip()
            if preset not in presets:
                print(t("settings.invalid_preset"))
                continue
            codec["preset"] = preset
        elif choice == "6":
            return
        else:
            try_again()
            continue
        save_config(config)


def edit_channel_recording():
    for index, channel in enumerate(config["channels"], 1):
        print(f"{index}. {channel['name']}")
    try:
        index = int(input(t("gui.select_channel") + ": ")) - 1
        if not 0 <= index < len(config["channels"]):
            raise ValueError(t("settings.invalid_channel_number"))
        channel = deepcopy(config["channels"][index])
        interval = int(input(t("gui.cli_split_prompt")))
        if not -1 <= interval <= MAX_RECORDING_SPLIT_MINUTES:
            raise ValueError(t("settings.invalid_number"))
        channel["recording_split_minutes"] = None if interval == -1 else interval
        inherit = input(t("gui.cli_quality_inherit")).strip()
        if inherit == "1":
            channel["quality_settings"] = None
        elif inherit == "2":
            channel["quality_settings"] = edit_quality(
                channel.get("quality_settings") or config["quality_settings"]
            )
        else:
            raise ValueError(t("settings.invalid_number"))
        config["channels"][index] = channel
        save_config(config)
    except ValueError:
        print(t("gui.invalid_quality"))


def main():
    global config, _store
    _store = ConfigStore(notify=print)
    try:
        config = _store.load()
    except (ConfigError, OSError) as error:
        print(translate(DEFAULT_LANGUAGE, "settings.config_read_error", error=error))
        return 1
    while True:
        print(t("settings.main_title"))
        print(t("settings.main_menu"))
        print(t("gui.cli_extra_menu"))
        choice = str(input(t("settings.prompt_choice"))).strip()

        if choice == "1":
            while True:
                print(t("settings.channel_menu"))
                print(t("gui.cli_channel_options"))
                choice1 = str(input(t("settings.prompt_choice"))).strip()
                if choice1 == "1":
                    print(t("settings.add_channel_menu"))
                    add_choice = str(input(t("settings.prompt_choice"))).strip()
                    if add_choice == "1":
                        selected_channel = choose_channel_by_search()
                    elif add_choice == "2":
                        selected_channel = choose_channel_by_id()
                    elif add_choice == "3":
                        continue
                    else:
                        try_again()
                        continue

                    if selected_channel is not None:
                        add_selected_channel(selected_channel)

                elif choice1 == "2":
                    if not config["channels"]:
                        print(t("settings.no_channels_delete"))
                        continue

                    print(t("settings.current_channel_list"))
                    for idx, channel in enumerate(config["channels"], start=1):
                        print(
                            t(
                                "settings.channel_list_item",
                                idx=idx,
                                channel_id=channel["id"],
                                name=channel["name"],
                            )
                        )

                    try:
                        idx_to_del = int(input(t("settings.prompt_delete_channel"))) - 1
                        if 0 <= idx_to_del < len(config["channels"]):
                            deleted_channel = config["channels"].pop(idx_to_del)
                            print(
                                t(
                                    "settings.deleted_channel",
                                    channel_id=deleted_channel["id"],
                                    name=deleted_channel["name"],
                                )
                            )

                            new_delays = {}
                            for i, channel in enumerate(config["channels"]):
                                new_identifier = f"ch{i + 1}"
                                channel["identifier"] = new_identifier
                                new_delays[new_identifier] = i

                            config["delays"] = new_delays
                            save_config(config)
                            print(t("settings.channel_deleted"))
                        else:
                            print(t("settings.invalid_channel_number"))
                    except ValueError:
                        print(t("settings.invalid_number"))

                elif choice1 == "3":
                    if not config["channels"]:
                        print(t("settings.no_channels_toggle"))
                        continue

                    print(t("settings.current_channel_list"))
                    for idx, channel in enumerate(config["channels"], start=1):
                        status = on_off_label(
                            current_language(), channel.get("active", "on") == "on"
                        )
                        print(
                            t(
                                "settings.channel_list_item_status",
                                idx=idx,
                                channel_id=channel["id"],
                                name=channel["name"],
                                status=status,
                            )
                        )

                    try:
                        idx_to_toggle = (
                            int(input(t("settings.prompt_toggle_channel"))) - 1
                        )
                        if 0 <= idx_to_toggle < len(config["channels"]):
                            channel = config["channels"][idx_to_toggle]
                            current_state = channel.get("active", "on")
                            channel["active"] = "off" if current_state == "on" else "on"
                            status = on_off_label(
                                current_language(), current_state != "on"
                            )
                            print(
                                t(
                                    "settings.channel_status_changed",
                                    name=channel["name"],
                                    status=status,
                                )
                            )
                            save_config(config)
                        else:
                            print(t("settings.invalid_channel_number"))
                    except ValueError:
                        print(t("settings.invalid_number"))

                elif choice1 == "4":
                    break
                elif choice1 == "5":
                    edit_channel_recording()
                else:
                    try_again()

        elif choice == "2":
            while True:
                print(t("settings.recording_menu"))
                choice2 = str(input(t("settings.prompt_choice"))).strip()

                if choice2 == "1":
                    print(
                        t(
                            "settings.current_threads",
                            count=config.get("stream_segment_threads", 2),
                        )
                    )
                    print(t("settings.thread_recommendation"))
                    new_threads = clamp_int(
                        input(t("settings.prompt_threads")), 2, 1, 16
                    )
                    config["stream_segment_threads"] = new_threads
                    save_config(config)
                    print(t("settings.threads_changed"))

                elif choice2 == "2":
                    print(
                        t(
                            "settings.current_timeout",
                            seconds=config.get(
                                "timeout", DEFAULT_RESCAN_INTERVAL_SECONDS
                            ),
                        )
                    )
                    new_timeout = clamp_int(
                        input(t("settings.prompt_timeout")),
                        DEFAULT_RESCAN_INTERVAL_SECONDS,
                        MIN_RESCAN_INTERVAL_SECONDS,
                        MAX_RESCAN_INTERVAL_SECONDS,
                    )
                    config["timeout"] = new_timeout
                    save_config(config)
                    print(t("settings.timeout_changed"))

                elif choice2 == "3":
                    current_format = config.get("output_format", DEFAULT_OUTPUT_FORMAT)
                    print(t("settings.current_output_format", format=current_format))
                    print(t("settings.available_formats"))
                    new_format = normalize_output_format(
                        input(t("settings.prompt_output_format"))
                    )
                    config["output_format"] = new_format
                    save_config(config)
                    print(t("settings.output_format_changed", format=new_format))

                elif choice2 == "4":
                    current_split = clamp_int(
                        config.get("recording_split_minutes"),
                        DEFAULT_RECORDING_SPLIT_MINUTES,
                        0,
                        MAX_RECORDING_SPLIT_MINUTES,
                    )
                    print(
                        t(
                            "settings.current_split",
                            interval=format_split_interval(
                                current_split, current_language()
                            ),
                        )
                    )
                    print(t("settings.choose_split_unit"))
                    print(t("settings.unit_hours"))
                    print(t("settings.unit_minutes"))
                    print(t("settings.unit_disable"))
                    unit_choice = input(t("settings.prompt_choice")).strip()

                    if unit_choice == "1":
                        split_hours = clamp_int(
                            input(t("settings.prompt_split_hours")),
                            DEFAULT_RECORDING_SPLIT_MINUTES,
                            0,
                            MAX_RECORDING_SPLIT_MINUTES // 60,
                        )
                        new_split = split_hours * 60
                    elif unit_choice == "2":
                        new_split = clamp_int(
                            input(t("settings.prompt_split_minutes")),
                            DEFAULT_RECORDING_SPLIT_MINUTES,
                            0,
                            MAX_RECORDING_SPLIT_MINUTES,
                        )
                    elif unit_choice == "3":
                        new_split = 0
                    else:
                        try_again()
                        continue

                    config["recording_split_minutes"] = new_split
                    save_config(config)
                    if new_split == 0:
                        print(t("settings.split_disabled"))
                    else:
                        print(
                            t(
                                "settings.split_changed",
                                interval=format_split_interval(
                                    new_split, current_language()
                                ),
                            )
                        )

                elif choice2 == "5":
                    break
                else:
                    try_again()

        elif choice == "3":
            while True:
                hevc = config["hevc_settings"]
                print_codec_settings("HEVC (H.265)", hevc)
                print(t("settings.hevc_menu"))
                choice3 = str(input(t("settings.prompt_choice"))).strip()

                if choice3 == "1":
                    hevc["enable"] = not hevc["enable"]
                    if hevc["enable"]:
                        config["av1_settings"]["enable"] = False
                        config["h264_settings"]["enable"] = False
                    save_config(config)
                    print(
                        t(
                            "settings.encoding_toggled",
                            codec="HEVC",
                            state=enabled_word(current_language(), hevc["enable"]),
                        )
                    )

                elif choice3 == "2":
                    print(t("settings.available_encoders"))
                    print(" - libx265 (CPU, Default)")
                    print(" - hevc_nvenc (NVIDIA GPU)")
                    print(" - hevc_qsv (Intel GPU)")
                    print(" - hevc_amf (AMD GPU)")
                    print(" - hevc_vaapi (Linux VAAPI)")
                    print(" - hevc_videotoolbox (macOS)")
                    new_encoder = input(t("settings.prompt_encoder")).strip()
                    if new_encoder in ALLOWED_ENCODERS:
                        hevc["encoder"] = new_encoder
                        hevc["preset"] = normalize_encoder_preset(
                            new_encoder, hevc.get("preset")
                        )
                        save_config(config)
                    else:
                        print(t("settings.invalid_encoder"))

                elif choice3 == "3":
                    hevc["bitrate"] = normalize_bitrate(
                        input(t("settings.prompt_target_bitrate")), hevc["bitrate"]
                    )
                    save_config(config)

                elif choice3 == "4":
                    hevc["max_bitrate"] = normalize_bitrate(
                        input(t("settings.prompt_max_bitrate")), hevc["max_bitrate"]
                    )
                    save_config(config)

                elif choice3 == "5":
                    if not print_preset_help(hevc["encoder"], t):
                        continue
                    new_preset = input(t("settings.prompt_preset")).strip()
                    if new_preset.lower() in ENCODER_PRESETS[hevc["encoder"]]:
                        hevc["preset"] = new_preset.lower()
                        save_config(config)
                    else:
                        print(t("settings.invalid_preset"))

                elif choice3 == "6":
                    break
                else:
                    try_again()

        elif choice == "4":
            while True:
                av1 = config["av1_settings"]
                print_codec_settings("AV1", av1)
                print(t("settings.av1_menu"))
                choice4 = str(input(t("settings.prompt_choice"))).strip()

                if choice4 == "1":
                    av1["enable"] = not av1["enable"]
                    if av1["enable"]:
                        config["hevc_settings"]["enable"] = False
                        config["h264_settings"]["enable"] = False
                    save_config(config)
                    print(
                        t(
                            "settings.encoding_toggled",
                            codec="AV1",
                            state=enabled_word(current_language(), av1["enable"]),
                        )
                    )

                elif choice4 == "2":
                    print(t("settings.available_encoders"))
                    print(" - libsvtav1 (CPU, Default)")
                    print(" - libaom-av1 (CPU)")
                    print(" - av1_nvenc (NVIDIA GPU)")
                    print(" - av1_qsv (Intel GPU)")
                    print(" - av1_amf (AMD GPU)")
                    print(" - av1_vaapi (Linux VAAPI)")
                    new_encoder = input(t("settings.prompt_encoder")).strip()
                    if new_encoder in ALLOWED_AV1_ENCODERS:
                        av1["encoder"] = new_encoder
                        av1["preset"] = normalize_encoder_preset(
                            new_encoder, av1.get("preset")
                        )
                        save_config(config)
                    else:
                        print(t("settings.invalid_encoder"))

                elif choice4 == "3":
                    av1["bitrate"] = normalize_bitrate(
                        input(t("settings.prompt_target_bitrate")), av1["bitrate"]
                    )
                    save_config(config)

                elif choice4 == "4":
                    av1["max_bitrate"] = normalize_bitrate(
                        input(t("settings.prompt_max_bitrate")), av1["max_bitrate"]
                    )
                    save_config(config)

                elif choice4 == "5":
                    if not print_preset_help(av1["encoder"], t):
                        continue
                    new_preset = input(t("settings.prompt_preset")).strip()
                    if new_preset.lower() in ENCODER_PRESETS[av1["encoder"]]:
                        av1["preset"] = new_preset.lower()
                        save_config(config)
                    else:
                        print(t("settings.invalid_preset"))

                elif choice4 == "6":
                    break
                else:
                    try_again()

        elif choice == "5":
            while True:
                has_cookies = all(
                    config["cookies"].get(name) for name in AUTH_COOKIE_NAMES
                )
                print("\n" + t("settings.cookie_title"))
                print(
                    t(
                        "settings.cookie_status",
                        status=state_label(current_language(), has_cookies),
                    )
                )
                print(t("settings.cookie_menu"))
                cookie_choice = str(input(t("settings.prompt_choice"))).strip()

                if cookie_choice == "1":
                    print(t("settings.browser_menu"))
                    browser_choice = str(input(t("settings.prompt_choice"))).strip()
                    browser_option = BROWSER_LOGIN_OPTIONS.get(browser_choice)
                    if browser_option is None:
                        if browser_choice != "4":
                            try_again()
                        continue

                    browser, browser_name = browser_option
                    print(
                        t(
                            "settings.browser_login_notice",
                            browser=browser_name,
                        )
                    )
                    import_cookies_from_browser(browser)

                elif cookie_choice == "2":
                    ses = sanitize_cookie(input(t("settings.prompt_ses")))
                    aut = sanitize_cookie(input(t("settings.prompt_aut")))
                    config["cookies"]["NID_SES"] = ses
                    config["cookies"]["NID_AUT"] = aut
                    save_config(config)
                    print(t("settings.cookies_saved"))

                elif cookie_choice == "3":
                    config["cookies"] = {"NID_SES": "", "NID_AUT": ""}
                    save_config(config)
                    print(t("settings.cookies_deleted"))

                elif cookie_choice == "4":
                    break
                else:
                    try_again()

        elif choice == "6":
            while True:
                dns_settings = config["dns_settings"]
                print("\n" + t("settings.dns_title"))
                print(
                    t(
                        "settings.status",
                        status=state_label(current_language(), dns_settings["enable"]),
                    )
                )
                print(t("settings.doh_url", url=dns_settings["doh_url"]))
                print("-" * 30)
                print(t("settings.dns_menu"))

                choice6 = str(input(t("settings.prompt_choice"))).strip()

                if choice6 == "1":
                    dns_settings["enable"] = not dns_settings["enable"]
                    save_config(config)
                    print(
                        t(
                            "settings.dns_toggled",
                            state=enabled_word(
                                current_language(), dns_settings["enable"]
                            ),
                        )
                    )

                elif choice6 == "2":
                    new_url = normalize_doh_url(input(t("settings.prompt_doh_url")))
                    dns_settings["doh_url"] = new_url
                    save_config(config)
                    print(t("settings.doh_url_changed", url=new_url))

                elif choice6 == "3":
                    dns_settings["doh_url"] = DEFAULT_DOH_URL
                    save_config(config)
                    print(t("settings.doh_url_reset", url=DEFAULT_DOH_URL))

                elif choice6 == "4":
                    break
                else:
                    try_again()

        elif choice == "7":
            config["log_enabled"] = not config["log_enabled"]
            save_config(config)
            print(
                t(
                    "settings.logging_toggled",
                    state=enabled_word(current_language(), config["log_enabled"]),
                )
            )

        elif choice == "8":
            print_language_menu()
            selected_language = select_language(input(t("settings.prompt_language")))
            if selected_language is None:
                print(t("settings.invalid_language"))
                continue
            config["language"] = selected_language
            save_config(config)
            print(
                t(
                    "settings.language_changed",
                    language=language_display_name(selected_language),
                )
            )

        elif choice == "10":
            edit_h264()
        elif choice == "11":
            try:
                config["quality_settings"] = edit_quality(config["quality_settings"])
                save_config(config)
            except ValueError:
                print(t("gui.invalid_quality"))
        elif choice == "9":
            print(t("settings.exiting"))
            break
        else:
            try_again()


if __name__ == "__main__":
    raise SystemExit(main())
