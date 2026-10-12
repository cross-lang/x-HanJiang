#!/usr/bin/env python3
"""
仪表盘统计服务测试（src/services/admin/dashboard_service.py）

DashboardService 只负责把 Repository 返回的原始统计行组装成前端结构，
本测试用 Fake DashboardRepository（SimpleNamespace 行对象）替代真实 SQLAlchemy
查询，不连数据库，覆盖：
    - get_stats：各板块组装、趋势数组补零、中文标签映射、空数据兜底
    - _build_openapi_stats：开放平台卡片、审批状态/趋势、最近申请
    - get_my_activity：个人最近登录 / 操作日志组装
"""

from datetime import date, datetime, timedelta
from types import SimpleNamespace

from src.services.admin.dashboard_service import DashboardService


def _trend_row(day: str, count: int) -> SimpleNamespace:
    return SimpleNamespace(date=day, count=count)


class FakeDashboardRepository:
    """内存版仪表盘仓库替身，默认全空；测试可按需覆盖各查询。"""

    def __init__(self) -> None:
        self.cards = (0, 0, 0)
        self.today_login = 0
        self.login_trend_rows: list = []
        self.audit_trend_rows: list = []
        self.role_dist_rows: list = []
        self.recent_login_rows: list = []
        self.recent_audit_rows: list = []
        self.user_status_rows: list = []
        self.new_users_rows: list = []
        self.login_failed_rows: list = []
        self.notify_channel_rows: list = []
        self.notify_status_rows: list = []
        self.storage_by_folder: list = []
        self.storage_total_size = 0
        self.storage_total_count = 0
        self.app_status_rows: list = []
        self.developer_count = 0
        self.reg_status_rows: list = []
        self.reg_trend_rows: list = []
        self.reg_review_rows: list = []
        self.recent_reg_rows: list = []
        self.my_login_rows: list = []
        self.my_audit_rows: list = []

    def card_counts(self):
        return self.cards

    def today_login_count(self, day):
        return self.today_login

    def login_trend(self, start_date):
        return self.login_trend_rows

    def audit_trend(self, start_date):
        return self.audit_trend_rows

    def role_distribution(self):
        return self.role_dist_rows

    def recent_logins(self, limit=10):
        return self.recent_login_rows

    def recent_audits(self, limit=10):
        return self.recent_audit_rows

    def user_status_distribution(self):
        return self.user_status_rows

    def new_users_trend(self, start_date):
        return self.new_users_rows

    def login_failed_trend(self, start_date):
        return self.login_failed_rows

    def notify_channel_distribution(self):
        return self.notify_channel_rows

    def notify_status_trend(self, start_date):
        return self.notify_status_rows

    def storage_stats(self):
        return self.storage_total_size, self.storage_total_count, self.storage_by_folder

    def openapi_app_status_distribution(self):
        return self.app_status_rows

    def openapi_developer_count(self):
        return self.developer_count

    def openapi_registration_status_distribution(self):
        return self.reg_status_rows

    def openapi_registration_trend(self, start_date):
        return self.reg_trend_rows

    def openapi_registration_review_trend(self, start_date):
        return self.reg_review_rows

    def recent_openapi_registrations(self, limit=6):
        return self.recent_reg_rows

    def my_logins(self, user_id, limit=10):
        return self.my_login_rows

    def my_audits(self, user_id, limit=10):
        return self.my_audit_rows


def _populated_repo() -> FakeDashboardRepository:
    """构造一组已知数据，便于断言组装逻辑。"""
    repo = FakeDashboardRepository()
    today = date.today()
    week_ago = today - timedelta(days=6)

    repo.cards = (10, 3, 4)
    repo.today_login = 5
    repo.login_trend_rows = [_trend_row(week_ago.isoformat(), 2), _trend_row(today.isoformat(), 3)]
    repo.audit_trend_rows = [_trend_row(today.isoformat(), 7)]
    repo.role_dist_rows = [
        SimpleNamespace(role_name="超级管理员", count=1),
        SimpleNamespace(role_name="普通用户", count=9),
    ]
    repo.recent_login_rows = [
        (
            SimpleNamespace(id=1, ip_address="1.2.3.4", status="success", created_at=datetime(2026, 10, 12, 10, 0, 0)),
            "alice",
            "Alice",
        ),
        # 用户名为空 → 展示 "-"；created_at 为 None → 不格式化
        (
            SimpleNamespace(id=2, ip_address="5.6.7.8", status="failed", created_at=None),
            None,
            None,
        ),
    ]
    repo.recent_audit_rows = [
        (
            SimpleNamespace(id=9, entity_type="user", action="create", ip_address="9.9.9.9", created_at=None),
            "bob",
            "Bob",
        )
    ]
    repo.user_status_rows = [SimpleNamespace(status="enabled", count=8), SimpleNamespace(status="disabled", count=2)]
    repo.new_users_rows = [_trend_row(today.isoformat(), 1)]
    repo.login_failed_rows = [_trend_row(today.isoformat(), 2)]
    repo.notify_channel_rows = [SimpleNamespace(channel="email", count=5), SimpleNamespace(channel="station", count=8)]
    repo.notify_status_rows = [
        SimpleNamespace(date=today.isoformat(), status="success", count=4),
        SimpleNamespace(date=week_ago.isoformat(), status="failed", count=1),
        SimpleNamespace(date=today.isoformat(), status="pending", count=2),
    ]
    repo.storage_by_folder = [SimpleNamespace(folder="avatars", count=3, size=1024)]
    repo.storage_total_size = 2048
    repo.storage_total_count = 3
    repo.app_status_rows = [SimpleNamespace(status="active", count=4), SimpleNamespace(status="disabled", count=1)]
    repo.developer_count = 6
    repo.reg_status_rows = [SimpleNamespace(status="pending", count=2), SimpleNamespace(status="approved", count=8)]
    repo.reg_trend_rows = [_trend_row(today.isoformat(), 1)]
    repo.reg_review_rows = [_trend_row(today.isoformat(), 1)]
    repo.recent_reg_rows = [
        (
            SimpleNamespace(
                registration_code="R20261012",
                name="我的应用",
                registration_type="create",
                status="pending",
                created_at=None,
            ),
            "developer",
            "张三",
            None,
        )
    ]
    repo.my_login_rows = [
        SimpleNamespace(id=11, ip_address="10.0.0.1", login_type="password", status="success", created_at=None)
    ]
    repo.my_audit_rows = [
        SimpleNamespace(id=22, entity_type="role", action="update", ip_address="10.0.0.2", created_at=None)
    ]
    return repo


class TestGetStats:
    """get_stats 组装。"""

    def test_populated_assembles_all_sections(self) -> None:
        repo = _populated_repo()
        service = DashboardService(repository=repo)
        result = service.get_stats()

        # 关键指标卡片
        assert result["cards"] == {"user_count": 10, "role_count": 3, "app_count": 4, "today_login": 5}
        # 近7天趋势：长度恒为 7，补零对齐
        assert len(result["login_trend"]["dates"]) == 7
        assert result["login_trend"]["counts"][0] == 2  # week_ago
        assert result["login_trend"]["counts"][6] == 3  # today
        # 角色分布
        assert result["role_distribution"] == [
            {"name": "超级管理员", "value": 1},
            {"name": "普通用户", "value": 9},
        ]
        # 最近登录：空用户名兜底为 "-"，created_at 为 None
        assert result["recent_logins"][0]["username"] == "alice"
        assert result["recent_logins"][1]["username"] == "-"
        assert result["recent_logins"][1]["created_at"] is None
        # 用户状态中文标签
        assert result["user_status_distribution"] == [
            {"name": "启用", "value": 8},
            {"name": "禁用", "value": 2},
        ]
        # 通知渠道中文标签 + 保留 channel 标识
        email_dist = result["notify_channel_distribution"][0]
        assert email_dist["name"] == "邮件"
        assert email_dist["channel"] == "email"
        assert email_dist["value"] == 5
        # 通知成功率趋势：pending 归入失败桶
        assert result["notify_trend"]["success"][6] == 4
        assert result["notify_trend"]["failed"][0] == 1
        assert result["notify_trend"]["failed"][6] == 2
        # 存储用量
        assert result["storage_usage"]["total_size_bytes"] == 2048
        assert result["storage_usage"]["by_folder"] == [{"folder": "avatars", "count": 3, "size_bytes": 1024}]

    def test_empty_repository_yields_zeroed_trends(self) -> None:
        """无任何统计行：趋势数组全 0，不抛异常。"""
        service = DashboardService(repository=FakeDashboardRepository())
        result = service.get_stats()

        assert len(result["login_trend"]["counts"]) == 7
        assert result["login_trend"]["counts"] == [0] * 7
        assert len(result["new_users_trend"]["counts"]) == 30
        assert result["new_users_trend"]["counts"] == [0] * 30
        assert result["cards"] == {"user_count": 0, "role_count": 0, "app_count": 0, "today_login": 0}
        assert result["openapi"]["cards"]["app_total"] == 0
        assert result["openapi"]["cards"]["pending_registrations"] == 0


class TestOpenapiStats:
    """开放平台统计板块。"""

    def test_openapi_cards_and_labels(self) -> None:
        repo = _populated_repo()
        service = DashboardService(repository=repo)
        result = service.get_stats()
        openapi = result["openapi"]

        # 应用总数 = 各状态之和；待审批数
        assert openapi["cards"]["app_total"] == 5
        assert openapi["cards"]["developer_count"] == 6
        assert openapi["cards"]["pending_registrations"] == 2
        assert openapi["cards"]["week_registrations"] == 1
        # 应用状态中文
        assert openapi["app_status_distribution"][0] == {"name": "启用", "value": 4}
        # 审批状态中文
        assert openapi["registration_status_distribution"][0]["name"] == "待审批"
        # 最近申请：类型 / 状态中文标签，归属人取开发者名
        reg = openapi["recent_registrations"][0]
        assert reg["registration_code"] == "R20261012"
        assert reg["registration_type"] == "创建申请"
        assert reg["status_label"] == "待审批"
        assert reg["owner_name"] == "张三"
        assert reg["created_at"] is None


class TestMyActivity:
    """个人最近活动。"""

    def test_assembles_my_logins_and_audits(self) -> None:
        repo = _populated_repo()
        service = DashboardService(repository=repo)
        result = service.get_my_activity(user_id=7)

        assert result["recent_logins"][0]["ip_address"] == "10.0.0.1"
        # 登录方式中文标签（password → 密码）
        assert result["recent_logins"][0]["login_type_label"] == "密码"
        assert result["recent_audits"][0]["entity_type"] == "role"
        assert result["recent_audits"][0]["action"] == "update"
