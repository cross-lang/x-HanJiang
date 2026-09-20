#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
压缩解压模块

提供 ZIP 与 7z（py7zr）格式的解压能力，支持指定输出目录与可选的子目录创建策略。
"""

import zipfile
import py7zr
from pathlib import Path
from typing import Any


def extract_zip(zip_file_path: str | Path, extract_folder: str | Path) -> None:
    """解压 ZIP 文件到指定目录。"""
    extract_path = Path(extract_folder)
    extract_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(extract_path)


class SevenZipExtractor:

    filters: list[dict[str, Any]] = [
        {
            'id': py7zr.FILTER_LZMA2,
            'options': {'dict_size': 65536, 'lc': 3, 'lp': 0, 'pb': 2}
        },
    ]

    def __init__(self, archive_path: str | Path, password: str | None = None) -> None:
        self.archive_path = Path(archive_path)
        self.password = password

    def extract_all(self, output_path: str | Path = ".", create_subfolder: bool = True) -> str | None:
        out_dir = Path(output_path)
        out_dir.mkdir(parents=True, exist_ok=True)

        with py7zr.SevenZipFile(self.archive_path, mode="r", password=self.password, filters=self.filters) as archive:
            if create_subfolder:
                names = archive.getnames()
                base_name = names[0].split("/")[0] if names else self.archive_path.stem
                out_dir = out_dir / base_name

            archive.extractall(str(out_dir))
            return str(out_dir)



if __name__ == "__main__":
    # 创建SevenZipExtractor实例，传入7z文件的路径和解压密码（如果有的话）
    extractor = SevenZipExtractor("your_archive.7z", password="your_password")

    # 指定解压缩的目标路径，默认为当前工作目录
    output_directory = "output_folder"

    # 调用extract_all方法进行解压缩，并指定是否创建子文件夹
    extractor.extract_all(output_directory, create_subfolder=True)
