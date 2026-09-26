#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
网络工具模块

提供 IP/MAC 校验、主机名与 IP 解析、网络段解析、连通性检测、ARP 获取 MAC、以及可选的 SSL 忽略等网络相关工具方法。
"""

import os
import time
import datetime
import re
import socket
import subprocess
import warnings
import netaddr
import struct
from typing import Optional, Any, Tuple

# scapy is optional for network scanning features
# Use type hints to help static analyzers
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scapy.layers.l2 import Ether, ARP
    from scapy.sendrecv import srp
else:
    # Runtime imports with fallbacks
    try:
        from scapy.layers.l2 import Ether, ARP
        from scapy.sendrecv import srp
    except ImportError:
        # Define dummy classes when scapy is not available
        class _DummyEther:
            def __init__(self, dst: str = "") -> None:
                self.dst = dst

            def __truediv__(self, other: Any) -> Any:
                return other

        class _DummyARP:
            def __init__(self, pdst: str = "") -> None:
                self.pdst = pdst

        def _dummy_srp(*args: Any, **kwargs: Any) -> tuple[list, list]:
            return ([], [])

        Ether = _DummyEther  # type: ignore
        ARP = _DummyARP  # type: ignore
        srp = _dummy_srp  # type: ignore


def is_valid_ip(ip_addr: str) -> bool:
    """检查 IP 地址是否合法。"""
    try:
        netaddr.IPAddress(ip_addr, flags=1)
    except Exception:
        return False
    return True


def is_valid_mac(mac_addr: str) -> bool:
    """检查 MAC 地址是否合法。"""
    try:
        if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", mac_addr.lower()):
            return True
    except Exception:
        return False
    return False


def is_ip_reachable(ip: str, retries: int = 5) -> bool:
    """检查 IP 地址是否通达。"""
    while retries > 0:
        ret = normal_exec("ping -c 1 -w 1 %s" % ip)
        if ret is not None and ret[0] == 0:
            return True
        retries -= 1
    return False


def is_ip_port_reachable(ip: str, port: int) -> bool:
    """检查 IP 地址和端口号是否通达。"""
    if not os.path.exists("/bin/nc"):
        return False
    ret = normal_exec("/bin/nc -z -w 1 %s %s" % (ip, port))
    if ret is not None and ret[0] == 0:
        return True
    return False


def is_ip_network(network: Any) -> bool:
    """判断是否为 IPv4 网络。"""
    n = network
    if not isinstance(n, (netaddr.IPNetwork, netaddr.IPAddress)):
        n = get_ip_network(network)
    return getattr(n, "version", None) == 4


def is_ipv6_network(network: Any) -> bool:
    """判断是否为 IPv6 网络。"""
    n = network
    if not isinstance(n, (netaddr.IPNetwork, netaddr.IPAddress)):
        n = get_ip_network(network)
    return getattr(n, "version", None) == 6


def get_hostname() -> str:
    """获取主机名称。"""
    return socket.gethostname()


def get_ip_address() -> str:
    """获取本机 IP 地址。"""
    host_name = get_hostname()
    return socket.gethostbyname(host_name)


def get_hostname_by_ip(ip: str) -> Optional[str]:
    """根据 IP 地址获取主机名称。"""
    try:
        socket.setdefaulttimeout(3)
        names = socket.gethostbyaddr(ip)
        for _name in names:
            name: Optional[str] = None
            if isinstance(_name, str):
                name = _name
            elif isinstance(_name, list):
                if not _name:
                    continue
                name = _name[0]
            if name and is_valid_ip(name):
                continue
            if not name:
                continue
            idx = name.find(".")
            if idx > 0:
                return name[:idx]
            else:
                return name
    except Exception:
        print("get hostname of [%s] failed" % ip)
    return None


def get_ip_network(network: str, suppress_error: bool = False) -> Optional[netaddr.IPNetwork]:
    """获取 IP Network。"""
    try:
        ip_network = netaddr.IPNetwork(network)
        return ip_network
    except Exception as e:
        if not suppress_error:
            print("invalid network [%s]: %s", network, e)
        return None


def get_ip_by_if_name(if_name: str = "eth0") -> str:
    """获取当前主机指定网卡的 IP 地址。"""
    import sys
    import platform

    if platform.system() != "Linux":
        return "127.0.0.1"

    try:
        import fcntl
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(
            fcntl.ioctl(  # type: ignore
                s.fileno(),
                0x8915,  # SIOCGIFADDR
                struct.pack('256s', bytes(if_name[:15], 'utf-8'))
            )[20:24]
        )
    except ImportError:
        return 'UNKNOWN'
    except Exception as e:
        print(f"Error getting IP for interface {if_name}: {e}")
        return 'UNKNOWN'


def get_ip_by_hostname(hostname: str, suppress_warning: bool = False, default: Optional[str] = None) -> str:
    """根据主机名称获取 IP 地址。"""
    try:
        socket.setdefaulttimeout(3)
        ip = socket.gethostbyname(hostname)
    except Exception as e:
        print("failed to get host by name [%s]: %s", hostname, e)
        print("get ip of [%s] failed" % hostname)
        return default if default else hostname
    return ip


def get_mac_address(ip_address: str) -> Optional[str]:
    """通过 ARP 获取 MAC 地址。"""
    arp_request = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip_address)
    result = srp(arp_request, timeout=3, verbose=False)[0]
    if result:
        return result[0][1].hwsrc
    return None


def ignore_ssl() -> None:
    """禁用 SSL 证书验证（不推荐，仅用于测试）。"""
    import ssl

    warnings.warn(
        "ignore_ssl() disables SSL verification and should only be used for testing",
        category=RuntimeWarning
    )
    ssl._create_default_https_context = ssl._create_unverified_context  # type: ignore


def normal_exec(args: str, timeout: int = 60) -> Optional[Tuple[int, bytes, bytes]]:
    """执行外部命令。"""
    start_time = datetime.datetime.now()
    pipe = subprocess.Popen(args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True)

    while pipe.poll() is None:
        end_time = datetime.datetime.now()
        total_seconds = (end_time - start_time).total_seconds()
        if total_seconds > timeout:
            pipe.terminate()
            raise Exception("exec cmd timeout, cmd: %s, timeout: %s" % (args, timeout))
        time.sleep(0.1)

    stdout, stderr = pipe.communicate()
    return pipe.returncode, stdout.strip(), stderr.strip()


if __name__ == '__main__':
    print(get_hostname())
    print(get_ip_network("192.168.100.152"))
    print(is_ip_network("192.168.100.152"))
    print(get_hostname_by_ip("127.0.0.1"))
    print(get_hostname_by_ip("192.168.100.152"))
    print(get_ip_by_hostname("localhost"))
    print(is_ip_reachable("192.168.100.151"))
    print(is_ip_port_reachable("192.168.100.151", 22))
    print(is_valid_ip("192.168.100.151"))
    print(is_valid_mac("10:7B:44:80:F4:6A"))
    print(ignore_ssl())
    print(get_mac_address("192.168.110.167"))
    print(get_ip_address())
