#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""超预测档案文件读写助手（archive_io）

为什么需要它
------------
在某些环境下，编辑工具修改 ~/.workbuddy/forecast-archive/ 下**既有文件**时会失败，
报 `ModifyBackup failed ... target stat failed (fail-closed): 参数错误 (os error 87)`，
或 Python 直写报 `PermissionError: [Errno 13]`（新建文件仍正常）。
实测：同一目录下部分文件可正常修改、部分不可，根因未知。

本脚本用直接文件 IO 完成写入并**回读校验**，用于规避上述问题。

用法
----
  python archive_io.py stat   <目标文件>
  python archive_io.py read   <目标文件>
  python archive_io.py write  <目标文件> <内容来源文件>      # 覆盖写入
  python archive_io.py append <目标文件> <内容来源文件>      # 追加写入

约定
----
- 一律 UTF-8
- write / append 完成后自动回读校验（字节数 + sha1），不一致即报错退出
- 只做文件搬运，不做内容解释；内容由调用方准备
"""

import hashlib
import os
import shutil
import sys

USAGE = __doc__


def sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_parent(path):
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.isdir(parent):
        os.makedirs(parent, exist_ok=True)


def cmd_stat(target):
    if not os.path.exists(target):
        print("不存在：%s" % target)
        return 1
    st = os.stat(target)
    print("路径：%s" % os.path.abspath(target))
    print("大小：%d 字节" % st.st_size)
    print("sha1：%s" % sha1_of(target))
    return 0


def cmd_read(target):
    if not os.path.exists(target):
        print("不存在：%s" % target, file=sys.stderr)
        return 1
    with open(target, "r", encoding="utf-8") as fh:
        sys.stdout.write(fh.read())
    return 0


def cmd_write(target, src, append=False):
    if not os.path.exists(src):
        print("内容来源文件不存在：%s" % src, file=sys.stderr)
        return 1

    with open(src, "r", encoding="utf-8") as fh:
        payload = fh.read()

    ensure_parent(target)
    existed = os.path.exists(target)
    before = sha1_of(target) if existed else None

    mode = "a" if append else "w"
    try:
        with open(target, mode, encoding="utf-8", newline="\n") as fh:
            fh.write(payload)
    except PermissionError as exc:
        print("[失败] 无写入权限：%s" % exc, file=sys.stderr)
        print("提示：可先删除目标文件再用本脚本重建（内容由调用方提供）。",
              file=sys.stderr)
        return 2

    # 回读校验
    with open(target, "r", encoding="utf-8") as fh:
        back = fh.read()
    if append:
        if not back.endswith(payload):
            print("[校验失败] 追加内容未出现在文件末尾", file=sys.stderr)
            return 3
    else:
        if back != payload:
            print("[校验失败] 回读内容与写入内容不一致", file=sys.stderr)
            return 3

    st = os.stat(target)
    print("写入成功（%s）：%s" % ("追加" if append else "覆盖", os.path.abspath(target)))
    print("大小：%d 字节　sha1：%s" % (st.st_size, sha1_of(target)))
    if before and not append:
        print("写入前 sha1：%s（已变更）" % before)
    return 0


def main(argv):
    if len(argv) < 3:
        print(USAGE)
        return 1
    action, target = argv[1], argv[2]
    if action == "stat":
        return cmd_stat(target)
    if action == "read":
        return cmd_read(target)
    if action in ("write", "append"):
        if len(argv) < 4:
            print("缺少内容来源文件", file=sys.stderr)
            print(USAGE)
            return 1
        return cmd_write(target, argv[3], append=(action == "append"))
    print("未知操作：%s" % action, file=sys.stderr)
    print(USAGE)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
