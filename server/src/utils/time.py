#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
时间日期工具模块

提供常用的日期时间生成、格式校验、时间戳与日期互转、区间计算、周/月/季度边界计算等工具方法。
"""

import time
import datetime
import random
from typing import Any, Optional


def gen_random_today_date() -> str:
    """生成随机的今日时间。"""
    random_hour = str(random.randint(0, 23))
    random_min = str(random.randint(0, 59))
    random_second = str(random.randint(0, 59))

    today = datetime.datetime.now().strftime('%Y-%m-%d')
    today_time = '%s %s:%s:%s' % (today, random_hour, random_min, random_second)
    return today_time


def is_valid_date(date_str: str) -> bool:
    """验证日期格式。"""
    try:
        if ":" in date_str:
            time.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        else:
            time.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def timestamp_to_date(ts: int) -> str:
    """将时间戳转换为日期。"""
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def timestamp_to_date_without_second(ts: int) -> str:
    """将时间戳转换为日期（不含秒）。"""
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def timestamp_to_day(ts: int) -> str:
    """将时间戳转换为天。"""
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")


def date_to_timestamp(date_str: str) -> int:
    """将日期转换为时间戳，date_str 格式为 '%Y-%m-%d %H:%M:%S'。"""
    return int(time.mktime(time.strptime(date_str, '%Y-%m-%d %H:%M:%S')))


def day_to_timestamp(day_str: str) -> int:
    """将天转换为时间戳，day_str 格式为 '%Y-%m-%d'。"""
    return int(time.mktime(time.strptime(day_str, '%Y-%m-%d')))


def datetime_to_str(dt: datetime.datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """将 datetime 类型转换为字符串类型。"""
    return dt.strftime(format_str)


def datetime_to_datetime(dt: datetime.datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> datetime.datetime:
    """将 datetime 转为字符串再转回 datetime（用于截断秒等）。"""
    dt_str = dt.strftime(format_str)
    return datetime.datetime.strptime(dt_str, format_str)


def get_today_weekday() -> int:
    """获取今天是星期几。"""
    return datetime.datetime.now().weekday()


def get_weekday_by_date(date: datetime.date) -> int:
    """获取指定日期是星期几。"""
    return date.weekday()


def get_now_day() -> str:
    """获得今天的日期。"""
    return datetime.datetime.now().strftime("%Y-%m-%d")


def get_now_hour() -> str:
    """获得现在的小时。"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H")


def get_now_datetime() -> datetime.datetime:
    """获取当前时间。"""
    return datetime.datetime.now()


def get_now_minute() -> str:
    """获得现在的分钟。"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def get_now_second() -> str:
    """获得现在的秒。"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_now_timestamp() -> int:
    """获取当前时间戳。"""
    return int(time.time())


def get_now_datetime_str() -> str:
    """获得现在的时间字符串。"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_before_day(number: int = 1, format_str: str = "%Y-%m-%d") -> str:
    """获取前几天的日期。"""
    today = datetime.date.today()
    oneday = datetime.timedelta(days=number)
    yesterday = today - oneday
    return yesterday.strftime(format_str)


def get_before_day_by_date(date: Any, number: int = 1, format_str: str = "%Y-%m-%d") -> str:
    """获取指定日期前几天的日期。"""
    oneday = datetime.timedelta(days=number)
    yesterday = date - oneday
    return yesterday.strftime(format_str)


def get_after_day(number: int = 1, format_str: str = "%Y-%m-%d") -> str:
    """获取后几天的日期。"""
    today = datetime.date.today()
    oneday = datetime.timedelta(days=number)
    tomorrow = today + oneday
    return tomorrow.strftime(format_str)


def get_after_day_by_date(date: Any, number: int = 1, format_str: str = "%Y-%m-%d") -> str:
    """获取指定日期后几天的日期。"""
    oneday = datetime.timedelta(days=number)
    tomorrow = date + oneday
    return tomorrow.strftime(format_str)


def is_weekday(date: Any = None) -> bool:
    """判断是工作日还是周末。"""
    if not date:
        date = datetime.datetime.now()
    return True if date.weekday() <= 4 else False


def is_today(ts: int) -> bool:
    """时间戳对应的日期是不是今天。"""
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    today_start_ts = int(time.mktime(time.strptime(today_str, "%Y-%m-%d")))
    today_end_ts = today_start_ts + 86400
    return today_start_ts <= ts < today_end_ts

def is_lastday(ts: int) -> bool:
    """时间戳对应的日期是不是昨天。"""
    now = datetime.datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    today_start_ts = int(time.mktime(time.strptime(today_str, "%Y-%m-%d")))
    last_day_start_ts = today_start_ts - 86400
    return last_day_start_ts <= ts < today_start_ts


def is_between_start_and_end_ts(ts: int, start_ts: int, end_ts: int) -> bool:
    """时间戳是否在开始和结束时间戳之间。"""
    return start_ts <= ts <= end_ts


def get_week_start_day(current_datetime: Optional[datetime.date] = None) -> datetime.date:
    """获取本周周一的日期。"""
    if current_datetime is None:
        current_datetime = datetime.datetime.now().date()
    current_week_num = current_datetime.weekday()
    return current_datetime - datetime.timedelta(days=current_week_num)


def get_week_end_day(current_datetime: Optional[datetime.date] = None) -> datetime.date:
    """获取本周周日的日期。"""
    if current_datetime is None:
        current_datetime = datetime.datetime.now().date()
    current_week_num = current_datetime.weekday()
    return current_datetime + datetime.timedelta(days=6 - current_week_num)


def get_last_week_start_day() -> datetime.date:
    """获取上周周一的日期。"""
    week_start_date = get_week_start_day()
    return week_start_date - datetime.timedelta(days=7)


def get_last_week_end_day() -> datetime.date:
    """获取上周周日的日期。"""
    week_start_date = get_week_start_day()
    return week_start_date - datetime.timedelta(days=1)


def get_last_month_start_day() -> datetime.date:
    """获取上个月第一天的日期。"""
    today = datetime.date.today()
    last_month_end_day = datetime.date(today.year, today.month, 1) - datetime.timedelta(1)
    return datetime.date(last_month_end_day.year, last_month_end_day.month, 1)


def get_last_month_end_day() -> datetime.date:
    """获取上个月最后一天的日期。"""
    today = datetime.date.today()
    return datetime.date(today.year, today.month, 1) - datetime.timedelta(1)


def get_current_month_start_day() -> datetime.date:
    """获取当前月第一天的日期。"""
    today = datetime.date.today()
    return datetime.date(today.year, today.month, 1)


def get_last_quarter_start_day() -> datetime.date:
    """获取上个季度第一天的日期。"""
    today = datetime.date.today()
    month = today.month

    if month in [1, 2, 3]:
        year = today.year - 1
        return datetime.date(year, 10, 1)
    elif month in [4, 5, 6]:
        return datetime.date(today.year, 1, 1)
    elif month in [7, 8, 9]:
        return datetime.date(today.year, 4, 1)
    elif month in [10, 11, 12]:
        return datetime.date(today.year, 7, 1)
    else:
        raise Exception('month error')


def get_last_quarter_end_day() -> datetime.date:
    """获取上个季度最后一天的日期。"""
    today = datetime.date.today()
    month = today.month

    if month in [1, 2, 3]:
        year = today.year - 1
        return datetime.date(year, 12, 31)
    elif month in [4, 5, 6]:
        return datetime.date(today.year, 3, 31)
    elif month in [7, 8, 9]:
        return datetime.date(today.year, 6, 30)
    elif month in [10, 11, 12]:
        return datetime.date(today.year, 9, 30)
    else:
        raise Exception('month error')


def get_datetime_range(start: Any, end: Any, step: int = 86400) -> list[int]:
    """获取两个时间戳范围内的所有时间戳列表，步长默认为一天。"""
    res: list[int] = []
    i = start
    while i <= end:
        res.append(i)
        i += step
    return res


def get_date_list_by_day_range(start_date: str, end_date: str) -> list[str]:
    """根据开始和结束日期获得日期列表。"""
    date_list: list[str] = []
    begin_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    while begin_dt <= end_dt:
        date_str = begin_dt.strftime("%Y-%m-%d")
        date_list.append(date_str)
        begin_dt += datetime.timedelta(days=1)
    return date_list


def get_weekday_list_by_week_range(week_start: datetime.date, week_end: datetime.date) -> list[int]:
    """根据开始和结束的周时间，获得这个时间内的所有周几列表。"""
    weekday_list: list[int] = []
    date = week_start
    while date <= week_end:
        weekday_list.append(date.weekday())
        date += datetime.timedelta(days=1)
    return weekday_list


def get_msec_timestamp() -> int:
    """生成秒的时间戳乘以 1000。"""
    return int(time.time() * 1000)


def get_ts_start(ts: int) -> int:
    """获取该时间戳当天的起始时间戳。"""
    dt = datetime.datetime.fromtimestamp(ts)
    return int(time.mktime(dt.replace(hour=0, minute=0, second=0, microsecond=0).timetuple()))


def get_ts_end(ts: int) -> int:
    """获取该时间戳当天的结束时间戳。"""
    return get_ts_start(ts) + 86400 - 1


if __name__ == '__main__':
    print(get_weekday_list_by_week_range(
        get_last_week_start_day(),
        get_last_week_end_day()
    ))
