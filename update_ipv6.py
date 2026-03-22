#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import ipaddress
import logging
from datetime import datetime

# ===== 配置 =====
WORK_DIR = os.getcwd()
if ("/home/veryrrd/projects/pclpage-2pch" in WORK_DIR):
    pass
else:
    WORK_DIR = "/opt/a"
IPV6_FILE = 'ipv6'
LOG_FILE = 'update_ipv6.log'
GIT_COMMIT_MSG = 'Update Address'

# ===== 日志设置 =====
logging.basicConfig(
    filename=os.path.join(WORK_DIR, LOG_FILE),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def log_info(msg):
    print(msg)
    logging.info(msg)

def log_error(msg):
    print(msg, file=sys.stderr)
    logging.error(msg)

def get_global_ipv6():
    """获取当前主机的全局 IPv6 地址（scope global，非临时地址）"""
    try:
        # 执行 ip -6 addr show，捕获输出
        result = subprocess.run(
            # enp1s0
            ['ip', '-6', 'addr', 'show', 'ens37'],
            capture_output=True,
            text=True,
            check=True
        )
    except subprocess.CalledProcessError as e:
        log_error(f"执行 ip 命令失败: {e}")
        return None

    lines = result.stdout.splitlines()
    for line in lines:
        # 查找包含 'scope global' 的行，且不是临时地址（temporary）
        if 'scope global' in line and 'temporary' not in line:
            # 行格式类似：inet6 2001:db8::1/64 scope global
            parts = line.strip().split()
            if len(parts) >= 2:
                addr_with_prefix = parts[1]
                # 去掉 /64 后缀，只保留地址
                addr = addr_with_prefix.split('/')[0]
                # 验证是否为有效 IPv6 地址
                try:
                    ipaddress.IPv6Address(addr)
                    return addr
                except ipaddress.AddressValueError:
                    continue
    log_error("未找到有效的全局 IPv6 地址")
    return None

def read_stored_ipv6():
    """读取已存储的 IPv6 地址"""
    filepath = os.path.join(WORK_DIR, IPV6_FILE)
    if not os.path.isfile(filepath):
        return None
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip()
            if content:
                return content
    except Exception as e:
        log_error(f"读取 {IPV6_FILE} 失败: {e}")
    return None

def write_current_ipv6(addr):
    """将新地址写入文件"""
    filepath = os.path.join(WORK_DIR, IPV6_FILE)
    try:
        with open(filepath, 'w') as f:
            f.write(addr + '\n')
        log_info(f"已写入新地址: {addr}")
    except Exception as e:
        log_error(f"写入 {IPV6_FILE} 失败: {e}")
        return False
    return True

def compare_prefix(addr1, addr2):
    """比较两个 IPv6 地址的 /64 前缀是否相同"""
    if not addr1 or not addr2:
        return False
    try:
        net1 = ipaddress.IPv6Network(f"{addr1}/64", strict=False)
        net2 = ipaddress.IPv6Network(f"{addr2}/64", strict=False)
        return net1.network_address == net2.network_address
    except Exception as e:
        log_error(f"比较前缀时出错: {e}")
        return False

def run_git_command(cmd):
    """执行 git 命令，工作目录为 WORK_DIR，返回成功与否"""
    try:
        result = subprocess.run(
            cmd,
            cwd=WORK_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        log_info(f"成功执行: {' '.join(cmd)}")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Git 命令失败: {' '.join(cmd)}")
        log_error(f"stderr: {e.stderr}")
        return False

def main():
    # 切换到工作目录
    try:
        os.chdir(WORK_DIR)
    except Exception as e:
        log_error(f"无法切换到工作目录 {WORK_DIR}: {e}")
        sys.exit(1)

    log_info("开始检查 IPv6 地址变更")

    # 1. 获取当前 IPv6
    current_addr = get_global_ipv6()
    if not current_addr:
        log_error("获取当前 IPv6 地址失败，退出")
        sys.exit(1)

    # 2. 读取存储的 IPv6
    stored_addr = read_stored_ipv6()
    if not stored_addr:
        log_info("未找到存储的 IPv6 地址，将首次写入")

    # 3. 前缀比较
    if stored_addr and compare_prefix(current_addr, stored_addr):
        log_info("前缀未变化，无需操作")
        sys.exit(0)

    log_info("前缀发生变化，准备更新")

    # 4. 写入新地址
    if not write_current_ipv6(current_addr):
        sys.exit(1)

    # ===== TODO: 在此处添加修改其他文件的逻辑 =====
    # 例如：修改某个配置文件
    # with open('some_file', 'w') as f:
    #     f.write(...)
    # ============================================

    if current_addr.startswith("240e:3b4:38ab:4a50"):
        print("本地测试，拉了")
        sys.exit(1)
    # 4.5 先pull
    if not run_git_command(['git', 'pull']):
        sys.exit(1)

    # 5. Git 操作
    # 添加所有变更（也可指定具体文件）
    if not run_git_command(['git', 'add', '.']):
        sys.exit(1)

    # 提交
    if not run_git_command(['git', 'commit', '-m', GIT_COMMIT_MSG]):
        sys.exit(1)

    # 推送
    if not run_git_command(['git', 'push']):
        sys.exit(1)

    log_info("更新完成并已推送到 GitHub")

if __name__ == '__main__':
    main()