"""Safe, model-callable data tools for the autonomous vehicle agent.

The language model chooses *when* to use a tool. This module only
describes the available capabilities and executes a selected capability
safely; it does not classify questions or match words from a user
message.
"""

from __future__ import annotations

import math
import re
import secrets
from typing import Any

from app.tools.pitstrack_data import PitstrackDataTool


# Schemas describe capabilities rather than question patterns. Ollama
# receives them with every request and decides semantically whether
# data is needed.
VEHICLES_TOOL = {
    "type": "function",
    "function": {
        "name": "get_vehicles",
        "description": (
            "Read current Pitstrack vehicle records. Use only for factual, "
            "current vehicle/fleet data. Common fields include id, name, "
            "odometer, speed, vehicle_status, driver_name, device_number, "
            "longitude, and latitude. Results can be filtered, sorted, "
            "limited, or sampled at random. Every result includes "
            "matched_count, the exact number before limiting or sampling. "
            "Use matched_count for the total number of all matching fleet "
            "entries; it counts the complete retrieved result rather than "
            "just the rows shown to the model."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "filters": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/filter"},
                },
                "sort": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "direction": {"type": "string", "enum": ["asc", "desc"]},
                    },
                    "required": ["field"],
                    "description": (
                        "Ordering of returned records. Use desc for a "
                        "maximum, fastest-to-slowest, newest-to-oldest, or "
                        "largest-to-smallest request; use asc for the "
                        "opposite ordering."
                    ),
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                "selection": {
                    "type": "string",
                    "enum": ["first", "random"],
                    "description": (
                        "Use random for a random sample. Use first when no "
                        "random selection is requested."
                    ),
                },
                "fields": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": (
                        "Optional vehicle fields needed in the answer. "
                        "Omit for a concise safe record view."
                    ),
                },
            },
            "$defs": {
                "filter": {
                    "type": "object",
                    "properties": {
                        "field": {"type": "string"},
                        "operator": {"type": "string"},
                        "value": {},
                    },
                    "required": ["field", "operator"],
                },
            },
        },
    },
}

WORKING_HOURS_TOOL = {
    "type": "function",
    "function": {
        "name": "get_working_hours",
        "description": (
            "Read Pitstrack working-hours data for one vehicle over an "
            "explicit date range. Use after obtaining a vehicle id when "
            "the answer needs working hours, distance, or the supplied "
            "period summary."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "vehicle_id": {"type": "integer"},
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format.",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format.",
                },
                "page": {"type": "integer", "minimum": 1},
                "unit_id": {"type": "integer"},
            },
            "required": ["vehicle_id", "start_date", "end_date"],
        },
    },
}

TOOLS = [
    VEHICLES_TOOL,
    WORKING_HOURS_TOOL,
]


class AgentTools:
    """Executes the small allow-list of agent capabilities."""

    MAX_ROWS = 50

    def __init__(self) -> None:
        self.pitstrack = PitstrackDataTool()

    def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        user_id: int,
    ) -> Any:
        handlers = {
            "get_vehicles": self.get_vehicles,
            "get_working_hours": self.get_working_hours,
        }
        handler = handlers.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        return handler(arguments, user_id)

    def get_vehicles(
        self,
        arguments: dict[str, Any],
        _: int,
    ) -> dict[str, Any]:
        arguments = self._normalize_vehicle_arguments(arguments)
        rows = self.pitstrack.vehicles(fetch_all=True)
        rows = self._filter_rows(rows, self._filters(arguments.get("filters")))

        # Older local model responses may use result_mode="random" although
        # random selection belongs to the independent `selection` argument.
        # Normalize that equivalent call rather than rejecting valid data.
        legacy_mode = str(arguments.get("result_mode", "")).lower()
        if legacy_mode in {"random", "sample", "sampled"}:
            arguments = {**arguments, "selection": "random"}

        rows = self._sort_rows(rows, self._sort(arguments.get("sort")))
        matched_count = len(rows)
        limit = self._limit(arguments.get("limit"))
        selection = str(arguments.get("selection", "first")).lower()

        # Accept a harmless equivalent emitted by some models while
        # retaining a strict public schema.
        if arguments.get("random") is True:
            selection = "random"

        if selection not in {"first", "random"}:
            raise ValueError("selection must be first or random.")

        if selection == "random":
            shown = secrets.SystemRandom().sample(rows, min(limit, matched_count))
        else:
            shown = rows[:limit]

        return {
            "matched_count": matched_count,
            "selection": selection,
            "records": self._vehicle_view(shown, arguments.get("fields")),
        }

    @staticmethod
    def _normalize_vehicle_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
        """Accept equivalent structured calls emitted by local models.

        This is deliberately structural rather than language based: the
        model still decides whether vehicle data is needed and what it
        means. It merely prevents harmless JSON wrappers such as
        ``{"number": 60}`` and the common ``select`` alias from corrupting
        a valid query.
        """
        normalized = dict(arguments)
        if "fields" not in normalized and isinstance(normalized.get("select"), list):
            normalized["fields"] = normalized["select"]
        if "sort" not in normalized:
            for alias in ("order_by", "order", "orderBy"):
                if alias in normalized:
                    normalized["sort"] = normalized[alias]
                    break
        return normalized

    @staticmethod
    def _vehicle_view(
        rows: list[dict[str, Any]],
        fields: Any,
    ) -> list[dict[str, Any]]:
        """Return compact factual records that fit safely in model context."""
        default_fields = (
            "id", "name", "icon", "vehicle_type", "manufacturer", "model",
            "vehicle_status", "driver_name", "odometer", "speed",
            "last_update_point", "device_number",
        )

        if fields is None:
            selected = default_fields
        elif isinstance(fields, list) and all(isinstance(field, str) for field in fields):
            selected = tuple(dict.fromkeys(["id", "name", *fields]))
        else:
            raise ValueError("fields must be an array of field names.")

        return [
            {
                field: row.get(field)
                for field in selected
                if field in row
            }
            for row in rows
        ]

    def get_working_hours(
        self,
        arguments: dict[str, Any],
        _: int,
    ) -> list[dict[str, Any]]:
        required = ("vehicle_id", "start_date", "end_date")
        if any(arguments.get(key) in (None, "") for key in required):
            raise ValueError("vehicle_id, start_date and end_date are required.")

        return self.pitstrack.working_hours(
            vehicle_id=int(arguments["vehicle_id"]),
            start_date=str(arguments["start_date"]),
            end_date=str(arguments["end_date"]),
            page=max(int(arguments.get("page", 1)), 1),
            unit_id=(
                int(arguments["unit_id"])
                if arguments.get("unit_id") is not None
                else None
            ),
        )[: self.MAX_ROWS]

    @staticmethod
    def _filters(value: Any) -> list[dict[str, Any]]:
        if value is None:
            return []

        # Tool-capable local models often return semantically equivalent JSON
        # shapes, e.g. {"speed": {"operator": ">", "value": 20}} or
        # {"speed": ">20"}. Normalize structure here; interpretation of the
        # user's language still belongs entirely to the model.
        if isinstance(value, dict):
            if value.get("field"):
                value = [value]
            else:
                expanded: list[dict[str, Any]] = []
                for field, condition in value.items():
                    if isinstance(condition, dict):
                        mongo_operators = {
                            "$eq": "=", "$ne": "!=", "$gt": ">",
                            "$gte": ">=", "$lt": "<", "$lte": "<=",
                            "$in": "in", "$nin": "not in",
                        }
                        if len(condition) == 1:
                            raw_operator, raw_value = next(iter(condition.items()))
                            if raw_operator in mongo_operators:
                                expanded.append({
                                    "field": field,
                                    "operator": mongo_operators[raw_operator],
                                    "value": raw_value,
                                })
                                continue
                        expanded.append({
                            "field": condition.get("field", field),
                            "operator": condition.get("operator", "="),
                            "value": condition.get("value"),
                        })
                        continue

                    if isinstance(condition, str):
                        match = re.fullmatch(
                            r"\s*(>=|<=|!=|<>|>|<|=)\s*(.+?)\s*",
                            condition,
                        )
                        if match:
                            raw_value = match.group(2)
                            try:
                                parsed_value: Any = float(raw_value)
                                if parsed_value.is_integer():
                                    parsed_value = int(parsed_value)
                            except ValueError:
                                parsed_value = raw_value
                            expanded.append({
                                "field": field,
                                "operator": match.group(1),
                                "value": parsed_value,
                            })
                            continue

                    expanded.append({
                        "field": field,
                        "operator": "=",
                        "value": condition,
                    })
                value = expanded

        if not isinstance(value, list):
            raise ValueError("filters must be an array or object.")

        filters: list[dict[str, Any]] = []
        for item in value:
            if isinstance(item, dict) and isinstance(item.get("properties"), dict):
                properties = item["properties"]
                if not properties.get("field"):
                    filters.extend(AgentTools._filters(properties))
                    continue
                item = properties
            if not isinstance(item, dict) or not item.get("field"):
                raise ValueError("Each filter needs a field.")
            normalized_item = dict(item)
            normalized_item["value"] = AgentTools._unwrap_model_value(
                normalized_item.get("value")
            )
            filters.append(normalized_item)
        return filters

    @staticmethod
    def _unwrap_model_value(value: Any) -> Any:
        """Unwrap scalar JSON containers produced by tool-calling models."""
        if isinstance(value, list):
            return [AgentTools._unwrap_model_value(item) for item in value]
        if not isinstance(value, dict):
            return value

        # JSON-schema-style scalar emitted by some tool-calling runtimes,
        # e.g. {"type": "boolean", "value": true}.
        if "value" in value and set(value).issubset({"type", "value"}):
            return AgentTools._unwrap_model_value(value["value"])

        scalar_keys = (
            "number", "integer", "float", "value", "text", "string",
            "boolean", "bool",
        )
        present = [key for key in scalar_keys if key in value]
        if len(value) == 1 and len(present) == 1:
            return AgentTools._unwrap_model_value(value[present[0]])
        return value

    @classmethod
    def _limit(cls, value: Any) -> int:
        try:
            return min(max(int(value or 20), 1), cls.MAX_ROWS)
        except (TypeError, ValueError):
            return 20

    @staticmethod
    def _sort(value: Any) -> dict[str, str] | None:
        if value is None:
            return None
        if (
            isinstance(value, dict)
            and "field" not in value
            and len(value) == 1
        ):
            field, direction = next(iter(value.items()))
            value = {"field": field, "direction": direction}
        if not isinstance(value, dict) or not isinstance(value.get("field"), str):
            raise ValueError("sort requires a field.")

        direction = str(value.get("direction", "asc")).lower()
        if direction not in {"asc", "desc"}:
            raise ValueError("sort direction must be asc or desc.")
        return {"field": value["field"], "direction": direction}

    @staticmethod
    def _matches(row: dict[str, Any], condition: dict[str, Any]) -> bool:
        field = str(condition.get("field", ""))
        operator = str(condition.get("operator", "=")).strip().lower()
        expected = condition.get("value")
        actual = row.get(field)

        if operator == "is null":
            return actual is None
        if operator == "is not null":
            return actual is not None
        if operator in {"in", "not in"}:
            if not isinstance(expected, list):
                return False
            matched = actual in expected
            return not matched if operator == "not in" else matched
        if operator in {"like", "not like"}:
            matched = str(expected or "").lower() in str(actual or "").lower()
            return not matched if operator == "not like" else matched
        if operator in {">", ">=", "<", "<="}:
            if actual is None or expected is None:
                return False
            try:
                left, right = float(actual), float(expected)
            except (TypeError, ValueError):
                return False
            return {
                ">": left > right,
                ">=": left >= right,
                "<": left < right,
                "<=": left <= right,
            }[operator]
        if operator in {"=", "=="}:
            return actual == expected or str(actual).lower() == str(expected).lower()
        if operator in {"!=", "<>"}:
            return not AgentTools._matches(row, {**condition, "operator": "="})
        return False

    @classmethod
    def _filter_rows(
        cls,
        rows: list[dict[str, Any]],
        filters: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            row for row in rows
            if isinstance(row, dict) and all(cls._matches(row, item) for item in filters)
        ]

    @staticmethod
    def _sort_rows(
        rows: list[dict[str, Any]],
        sort: dict[str, str] | None,
    ) -> list[dict[str, Any]]:
        if not sort:
            return rows

        field = sort["field"]

        numeric_rows: list[tuple[dict[str, Any], float]] = []
        text_rows: list[dict[str, Any]] = []
        missing_rows: list[dict[str, Any]] = []

        for row in rows:
            value = row.get(field)
            if value is None or str(value).strip() in {"", "-"}:
                missing_rows.append(row)
                continue
            try:
                number = float(value)
                if math.isfinite(number):
                    numeric_rows.append((row, number))
                    continue
            except (TypeError, ValueError):
                pass
            text_rows.append(row)

        # When a field is numeric, invalid/missing values never represent a
        # maximum and must stay after valid values even in descending order.
        if numeric_rows:
            ordered_numeric = sorted(
                numeric_rows,
                key=lambda item: item[1],
                reverse=sort["direction"] == "desc",
            )
            return [row for row, _ in ordered_numeric] + text_rows + missing_rows

        return sorted(
            text_rows,
            key=lambda row: str(row.get(field) or "").lower(),
            reverse=sort["direction"] == "desc",
        ) + missing_rows
