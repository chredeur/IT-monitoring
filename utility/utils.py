from __future__ import annotations


from ipaddress import ip_address, AddressValueError

from typing import Optional
from urllib.parse import parse_qsl

from quart import request, websocket
from starlette.datastructures import Headers

class ProxyHeadersMiddleware:
    def __init__(self, app, trusted_hosts=None):
        self.app = app
        self.trusted_hosts = trusted_hosts or ["127.0.0.1"]

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            # Utilisation de la classe Headers
            headers = Headers(scope=scope)

            # Vérifie si l'IP source est dans la liste des hosts de confiance
            client_ip, _ = scope.get("client", ("", 0))
            if client_ip in self.trusted_hosts:
                # Gérer le header `X-Forwarded-For`
                x_forwarded_for = headers.get("x-forwarded-for")
                if x_forwarded_for:
                    ip_addresses = x_forwarded_for.split(",")
                    scope["client"] = (ip_addresses[0].strip(), scope["client"][1])

                # Gérer le header `X-Forwarded-Proto`
                x_forwarded_proto = headers.get("x-forwarded-proto")
                if x_forwarded_proto:
                    scope["scheme"] = x_forwarded_proto

        await self.app(scope, receive, send)

def get_client_ip() -> Optional[str]:
    ip = request.headers.get('CF-Connecting-IP', None)
    if not ip:
        x_forwarded_for = request.headers.get('X-Forwarded-For', None)
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.remote_addr
    try:
        ip = str(ip_address(ip))
    except AddressValueError:
        ip = None
    return ip

def get_client_ip_ws():
    return websocket.remote_addr[0] if websocket.remote_addr else "unknown"

def mask_query(query_string: str):
    params = parse_qsl(query_string, keep_blank_values=True)
    if params:
        return "&".join(f"{key}=***" for key, _ in params)
    return ""
