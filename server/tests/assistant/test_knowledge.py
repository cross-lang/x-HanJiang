#!/usr/bin/env python3
"""静态知识库（系统提示词组装）单元测试。

测试 src/assistant/memories/knowledge.py：
    - load_assistant_faq：FAQ 数据加载与各类结构校验分支（文件缺失 / YAML 错误 /
      顶层结构非法 / 条目字段缺失或类型错误 / entry_path 非法 / id 重复 / 空列表）
    - load_prompt_template：系统提示词模板加载与占位符校验
    - SystemPromptBuilder：match_faq 确定性召回、按权限过滤入口路由表、
      系统提示词四块组装（用户档案兜底 / RAG 补充块 / FAQ 优先参考块渲染）

所有数据文件用 tmp_path 临时生成，不依赖真实 YAML 资产，不触网、不连库。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from src.assistant.memories.knowledge import (
    SystemPromptBuilder,
    default_faq_path,
    default_prompt_path,
    load_assistant_faq,
    load_prompt_template,
)
from src.constants.assistant import ASSISTANT_ENTRY_CATALOG

#: 合法 FAQ 数据（entry_path 取自真实入口路由表，保证通过校验）
_VALID_FAQ_YAML = """\
faq:
  - id: faq_user
    keywords: ["用户管理", "新增用户"]
    question: "如何新增用户？"
    answer: "进入用户管理页，点击新增按钮填写表单。"
    entry_path: "/users"
  - id: faq_role
    keywords: ["角色分配"]
    question: "如何为用户分配角色？"
    answer: "进入角色管理，为用户绑定权限。"
    entry_path: ""
"""

#: 合法系统提示词模板（含全部必需占位符与 FAQ 块模板；块标量内容须统一缩进）
_VALID_PROMPT_YAML = """\
system_prompt: |
  【系统入口】
  {entries_block}
  【用户档案】
  {user_block}
  {faq_block}
  {rag_block}
faq_block_template: |
  【优先参考】
  问：{hit_question}
  答：{hit_answer}
  跳转：{hit_entry_path}
"""


def _write(tmp_path: Path, name: str, text: str) -> Path:
    """把文本写入临时文件并返回路径。"""
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


# ============================================================
# load_assistant_faq
# ============================================================


class TestLoadAssistantFaq:
    """FAQ 加载与校验分支测试。"""

    def test_default_paths_are_under_templates(self):
        """默认路径指向 assistant_templates 目录下的两个资产文件。"""
        assert default_faq_path().name == "assistant_faq.yaml"
        assert default_prompt_path().name == "assistant_prompt.yaml"

    def test_missing_file_raises(self):
        """数据文件缺失抛 ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            load_assistant_faq(Path("不存在的文件.yaml"))

    def test_broken_yaml_raises(self, tmp_path: Path):
        """YAML 语法错误抛 ValueError。"""
        path = _write(tmp_path, "broken.yaml", "faq: [未闭合")
        with pytest.raises(ValueError, match="YAML 解析失败"):
            load_assistant_faq(path)

    @pytest.mark.parametrize(
        "bad_content",
        [
            "不是字典",  # 顶层非 dict
            "faq: 123",  # faq 不是列表
            'faq: ["字符串条目"]',  # 条目不是对象
        ],
    )
    def test_structure_invalid_raises(self, tmp_path: Path, bad_content: str):
        """顶层结构非法（非 dict / faq 非列表 / 条目非对象）抛 ValueError。"""
        path = _write(tmp_path, "bad_struct.yaml", bad_content)
        with pytest.raises(ValueError):
            load_assistant_faq(path)

    @pytest.mark.parametrize(
        "field, bad_entry",
        [
            ("id", '- keywords: ["k"]\n    question: q\n    answer: a'),
            ("keywords", "- id: x\n    keywords: []\n    question: q\n    answer: a"),
            ("keywords 类型", "- id: x\n    keywords: [1]\n    question: q\n    answer: a"),
            ("question", '- id: x\n    keywords: ["k"]\n    answer: a'),
            ("answer", '- id: x\n    keywords: ["k"]\n    question: q'),
            (
                "entry_path",
                '- id: x\n    keywords: ["k"]\n    question: q\n    answer: a\n    entry_path: "/not-exist"',
            ),
        ],
    )
    def test_field_invalid_raises(self, tmp_path: Path, field: str, bad_entry: str):
        """单字段缺失 / 类型错误 / entry_path 不在入口目录时抛 ValueError。"""
        content = f"faq:\n  {bad_entry}\n"
        path = _write(tmp_path, f"bad_{field}.yaml", content)
        with pytest.raises(ValueError):
            load_assistant_faq(path)

    def test_duplicate_id_raises(self, tmp_path: Path):
        """id 重复抛 ValueError。"""
        content = """\
faq:
  - id: same
    keywords: ["甲"]
    question: "q1"
    answer: "a1"
  - id: same
    keywords: ["乙"]
    question: "q2"
    answer: "a2"
"""
        path = _write(tmp_path, "dup.yaml", content)
        with pytest.raises(ValueError, match="重复"):
            load_assistant_faq(path)

    def test_empty_faq_raises(self, tmp_path: Path):
        """faq 列表为空抛 ValueError。"""
        path = _write(tmp_path, "empty.yaml", "faq: []\n")
        with pytest.raises(ValueError, match="为空"):
            load_assistant_faq(path)

    def test_valid_load_keeps_order(self, tmp_path: Path):
        """合法数据按文件顺序加载，entry_path 缺省为空串。"""
        path = _write(tmp_path, "ok.yaml", _VALID_FAQ_YAML)
        items = load_assistant_faq(path)
        assert [item.id for item in items] == ["faq_user", "faq_role"]
        assert items[0].keywords == ("用户管理", "新增用户")
        assert items[0].entry_path == "/users"
        # 第二条 entry_path 缺省 → 空串（表示无需跳转）
        assert items[1].entry_path == ""


# ============================================================
# load_prompt_template
# ============================================================


class TestLoadPromptTemplate:
    """系统提示词模板加载与校验分支测试。"""

    def test_missing_file_raises(self):
        """模板文件缺失抛 ValueError。"""
        with pytest.raises(ValueError, match="不存在"):
            load_prompt_template(Path("不存在的模板.yaml"))

    def test_missing_system_prompt_raises(self, tmp_path: Path):
        """缺少 system_prompt 字段抛 ValueError。"""
        path = _write(tmp_path, "no_sp.yaml", 'faq_block_template: "x"\n')
        with pytest.raises(ValueError, match="system_prompt"):
            load_prompt_template(path)

    def test_missing_placeholder_raises(self, tmp_path: Path):
        """system_prompt 缺任一必需占位符抛 ValueError。"""
        content = 'system_prompt: "{entries_block} 少了其他占位符"\nfaq_block_template: "x"\n'
        path = _write(tmp_path, "no_ph.yaml", content)
        with pytest.raises(ValueError, match="占位符"):
            load_prompt_template(path)

    def test_missing_faq_block_template_raises(self, tmp_path: Path):
        """缺少 faq_block_template 字段抛 ValueError。"""
        content = 'system_prompt: "{entries_block}{user_block}{faq_block}{rag_block}"\n'
        path = _write(tmp_path, "no_faq_tpl.yaml", content)
        with pytest.raises(ValueError, match="faq_block_template"):
            load_prompt_template(path)

    def test_empty_faq_block_template_raises(self, tmp_path: Path):
        """faq_block_template 为空串抛 ValueError。"""
        content = 'system_prompt: "{entries_block}{user_block}{faq_block}{rag_block}"\nfaq_block_template: ""\n'
        path = _write(tmp_path, "empty_faq_tpl.yaml", content)
        with pytest.raises(ValueError, match="faq_block_template"):
            load_prompt_template(path)

    def test_valid_load(self, tmp_path: Path):
        """合法模板返回 PromptTemplate，两个字段均为字符串。"""
        path = _write(tmp_path, "ok.yaml", _VALID_PROMPT_YAML)
        tpl = load_prompt_template(path)
        assert "{entries_block}" in tpl.system_prompt
        assert "{hit_answer}" in tpl.faq_block_template


# ============================================================
# SystemPromptBuilder
# ============================================================


@pytest.fixture()
def builder(tmp_path: Path) -> SystemPromptBuilder:
    """用临时 FAQ / 模板文件构造组装器（隔离真实资产）。"""
    return SystemPromptBuilder(
        faq_path=_write(tmp_path, "faq.yaml", _VALID_FAQ_YAML),
        prompt_path=_write(tmp_path, "prompt.yaml", _VALID_PROMPT_YAML),
    )


class TestMatchFaq:
    """确定性关键词召回测试。"""

    def test_blank_question_returns_none(self, builder: SystemPromptBuilder):
        """空白问题不召回。"""
        assert builder.match_faq("   ") is None

    def test_hit_by_first_keyword(self, builder: SystemPromptBuilder):
        """命中任一关键词即召回（子串匹配）。"""
        hit = builder.match_faq("请问在哪里新增用户？")
        assert hit is not None
        assert hit.id == "faq_user"

    def test_priority_follows_file_order(self, builder: SystemPromptBuilder):
        """同时可命中多条时，按文件顺序返回第一条。"""
        hit = builder.match_faq("新增用户的角色分配怎么操作")
        assert hit is not None
        assert hit.id == "faq_user"  # faq_user 排在 faq_role 之前

    def test_no_hit_returns_none(self, builder: SystemPromptBuilder):
        """无关键词命中返回 None。"""
        assert builder.match_faq("今天天气怎么样") is None


class TestBuildEntriesBlock:
    """按权限过滤系统入口路由表测试。"""

    def test_none_permissions_returns_all(self, builder: SystemPromptBuilder):
        """权限为 None 时返回全量入口。"""
        out = builder._build_entries_block(None)
        assert out.count("\n- ") + (1 if out.startswith("- ") else 0) == len(ASSISTANT_ENTRY_CATALOG)

    def test_wildcard_returns_all(self, builder: SystemPromptBuilder):
        """含 "*" 超管通配时返回全量入口。"""
        out = builder._build_entries_block({"*"})
        assert "首页" in out
        assert "个人中心" in out

    def test_empty_permissions_only_public_entries(self, builder: SystemPromptBuilder):
        """空权限集合只保留登录即可访问（permission 为空）的入口。"""
        out = builder._build_entries_block(set())
        public_titles = [item["title"] for item in ASSISTANT_ENTRY_CATALOG if not item["permission"]]
        private_titles = [item["title"] for item in ASSISTANT_ENTRY_CATALOG if item["permission"]]
        for title in public_titles:
            assert title in out
        for title in private_titles:
            assert title not in out

    def test_partial_permissions_filtered(self, builder: SystemPromptBuilder):
        """传入某入口所需权限码时，该入口可见、其余私有入口不可见。"""
        sample = next(item for item in ASSISTANT_ENTRY_CATALOG if item["permission"])
        out = builder._build_entries_block({sample["permission"]})
        assert sample["title"] in out
        other_private = next(
            item for item in ASSISTANT_ENTRY_CATALOG if item["permission"] and item["title"] != sample["title"]
        )
        assert other_private["title"] not in out


class TestBuildSystemPrompt:
    """系统提示词四块组装测试。"""

    def test_empty_user_context_uses_fallback(self, builder: SystemPromptBuilder):
        """用户档案为空时模板给出通用兜底文案。"""
        out = builder.build_system_prompt(user_context="")
        assert "暂无" in out

    def test_user_context_injected(self, builder: SystemPromptBuilder):
        """有用户档案时原样注入。"""
        out = builder.build_system_prompt(user_context="- 管理员")
        assert "- 管理员" in out

    def test_retriever_context_adds_block(self, builder: SystemPromptBuilder):
        """RAG 有结果时追加【补充知识】块；为空时不出现。"""
        with_retrieval = builder.build_system_prompt(retriever_context="向量召回的知识")
        assert "补充知识" in with_retrieval
        assert "向量召回的知识" in with_retrieval
        without = builder.build_system_prompt(retriever_context="")
        assert "补充知识" not in without

    def test_faq_hit_renders_reference_block(self, builder: SystemPromptBuilder):
        """问题命中 FAQ 时渲染【优先参考】块，含标准答案与跳转路径。"""
        out = builder.build_system_prompt(user_question="怎么新增用户")
        assert "如何新增用户？" in out
        assert "进入用户管理页" in out
        assert "/users" in out

    def test_faq_hit_with_empty_entry_path_uses_no_jump(self, builder: SystemPromptBuilder):
        """entry_path 为空时跳转位置显示「无需跳转」。"""
        out = builder.build_system_prompt(user_question="帮我做角色分配")
        assert "无需跳转" in out

    def test_no_faq_hit_leaves_block_empty(self, builder: SystemPromptBuilder):
        """未命中 FAQ 时优先参考块为空（占位符被替换为空串）。"""
        out = builder.build_system_prompt(user_question="今天天气如何")
        assert "优先参考" not in out

    def test_permissions_affect_entries_block(self, builder: SystemPromptBuilder):
        """按权限过滤后的入口表进入系统提示词。"""
        out = builder.build_system_prompt(user_permissions=set())
        assert "个人中心" in out  # 登录即可访问
        assert "用户管理" not in out  # 需要权限码，空权限集合下不可见
