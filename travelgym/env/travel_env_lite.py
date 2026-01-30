"""
TravelEnvLite: A simplified Gymnasium environment without preference elicitation.

This environment only processes search actions and updates observations.
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, Any, Tuple
import re
import random

from .action_parser import (
    parse_action,
    perform_search,
    build_search_feedback,
    ActionParseError,
)
from .task_data import load_tasks, get_task_by_id
from ..config import TravelGymConfig, get_default_config


class TravelEnvLite(gym.Env):
    """Lite TravelGym environment that skips preference elicitation."""

    def __init__(self, config: TravelGymConfig = None):
        super().__init__()

        self.config = config if config is not None else get_default_config()
        self.config.validate()

        if self.config.seed is not None:
            random.seed(self.config.seed)
            np.random.seed(self.config.seed)

        self.current_task_index = 0
        self._load_tasks()

        self.action_space = spaces.Text(max_length=1000)
        self.observation_space = spaces.Dict({
            "task_description": spaces.Text(max_length=5000),
            "goal": spaces.Text(max_length=500),
            "feedback": spaces.Text(max_length=5000),
            "step_count": spaces.Box(low=0, high=self.config.max_steps, shape=(), dtype=int),
            "episode_complete": spaces.Discrete(2),
            "last_reward": spaces.Box(low=-10.0, high=10.0, shape=(), dtype=float),
        })

        self.reset()

    def _load_tasks(self):
        if self.config.data_mode == "random":
            self.tasks = load_tasks(self.config)
        elif self.config.data_mode == "single":
            task = get_task_by_id(self.config.data_source)
            self.tasks = [task]
        elif self.config.data_mode == "list":
            self.tasks = []
            for task_id in self.config.data_source:
                try:
                    task = get_task_by_id(task_id)
                    self.tasks.append(task)
                except ValueError:
                    if self.config.verbose:
                        print(f"Warning: Task '{task_id}' not found, skipping")

            if not self.tasks:
                raise ValueError("No valid tasks found in data_source list")

        random.seed(123)
        random.shuffle(self.tasks)
        if self.config.verbose:
            print(f"Loaded {len(self.tasks)} tasks in {self.config.data_mode} mode")

    def _get_next_task(self):
        if self.config.data_mode == "random":
            return random.choice(self.tasks)
        if self.config.data_mode == "single":
            return self.tasks[0]
        task = self.tasks[self.current_task_index]
        self.current_task_index = (self.current_task_index + 1) % len(self.tasks)
        return task

    def reset(self, *, task_index=None, seed=None, options=None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.episode_complete = False
        self.step_count = 0
        self.total_reward = 0.0
        self.reward_by_dimension = {}
        self.recommendations = {}

        self.action_history = []
        self.conversation_history = []
        self.state_list = {"search_times": 0}

        if task_index is not None:
            self.current_task_index = task_index
            self.current_task = self.tasks[task_index]
        else:
            self.current_task = self._get_next_task()

        self._initialize_answer_state()

        observation = {
            "task_description": self.current_task.get("scenario", ""),
            "goal": "Perform search actions and review results.",
            "feedback": self.current_task.get("initial_desc", "Let's start the conversation!"),
            "step_count": self.step_count,
            "episode_complete": self.episode_complete,
            "last_reward": 0.0,
        }

        info = {
            "task_id": self.current_task.get("id", ""),
            "action_history": self.action_history.copy(),
            "conversation_history": self.conversation_history.copy(),
            "total_reward": self.total_reward,
            "reward_by_dimension": dict(self.reward_by_dimension),
            "recommendations": self.recommendations,
        }

        if self.config.verbose:
            print("🎯 New Lite Episode Started")
            print(f"Task ID: {info['task_id']}")
            print(f"Scenario: {observation['task_description'][:100]}...")

        return observation, info

    def close(self):
        pass

    def _initialize_answer_state(self) -> None:
        self.state_list["remaining_best_options"] = []
        self.state_list["remaining_correct_options"] = []
        self.state_list["choice_initials"] = []

        preferences_data = self.current_task.get("preferences", {})
        for dimension in self.current_task.get("dimensions", []):
            self.reward_by_dimension[dimension] = 0.0
            if dimension in preferences_data:
                dim_data = preferences_data[dimension]
                if "correct_ids" in dim_data:
                    self.state_list["remaining_correct_options"].extend(dim_data["correct_ids"])
                if "best_id" in dim_data:
                    self.state_list["remaining_best_options"].append(dim_data["best_id"])

    def _handle_search(self, action: str) -> Tuple[str, float] | None:
        try:
            parsed = parse_action(action)
        except ActionParseError as exc:
            feedback = str(exc)
            return feedback, 0.0
        if parsed is None:
            return None

        try:
            dimension, options, unknown_args = perform_search(self.current_task, parsed)
            feedback = build_search_feedback(dimension, options, parsed.args, unknown_args)
            self.conversation_history.append({"role": "agent", "content": action})
            self.conversation_history.append(
                {"role": "database", "content": feedback.split("\n")[0] + " ... (skip detailed results here) ..."}
            )
            # return feedback, self.config.search_correct_reward
            return feedback, 0.0
        except ActionParseError as exc:
            feedback = f"Invalid search action format: {exc}"
        except Exception as exc:
            if "Simulate a system error" in str(exc):
                print("[TravelGymLite - Search] Normally simulate a system error")
            else:
                print(f"[TravelGymLite - Search] {exc}; By default will return error message")
            feedback = "Currently the searching backend is experiencing some issues. Please try again later."

        self.conversation_history.append({"role": "agent", "content": action})
        self.conversation_history.append({"role": "database", "content": feedback})
        return feedback, 0.0

    def _handle_answer(self, action: str) -> Tuple[str, float]:
        match = re.match(r"^answer\((.*)\)$", action.strip(), re.IGNORECASE)
        if not match:
            return "Answer format is wrong. Use answer(ID).", 0.0

        raw = match.group(1).strip()
        if not raw:
            return "No answer ID provided.", 0.0

        answer_ids = [item.strip() for item in raw.split(",") if item.strip()]
        if len(answer_ids) > 1:
            return "You have chosen multiple options. Please choose only one option at a time.", 0.0

        answer_id = answer_ids[0]
        if (answer_id.startswith('"') and answer_id.endswith('"')) or (
            answer_id.startswith("'") and answer_id.endswith("'")
        ):
            answer_id = answer_id[1:-1].strip()
        if not re.match(r"^[ACFHR]\d+$", answer_id):
            return f"Invalid option ID format detected for '{answer_id}'. Expected format: H1, F12, C4, etc.", 0.0

        id_initial = answer_id[0]
        initial_aspect_map = {"F": "flight", "A": "apartment", "C": "rental_car", "H": "hotel", "R": "restaurant"}
        aspect = initial_aspect_map.get(id_initial, "option")
        if self.config.one_choice_per_aspect and id_initial in self.state_list["choice_initials"]:
            return f"You have already booked a {aspect}, you cannot change it now.", 0.0

        reward = 0.0
        best_found = False
        correct_found = False
        wrong_found = False

        if answer_id in self.state_list["remaining_best_options"]:
            reward += self.config.choice_best_reward
            best_found = True
            self.state_list["remaining_best_options"].remove(answer_id)
            if answer_id in self.state_list["remaining_correct_options"]:
                self.state_list["remaining_correct_options"].remove(answer_id)
        elif answer_id in self.state_list["remaining_correct_options"]:
            reward += self.config.choice_correct_reward
            correct_found = True
            self.state_list["remaining_correct_options"].remove(answer_id)
        else:
            reward -= self.config.wrong_choice_penalty
            wrong_found = True

        if id_initial not in self.state_list["choice_initials"]:
            self.state_list["choice_initials"].append(id_initial)

        reward = max(reward, 0.0)
        reward = min(reward, 1.0)

        self.reward_by_dimension[aspect] = reward
        assert aspect not in self.recommendations, f"Aspect {aspect} already in recommendations"
        self.recommendations[aspect] = answer_id
        feedback = f"You have successfully booked the {aspect} {answer_id}."

        self.conversation_history.append({"role": "agent", "content": action})
        self.conversation_history.append({"role": "database", "content": feedback})
        return feedback, reward

    def step(self, action_input: str) -> Tuple[Dict[str, Any], float, bool, bool, Dict[str, Any]]:
        if self.episode_complete:
            raise ValueError("Episode is complete. Call reset() to start a new episode.")

        self.step_count += 1
        action = str(action_input).strip()
        self.action_history.append(action)

        action_lower = action.lower()
        if action_lower == "finish()" or action_lower.startswith("[finish]"):
            self.episode_complete = True
            reward = 0.0
            observation = {
                "task_description": self.current_task.get("scenario", ""),
                "goal": "Perform search actions and review results.",
                "feedback": "Session ended.",
                "step_count": self.step_count,
                "episode_complete": self.episode_complete,
                "last_reward": reward,
            }
            info = {
                "task_id": self.current_task.get("id", ""),
                "action_history": self.action_history.copy(),
                "conversation_history": self.conversation_history.copy(),
                "total_reward": self.total_reward,
                "reward_by_dimension": dict(self.reward_by_dimension),
                "recommendations": self.recommendations,
            }
            return observation, reward, True, False, info

        if action_lower.startswith("answer("):
            response, reward = self._handle_answer(action)
        elif action_lower.startswith("search_"):
            search_result = self._handle_search(action)
            if search_result is not None:
                response, reward = search_result
            else:
                response = "Unsupported action. Use search_<dimension>(...), answer(...), or finish()."
                reward = 0.0
        else:
            response = "Unsupported action. Use search_<dimension>(...), answer(...), or finish()."
            reward = 0.0

        reward = reward * self.config.reward_scale - self.config.step_penalty
        if self.config.normalize_rewards:
            reward = max(0.0, min(1.0, reward))
        self.total_reward += reward

        truncated = self.step_count >= self.config.max_steps
        if truncated:
            self.episode_complete = True

        observation = {
            "task_description": self.current_task.get("scenario", ""),
            "goal": "Perform search actions and review results.",
            "feedback": response,
            "step_count": self.step_count,
            "episode_complete": self.episode_complete,
            "last_reward": reward,
        }

        info = {
            "task_id": self.current_task.get("id", ""),
            "action_history": self.action_history.copy(),
            "conversation_history": self.conversation_history.copy(),
            "total_reward": self.total_reward,
            "reward_by_dimension": dict(self.reward_by_dimension),
            "recommendations": self.recommendations,
        }

        return observation, reward, False, truncated, info
