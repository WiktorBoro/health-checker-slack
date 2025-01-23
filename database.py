# database.py
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from dtos import HealthResultDTO, SlackConnectorConfigDTO, MonthlySummary


class Database:
    DATABASE_BASE_FILE_NAME = "database_base.json"
    DATABASE_FILE_NAME = "database.json"

    def __init__(
        self,
        *,
        current_path: Path,
    ):
        self.current_path = current_path
        self._init()
        self.data = self._open()

    def _init(self) -> None:
        if not os.path.isfile(f"{self.current_path}/{self.DATABASE_FILE_NAME}"):
            with open(
                f"{self.current_path}/{self.DATABASE_BASE_FILE_NAME}", "r"
            ) as database_base_file:
                database_base_data = json.load(database_base_file)
            with open(
                f"{self.current_path}/{self.DATABASE_FILE_NAME}", "w"
            ) as database_file:
                json.dump(database_base_data, database_file)

    def _open(self) -> dict:
        with open(
            f"{self.current_path}/{self.DATABASE_FILE_NAME}", "r"
        ) as database_file:
            return json.load(database_file)

    def commit(self) -> None:
        with open(
            f"{self.current_path}/{self.DATABASE_FILE_NAME}", "w"
        ) as database_file:
            json.dump(self.data, database_file)

    @property
    def current_unhealthy_urls(self) -> List[str]:
        return [
            current_unhealthy
            for current_unhealthy in self.data.get("to_checks", {}).keys()
        ]

    def add_unhealthy(self, *, new_unhealthy: List[HealthResultDTO]) -> None:
        current_unhealthy_urls = self.current_unhealthy_urls
        for unhealthy in new_unhealthy:
            if unhealthy.url not in current_unhealthy_urls:
                self.data["to_checks"][unhealthy.url] = {}
                self.data["to_checks"][unhealthy.url][
                    "unhealthy_at"
                ] = datetime.now().isoformat()
                self.data["to_checks"][unhealthy.url][
                    "last_send_at"
                ] = datetime.now().isoformat()
                self.data["to_checks"][unhealthy.url]["number_of_sent_reminders"] = 0

    def update_still_unhealthy_last_send(
        self, *, still_unhealthy: List[HealthResultDTO]
    ) -> None:
        current_unhealthy_urls = self.current_unhealthy_urls
        for unhealthy in still_unhealthy:
            if unhealthy.is_sent_to_slack and unhealthy.url in current_unhealthy_urls:
                self.data["to_checks"][unhealthy.url][
                    "last_send_at"
                ] = datetime.now().isoformat()
                self.data["to_checks"][unhealthy.url]["number_of_sent_reminders"] += 1

    def remove_unhealthy(self, *, back_to_healthy: List[HealthResultDTO]) -> None:
        for healthy in back_to_healthy:
            self.data["to_checks"].pop(healthy.url, None)

    def update_monthly_summary(self, *, back_to_healthy: List[HealthResultDTO]) -> None:
        year_month = datetime.now().strftime("%Y-%m")
        if year_month not in self.data["monthly_summary"]:
            self._init_month_in_monthly_summary(year_month=year_month)
        for healthy in back_to_healthy:
            if healthy.url not in self.data["monthly_summary"][year_month]:
                self.data["monthly_summary"][year_month][healthy.url] = 0
            self.data["monthly_summary"][year_month][
                healthy.url
            ] += self.get_how_long_was_unhealthy(url=healthy.url)

    def _init_month_in_monthly_summary(self, *, year_month: str):
        self.data["monthly_summary"][year_month] = {}
        self.data["monthly_summary"][year_month]["already_send_this_month"] = False

    def get_summary_for_moth(
        self,
        *,
        year_month: str,  # %Y-%m
    ) -> List[MonthlySummary]:
        if year_month not in self.data["monthly_summary"]:
            return []
        return [
            MonthlySummary(url=url, unhealthy_this_month=unhealthy_this_month)
            for url, unhealthy_this_month in self.data["monthly_summary"][
                year_month
            ].items()
            if url != "already_send_this_month" and unhealthy_this_month != 0
        ]

    def set_monthly_summary_as_send(self, *, year_month: str) -> None:
        self.data["monthly_summary"][year_month]["already_send_this_month"] = True

    def has_already_send_this_month(self, *, year_month: str) -> bool:
        return self.data["monthly_summary"][year_month]["already_send_this_month"]

    def get_how_long_was_unhealthy(self, *, url: str) -> float:
        return round(
            (
                datetime.now()
                - datetime.fromisoformat(
                    self.data["to_checks"]
                    .get(url, {})
                    .get("unhealthy_at", datetime.now().isoformat()),
                )
            ).total_seconds()
            / 60,
        )

    def is_send_still_unhealthy_required(
        self,
        *,
        url: str,
        config: SlackConnectorConfigDTO,
    ) -> bool:
        return (
            datetime.now()
            - datetime.fromisoformat(
                self.data["to_checks"]
                .get(url, {})
                .get("last_send_at", datetime.now().isoformat()),
            )
        ) > timedelta(
            minutes=config.send_still_unhealthy_delay
            + (
                self.data["to_checks"].get(url, {}).get("number_of_sent_reminders", 0)
                * config.increment_each_next_unhealthy_reminder
            )
        )
