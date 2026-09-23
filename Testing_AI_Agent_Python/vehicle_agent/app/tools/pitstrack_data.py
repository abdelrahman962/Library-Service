import time
from typing import Any

from app.config.settings import settings
from app.services.pitstrack import PitstrackClient


class PitstrackDataTool:

    def __init__(self) -> None:

        self.client = PitstrackClient()
        self._vehicles_cache: list[dict[str, Any]] | None = None
        self._vehicles_cached_at = 0.0

    # ========================================================
    # VEHICLES
    # ========================================================

    def vehicles(
        self,
        fetch_all: bool = False,
    ) -> list[dict[str, Any]]:

        # /api/vehicles already returns the account's complete data set in
        # result.data. A short cache avoids downloading the same large payload
        # again for consecutive questions (for example max distance then speed).
        if (
            self._vehicles_cache is not None
            and time.monotonic() - self._vehicles_cached_at
            < settings.pitstrack_vehicles_cache_seconds
        ):
            return self._vehicles_cache

        # This endpoint returns the full account data set in result.data.
        # Requesting numbered pages made the upstream API return the same
        # large result more than once and was the cause of intermittent
        # 90+ second agent failures.
        #
        # Keep fetch_all in the signature for compatibility with callers; a
        # single endpoint response is already the complete data set.
        response = self.client.vehicles()
        rows = self._extract(response)
        self._vehicles_cache, self._vehicles_cached_at = rows, time.monotonic()
        return rows

    # ========================================================
    # WORKING HOURS
    # ========================================================

    def working_hours(
        self,
        vehicle_id: int,
        start_date: str,
        end_date: str,
        page: int = 1,
        unit_id: int | None = None,
    ) -> list[dict[str, Any]]:

        response = (
            self.client.working_hours(
                vehicle_id=vehicle_id,
                start_date=start_date,
                end_date=end_date,
                page=page,
                unit_id=unit_id,
            )
        )

        return self._extract(
            response,
            include_total=True,
        )

    # ========================================================
    # EXTRACT
    # ========================================================

    @staticmethod
    def _extract(
        response: Any,
        include_total: bool = False,
    ) -> list[dict[str, Any]]:

        if isinstance(response, list):

            return [
                row if isinstance(row, dict) else {"value": row}
                for row in response
            ]

        if not isinstance(response, dict):

            return [{"value": response}]

        # ====================================================
        # Pitstrack:
        #
        # {
        #     status: success,
        #     result: {
        #         data: [...],
        #         total: {...}
        #     }
        # }
        # ====================================================

        result = response.get("result")

        if isinstance(result, dict):

            data = result.get("data")

            if isinstance(data, list):

                rows = [
                    row if isinstance(row, dict) else {"value": row}
                    for row in data
                ]

                if include_total:

                    total = result.get("total")

                    if isinstance(total, dict):

                        rows.append({"__summary__": True, **total})

                return rows

        # ====================================================
        # Direct data
        # ====================================================

        data = response.get("data")

        if isinstance(data, list):

            return [
                row if isinstance(row, dict) else {"value": row}
                for row in data
            ]

        # ====================================================
        # Other common wrappers
        # ====================================================

        for key in ("vehicles", "results", "items", "working_hours"):

            value = response.get(key)

            if isinstance(value, list):

                return [
                    row if isinstance(row, dict) else {"value": row}
                    for row in value
                ]

        return [response]
