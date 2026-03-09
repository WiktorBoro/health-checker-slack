# monthly_summary.py
import math
from datetime import datetime, timedelta

from database import Database
from dtos import MonthlySummaryConfigDTO
from slack_connector import SlackConnector


class MonthlySummary:
    DEFAULT_SEND_AT_HOUR = "11:00"
    AVERAGE_MINUTES_IN_MONTH = 43800
    ONE_HUNDRED_PERCENT = 100

    def __init__(
        self,
        *,
        config: MonthlySummaryConfigDTO,
        connector: SlackConnector,
        repository: Database,
    ):
        self.config = config
        self.connector = connector
        self.repository = repository

    def execute(self) -> None:
        now = datetime.now()
        current_year_month = now.strftime("%Y-%m")
        last_month = now.replace(day=1) - timedelta(days=2)

        has_already_send_this_month = self.repository.has_already_send_this_month(
            year_month=current_year_month
        )
        last_month_year_month = datetime(
            year=last_month.year,
            month=last_month.month,
            day=1,
        ).strftime("%Y-%m")
        summary_for_moth = self.repository.get_summary_for_moth(
            year_month=last_month_year_month
        )
        count_100_percent = self.repository.get_count_100_percent_domains(
            year_month=last_month_year_month
        )

        hour, minute = (self.config.send_at_hour or self.DEFAULT_SEND_AT_HOUR).split(
            ":"
        )
        send_monthly_summary_at_first_day_of_month = (
            self.config.send_monthly_summary_at_first_day_of_month
        )
        time_to_send = datetime(
            year=now.year,
            month=now.month,
            day=1,
            hour=int(hour),
            minute=int(minute),
        )

        if (
            now < time_to_send
            or has_already_send_this_month
            or not send_monthly_summary_at_first_day_of_month
        ):
            return

        tier_high = []
        tier_mid = []
        tier_low = []

        for entry in summary_for_moth:
            efficiency = self._get_percent_efficiency(
                unhealthy_this_month=entry.unhealthy_this_month
            )
            if efficiency >= 99.90:
                tier_high.append((entry.url, efficiency))
            elif efficiency >= 99.50:
                tier_mid.append((entry.url, efficiency))
            else:
                tier_low.append((entry.url, efficiency))

        summary = (
            f"efficiency 100% number of domains: {count_100_percent}\n"
            f"efficiency 100%-99.90% number of domains: {len(tier_high)}\n"
            f"efficiency 99.90%-99.50% number of domains: {len(tier_mid)}\n"
        )
        if tier_low:
            domains_detail = ", ".join(
                f"{url}: {eff}%" for url, eff in tier_low
            )
            summary += f"efficiency below 99.50% number of domains: {len(tier_low)} [{domains_detail}]\n"
        else:
            summary += f"efficiency below 99.50% number of domains: 0\n"

        self.connector.send_monthly_summary(summary=summary)
        self.repository.set_monthly_summary_as_send(year_month=current_year_month)

    def _get_percent_efficiency(self, *, unhealthy_this_month: int) -> float:
        return (
            math.floor(
                (
                    (self.AVERAGE_MINUTES_IN_MONTH - unhealthy_this_month)
                    / self.AVERAGE_MINUTES_IN_MONTH
                    * self.ONE_HUNDRED_PERCENT
                )
                * 10**2
            )
            / 10**2
        )
