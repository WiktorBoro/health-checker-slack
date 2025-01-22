# health_check.py
import asyncio
import logging
from datetime import datetime
from typing import List

import aiohttp

from requests.exceptions import ConnectTimeout, ReadTimeout

from dtos import HealthResultDTO, HealthCheckDTO, HealthCheckConfigDTO

import to_checks_types as types


class HealthCheck:
    HEALTHY_STATUS_CODE = 200

    def __init__(
        self,
        *,
        health_check_config: HealthCheckConfigDTO,
    ):
        self.config = health_check_config

    async def execute(
        self,
        *,
        to_checks: List[types.ToChecksTypedDict],
        current_unhealthy_urls: List[str],  # List[urls]
        health_check_dto: HealthCheckDTO,
    ) -> None:
        tasks = [
            self._health_check(
                param=param,
                url=to_check["url_base"].format(param=param),
            )
            for to_check in to_checks
            for param in to_check["params"]
        ]
        health_results = await asyncio.gather(*tasks)
        for health_result in health_results:
            self._add_result_to_group(
                health_result=health_result,
                health_check_dto=health_check_dto,
                current_unhealthy_urls=current_unhealthy_urls,
            )

    def _add_result_to_group(
        self,
        *,
        health_result: HealthResultDTO,
        health_check_dto: HealthCheckDTO,
        current_unhealthy_urls: List[str],
    ) -> None:
        is_current_unhealthy = health_result.url in current_unhealthy_urls
        is_healthy = health_result.is_healthy
        if is_healthy:
            {
                True: health_check_dto.back_to_healthy,
                False: health_check_dto.healthy,
            }[
                is_current_unhealthy
            ].append(health_result)
        elif not is_healthy:
            {
                True: health_check_dto.still_unhealthy,
                False: health_check_dto.new_unhealthy,
            }[is_current_unhealthy].append(health_result)

    async def _health_check(
        self,
        *,
        url: str,
        param: str,
    ) -> HealthResultDTO:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=self.config.timeout) as response:
                    status_code = response.status
                    health_result = HealthResultDTO(
                        is_healthy=status_code == self.HEALTHY_STATUS_CODE,
                        status_code=status_code,
                        param=param,
                        url=url,
                    )
        except asyncio.TimeoutError:
            health_result = HealthResultDTO(
                is_healthy=False,
                status_code=-1,
                param=param,
                url=url,
                error_message="Client-side timeout",
            )
        except aiohttp.ClientConnectionError:
            health_result = HealthResultDTO(
                is_healthy=False,
                status_code=-1,
                param=param,
                url=url,
                error_message="Connection error occurred",
            )
        except aiohttp.ClientResponseError as e:
            health_result = HealthResultDTO(
                is_healthy=False,
                status_code=e.status,
                param=param,
                url=url,
                error_message=str(e.message),
            )
        except aiohttp.InvalidURL:
            health_result = HealthResultDTO(
                is_healthy=False,
                status_code=-1,
                param=param,
                url=url,
                error_message="Invalid URL",
            )
        except aiohttp.ClientPayloadError:
            health_result = HealthResultDTO(
                is_healthy=False,
                status_code=-1,
                param=param,
                url=url,
                error_message="Payload error",
            )
        except aiohttp.ClientError as e:
            health_result = HealthResultDTO(
                is_healthy=False,
                status_code=-1,
                param=param,
                url=url,
                error_message=str(e),
            )

        logging.info(
            f"{datetime.now()} - url: {health_result.url} - param: {health_result.param} - status_code: {health_result.status_code} - is_healthy: {health_result.is_healthy} - error_message: {health_result.error_message}"
        )
        return health_result
