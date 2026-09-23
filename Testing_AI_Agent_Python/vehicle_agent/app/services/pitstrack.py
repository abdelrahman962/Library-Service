from typing import Any

import requests

from app.config.settings import settings


class PitstrackError(RuntimeError):
    pass


class PitstrackClient:

    # Shared across every instance/request: Pitstrack is a remote HTTPS
    # host, so reusing a pooled, keep-alive session avoids a fresh TCP+TLS
    # handshake on every vehicle or working-hours lookup. requests.Session
    # is safe to share across threads for making requests concurrently.
    _session = requests.Session()

    def __init__(self) -> None:

        self.base_url = (
            settings.pitstrack_base_url.rstrip("/")
        )

    def _request(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> Any:

        url = (
            f"{self.base_url}{path}"
        )

        headers = {
            "Accept": "application/json",
        }

        if settings.pitstrack_token:

            headers["Authorization"] = (
                f"Bearer {settings.pitstrack_token}"
            )

        if settings.pitstrack_account_id:

            headers["selected-account"] = (
                settings.pitstrack_account_id
            )

        try:

            response = self._session.get(
                url,
                params=params,
                headers=headers,
                timeout=settings.pitstrack_timeout,
            )

        except requests.RequestException as exc:

            raise PitstrackError(
                f"Pitstrack unavailable: {exc}"
            ) from exc

        if response.status_code >= 400:

            raise PitstrackError(
                f"Pitstrack HTTP {response.status_code}: {response.text}"
            )

        if not response.content:

            return {}

        try:

            return response.json()

        except ValueError as exc:

            raise PitstrackError(
                f"Pitstrack request failed: {exc}"
            ) from exc

    # =====================================================
    # VEHICLES
    # =====================================================

    def vehicles(
        self,
        page: int | None = None,
    ) -> Any:

        return self._request(
            "/api/vehicles",
            {"page": page} if page is not None else None,
        )

    # =====================================================
    # WORKING HOURS
    # =====================================================

    def working_hours(
        self,
        vehicle_id: int,
        start_date: str,
        end_date: str,
        page: int = 1,
        unit_id: int | None = None,
    ) -> Any:

        params: dict[str, Any] = {
            "start_date": start_date,
            "end_date": end_date,
            "page": page,
        }

        if unit_id is not None:

            params["units[0]"] = int(
                unit_id
            )

        path = (
            "/api/vehicles/working_hours/"
            f"[{int(vehicle_id)}]"
        )

        return self._request(
            path,
            params,
        )
