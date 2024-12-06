# slack_connector.py
from datetime import datetime
from typing import List

from slack_sdk.webhook import WebhookClient
import logging

from dtos import SlackConnectorConfigDTO, HealthCheckDTO, HealthResultDTO


class SlackConnector:
    DEFAULT_HELLO_MESSAGE = ":wave: Hi, we are connected! Let's go! :tada:"
    DEFAULT_HEALTHY_MESSAGE = "URL {url} is fine :heart:"
    DEFAULT_UNHEALTHY_MESSAGE = (
        "URL {url} is dead :firecracker::skull_and_crossbones::firecracker:"
    )
    DEFAULT_NO_UNHEALTHY_MESSAGE = "Everything is fine :green_heart:"
    DEFAULT_BACK_TO_HEALTHY_MESSAGE = (
        "URL {url}, back to live! :tada: Total dead time {how_long_was_unhealthy} min"
    )
    DEFAULT_STILL_UNHEALTHY_MESSAGE = "URL {url}, is still dead :firecracker::skull_and_crossbones::firecracker: Total dead time {how_long_was_unhealthy} min"

    DEFAULT_MONTHLY_SUMMARY = "Summary for last month: \n{summary}\n The remaining services had 100% efficiency last month!:tada:"

    def __init__(
        self,
        *,
        repository,
        slack_webhook_url: str,
        slack_connector_config: SlackConnectorConfigDTO,
    ):
        self.repository = repository
        self.connector = WebhookClient(url=slack_webhook_url)
        self.config = slack_connector_config

    def send_health_check_report(self, health_check_dto: HealthCheckDTO):
        if self.config.send_back_to_healthy:
            self._send_results(
                health_results=health_check_dto.back_to_healthy,
                message=self.config.back_to_healthy_message
                or self.DEFAULT_BACK_TO_HEALTHY_MESSAGE,
            )
        if self.config.send_still_unhealthy:
            self._send_results(
                health_results=self._get_still_unhealthy_ready_to_send(
                    still_unhealthy=health_check_dto.still_unhealthy
                ),
                message=self.config.still_unhealthy_message
                or self.DEFAULT_STILL_UNHEALTHY_MESSAGE,
            )
        if self.config.send_healthy:
            self._send_results(
                health_results=health_check_dto.healthy,
                message=self.config.healthy_message or self.DEFAULT_HEALTHY_MESSAGE,
            )
        if self.config.send_unhealthy:
            self._send_results(
                health_results=health_check_dto.unhealthy,
                message=self.config.unhealthy_message or self.DEFAULT_UNHEALTHY_MESSAGE,
            )

    def _get_still_unhealthy_ready_to_send(
        self,
        *,
        still_unhealthy: List[HealthResultDTO],
    ) -> List[HealthResultDTO]:
        return [
            unhealthy
            for unhealthy in still_unhealthy
            if self.repository.is_send_still_unhealthy_required(
                url=unhealthy.url,
                config=self.config,
            )
        ]

    def hello_message(self):
        self._send(text=self.config.hello_message or self.DEFAULT_HELLO_MESSAGE)

    def send_monthly_summary(self, *, summary):
        self._send(
            text=(self.config.monthly_summary or self.DEFAULT_MONTHLY_SUMMARY).format(
                summary=summary
            )
        )

    def send_if_there_no_unhealthy(self):
        if self.config.send_if_there_no_unhealthy:
            self._send(
                text=self.config.no_unhealthy_message
                or self.DEFAULT_NO_UNHEALTHY_MESSAGE
            )

    def _send_results(
        self,
        *,
        message: str,
        health_results: List[HealthResultDTO],
    ):
        for health_result in health_results:
            self._send(
                text=message.format(
                    url=health_result.url,
                    param=health_result.param,
                    status_code=health_result.status_code,
                    is_healthy=health_result.is_healthy,
                    how_long_was_unhealthy=self.repository.get_how_long_was_unhealthy(
                        url=health_result.url
                    ),
                )
            )
            health_result.is_sent_to_slack = True

    def _send(self, *, text: str):
        try:
            response = self.connector.send(text=text)
            assert response.status_code == 200
            logging.info(f"{datetime.now()} - send to slack: success - text: {text}")
        except AssertionError:
            logging.info(f"{datetime.now()} - send to slack: failed - text: {text}")
        except Exception as e:
            logging.info(
                f"{datetime.now()} - send to slack: failed - text: {text}, {e}"
            )
