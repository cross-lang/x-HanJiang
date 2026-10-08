#!/usr/bin/env python3
"""
AI 助手 agent 循环模块的纯函数单元测试

测试 src/assistant/agent.py 中不依赖 LLM / 仓储的辅助逻辑：
    - chunk_text：边界感知切块（空文本 / 短文本 / 句号对齐 / 无边界硬切）
"""

from src.assistant.agent import chunk_text


class TestBoundaryChunker:
    """边界感知切块测试。"""

    def test_empty_text_yields_nothing(self):
        """空文本：无任何片段。"""
        assert list(chunk_text("")) == []

    def test_short_text_single_piece(self):
        """短于窗口：整块返回。"""
        assert list(chunk_text("短文本")) == ["短文本"]

    def test_cuts_at_chinese_sentence_boundary(self):
        """超长文本：非末块在句号处对齐，不劈开句子。"""
        text = "这是第一句话。这是第二句话。这是第三句话。这是第四句话。结尾"
        pieces = list(chunk_text(text))
        assert "".join(pieces) == text
        assert all(len(piece) <= 24 for piece in pieces)
        assert all(piece[-1] == "。" for piece in pieces[:-1])

    def test_hard_cut_when_no_boundary(self):
        """窗口内无任何边界字符：退回硬切，仍保证有界与无损。"""
        text = "字" * 100
        pieces = list(chunk_text(text))
        assert "".join(pieces) == text
        assert [len(piece) for piece in pieces] == [24, 24, 24, 24, 4]
