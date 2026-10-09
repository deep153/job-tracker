from typing import Literal

Platform = Literal["greenhouse", "lever", "ashby"]

ALL_PLATFORMS: tuple[Platform, ...] = ("greenhouse", "lever", "ashby")

PLATFORM_NAMES: dict[Platform, str] = {
    "greenhouse": "Greenhouse",
    "lever": "Lever",
    "ashby": "Ashby",
}
