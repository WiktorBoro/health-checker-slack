# monthly_summary.py
from datetime import datetime, timedelta

from database import Database
from dtos import MonthlySummaryConfigDTO
from slack_connector import SlackConnector


class MonthlySummary:
    DEFAULT_SEND_AT_HOUR = "11:00"
    AVERAGE_MINUTES_IN_MONTH = 43800

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
        summary_for_moth = self.repository.get_summary_for_moth(
            year_month=datetime(
                year=last_month.year,
                month=last_month.month,
                day=1,
            ).strftime("%Y-%m")
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

        summary = ""
        for url_with_monthly_dead_time in summary_for_moth:
            summary += f"{url_with_monthly_dead_time.url}: {url_with_monthly_dead_time.unhealthy_this_month} min, efficiency: {round((self.AVERAGE_MINUTES_IN_MONTH-url_with_monthly_dead_time.unhealthy_this_month)/self.AVERAGE_MINUTES_IN_MONTH, 2)}%\n"

        if summary:
            self.connector.send_monthly_summary(summary=summary)

        self.repository.set_monthly_summary_as_send(year_month=current_year_month)
