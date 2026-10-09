from pydantic import BaseModel


class CompanyUpdate(BaseModel):
    blocked: bool
