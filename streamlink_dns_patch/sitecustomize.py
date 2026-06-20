import os

if os.environ.get("CHZZK_REKODA_ENABLE_DOH_DNS") == "1":
    try:
        from dns_over_https import install_doh_dns

        install_doh_dns()
    except Exception:
        pass
