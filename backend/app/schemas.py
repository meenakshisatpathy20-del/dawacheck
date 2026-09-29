from datetime import date

from pydantic import BaseModel, Field


class MixRequest(BaseModel):
    product_ids: list[int] = Field(min_length=2, max_length=4)
    lang: str = "en"


class DoseRequest(BaseModel):
    product_id: int
    crop: str
    pest: str | None = None
    area_acre: float = Field(gt=0, le=1000)
    tank_l: float = Field(default=15, gt=0, le=1000)
    lang: str = "en"


class SprayRequest(BaseModel):
    plot_id: str = Field(min_length=1, max_length=60)
    crop: str
    product_id: int
    spray_date: date
    state: str | None = None
    pest: str | None = None
    area_acre: float | None = None
    tanks: int | None = None
    planned_harvest: date | None = None
    user_id: str | None = None
    lang: str = "en"


class BillItem(BaseModel):
    product_name: str
    pack_size: str | None = None
    quantity: float | None = 1
    price: float | None = None


class ExplainRequest(BaseModel):
    fired: list[dict]
    lang: str = "en"
    product_id: int | None = None
    crop: str | None = None
    pest: str | None = None
