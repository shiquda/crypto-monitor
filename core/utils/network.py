from config.settings import get_settings_manager


def get_proxy_config() -> dict[str, str]:
    settings = get_settings_manager().settings
    proxies = {}

    if settings.proxy.enabled:
        scheme = settings.proxy.type.lower()
        host = settings.proxy.host
        port = settings.proxy.port
        username = settings.proxy.username
        password = settings.proxy.password

        if username and password:
            auth = f"{username}:{password}@"
        else:
            auth = ""

        if scheme == "http":
            url = f"http://{auth}{host}:{port}"
            proxies = {"http": url, "https": url}
        elif scheme == "socks5":
            url = f"socks5://{auth}{host}:{port}"
            proxies = {"http": url, "https": url}

    return proxies


def get_aiohttp_proxy_url() -> str | None:
    proxies = get_proxy_config()
    return proxies.get("http") or proxies.get("https")
