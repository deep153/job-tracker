from typing import Annotated

from fastapi import Depends, Request

from job_tracker.container import Services


def _services(request: Request) -> Services:
    services: Services = request.app.state.services
    return services


ServicesDep = Annotated[Services, Depends(_services)]
