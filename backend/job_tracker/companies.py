from dataclasses import dataclass
from typing import Literal

Platform = Literal["greenhouse"]


@dataclass(frozen=True)
class Company:
    platform: Platform
    board_id: str


STARTER_COMPANIES = [
    Company(platform="greenhouse", board_id="anthropic"),
]
