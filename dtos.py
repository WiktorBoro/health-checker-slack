# dtos.py
from typing import List

from attr import frozen, define


@frozen(kw_only=True)
class SlackConnectorConfigDTO:
    send_healthy: bool = False
    send_unhealthy: bool = True
    send_still_unhealthy: bool = True
    send_still_unhealthy_delay: int = 30  # min
    increment_each_next_unhealthy_reminder: int = 0  # min
    send_back_to_healthy: bool = True
    send_if_there_no_unhealthy: bool = False
    hello_message: str = ""
    healthy_message: str = ""
    unhealthy_message: str = ""
    no_unhealthy_message: str = ""
    back_to_healthy_message: str = ""
    still_unhealthy_message: str = ""
    monthly_summary: str = ""


@frozen(kw_only=True)
class HealthCheckConfigDTO:
    timeout: int = 3


@frozen(kw_only=True)
class MonthlySummaryConfigDTO:
    send_monthly_summary_at_first_day_of_month: bool = False
    send_at_hour: str = ""


@define
class HealthResultDTO:
    is_healthy: bool
    status_code: int
    url: str
    param: str
    is_sent_to_slack: bool = False
    error_message: str = ""


@define(kw_only=True)
class HealthCheckDTO:
    healthy: List[HealthResultDTO]
    new_unhealthy: List[HealthResultDTO]
    still_unhealthy: List[HealthResultDTO]
    back_to_healthy: List[HealthResultDTO]


@frozen(kw_only=True)
class MonthlySummary:
    url: str
    unhealthy_this_month: int  # sec
