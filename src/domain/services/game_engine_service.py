"""Game engine service for mini-game selection and resolution."""

from src.domain.entities import MatchEvent, Prediction, PredictionWindow


class GameEngineService:
    """
    Service for selecting mini-games and resolving prediction windows.

    Game types:
    - NEXT_GOAL_TIMING: Predict the minute of the next goal
    - CORNERS_IN_INTERVAL: Predict number of corners in next interval
    - GOAL_IN_TIME_WINDOW: Predict if a goal will occur in time window
    """

    NEXT_GOAL_TIMING = "NEXT_GOAL_TIMING"
    CORNERS_IN_INTERVAL = "CORNERS_IN_INTERVAL"
    GOAL_IN_TIME_WINDOW = "GOAL_IN_TIME_WINDOW"

    GAMES = (NEXT_GOAL_TIMING, CORNERS_IN_INTERVAL, GOAL_IN_TIME_WINDOW)

    def select_game(self, recent_events: list[MatchEvent], now_ms: int) -> str:
        """
        Select a mini-game based on recent match events.

        Heuristic:
        - If recent corners (last 3 events include CORNER_KICK) → CORNERS_IN_INTERVAL
        - If recent shots → GOAL_IN_TIME_WINDOW
        - Otherwise → NEXT_GOAL_TIMING

        Args:
            recent_events: Recent match events (last N events)
            now_ms: Current time in milliseconds (for determinism)

        Returns:
            Selected game type
        """
        # Check last 3 events for corners
        last_3 = recent_events[-3:] if len(recent_events) >= 3 else recent_events

        has_corner = any(e.event_type == "CORNER_KICK" for e in last_3)
        has_shot = any(e.event_type == "SHOT" for e in last_3)

        if has_corner:
            return self.CORNERS_IN_INTERVAL
        elif has_shot:
            return self.GOAL_IN_TIME_WINDOW
        else:
            return self.NEXT_GOAL_TIMING

    def resolve_window(
        self,
        window: PredictionWindow,
        predictions: list[Prediction],
        events_after_close: list[MatchEvent],
    ) -> dict[str, int]:
        """
        Resolve a prediction window and rank players.

        Args:
            window: The prediction window to resolve
            predictions: All predictions submitted for this window
            events_after_close: Match events that occurred after window closed

        Returns:
            Dictionary mapping user_id to rank (1=best, 2=second, etc.)
            Users who didn't submit predictions are not included.
        """
        if window.game == self.NEXT_GOAL_TIMING:
            return self._resolve_next_goal_timing(predictions, events_after_close)
        elif window.game == self.CORNERS_IN_INTERVAL:
            return self._resolve_corners_in_interval(predictions, events_after_close)
        elif window.game == self.GOAL_IN_TIME_WINDOW:
            return self._resolve_goal_in_time_window(predictions, events_after_close)
        else:
            return {}

    def _resolve_next_goal_timing(
        self,
        predictions: list[Prediction],
        events_after_close: list[MatchEvent],
    ) -> dict[str, int]:
        """Resolve NEXT_GOAL_TIMING: rank by closest to actual goal minute."""
        # Find first goal
        goal_events = [e for e in events_after_close if e.event_type == "GOAL"]
        if not goal_events:
            return {}  # No goal occurred, no winners

        actual_minute = goal_events[0].minute

        # Calculate distances
        user_distances: list[tuple[str, int]] = []
        for pred in predictions:
            try:
                predicted_minute = int(pred.value)
                distance = abs(predicted_minute - actual_minute)
                user_distances.append((pred.user_id, distance))
            except (ValueError, TypeError):
                continue  # Invalid prediction

        if not user_distances:
            return {}

        # Sort by distance (ascending)
        user_distances.sort(key=lambda x: x[1])

        # Assign ranks (handle ties)
        ranks: dict[str, int] = {}
        current_rank = 1
        prev_distance = None

        for user_id, distance in user_distances:
            if prev_distance is not None and distance > prev_distance:
                current_rank = len(ranks) + 1
            ranks[user_id] = current_rank
            prev_distance = distance

        return ranks

    def _resolve_corners_in_interval(
        self,
        predictions: list[Prediction],
        events_after_close: list[MatchEvent],
    ) -> dict[str, int]:
        """Resolve CORNERS_IN_INTERVAL: rank by closest to actual corner count."""
        # Count corners
        actual_corners = sum(1 for e in events_after_close if e.event_type == "CORNER_KICK")

        # Calculate distances
        user_distances: list[tuple[str, int]] = []
        for pred in predictions:
            try:
                predicted_corners = int(pred.value)
                distance = abs(predicted_corners - actual_corners)
                user_distances.append((pred.user_id, distance))
            except (ValueError, TypeError):
                continue

        if not user_distances:
            return {}

        # Sort by distance
        user_distances.sort(key=lambda x: x[1])

        # Assign ranks (handle ties)
        ranks: dict[str, int] = {}
        current_rank = 1
        prev_distance = None

        for user_id, distance in user_distances:
            if prev_distance is not None and distance > prev_distance:
                current_rank = len(ranks) + 1
            ranks[user_id] = current_rank
            prev_distance = distance

        return ranks

    def _resolve_goal_in_time_window(
        self,
        predictions: list[Prediction],
        events_after_close: list[MatchEvent],
    ) -> dict[str, int]:
        """Resolve GOAL_IN_TIME_WINDOW: all correct predictions share rank 1."""
        # Check if goal occurred
        goal_occurred = any(e.event_type == "GOAL" for e in events_after_close)

        ranks: dict[str, int] = {}

        for pred in predictions:
            # Normalize prediction to boolean
            pred_value_str = str(pred.value).lower()
            predicted_yes = pred_value_str in ("yes", "true", "1")

            # Check if prediction matches reality
            if predicted_yes == goal_occurred:
                ranks[pred.user_id] = 1  # All correct share rank 1

        return ranks
