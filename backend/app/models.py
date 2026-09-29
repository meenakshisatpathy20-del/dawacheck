"""Core tables (playbook section 11). Arrays are stored as JSON so the same
schema runs on PostgreSQL (docker compose) and SQLite (tests, laptop demo)."""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class ActiveIngredient(Base):
    __tablename__ = "active_ingredients"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    synonyms: Mapped[list] = mapped_column(JSON, default=list)
    chem_class: Mapped[str | None] = mapped_column(String(120))
    kind: Mapped[str | None] = mapped_column(String(30))  # insecticide / fungicide / herbicide
    irac_frac_group: Mapped[str | None] = mapped_column(String(20))
    moa_scheme: Mapped[str | None] = mapped_column(String(10))  # IRAC / FRAC / HRAC
    toxicity_colour: Mapped[str | None] = mapped_column(String(10))
    banned: Mapped[bool] = mapped_column(Boolean, default=False)
    restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    ban_note: Mapped[str | None] = mapped_column(Text)
    banned_from: Mapped[date | None] = mapped_column(Date)  # effective date of a ban added by an admin
    antidote_text: Mapped[str | None] = mapped_column(Text)
    first_aid_text: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)

    formulations: Mapped[list["Formulation"]] = relationship(back_populates="active_ingredient")


class Formulation(Base):
    __tablename__ = "formulations"
    id: Mapped[int] = mapped_column(primary_key=True)
    active_ingredient_id: Mapped[int] = mapped_column(ForeignKey("active_ingredients.id"), index=True)
    strength_pct: Mapped[float] = mapped_column(Float)
    type: Mapped[str] = mapped_column(String(10))  # EC, SL, WP, SC, GR, WG ...
    registered: Mapped[bool] = mapped_column(Boolean, default=True)
    source_file: Mapped[str | None] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)

    active_ingredient: Mapped[ActiveIngredient] = relationship(back_populates="formulations")
    claims: Mapped[list["LabelClaim"]] = relationship(back_populates="formulation")

    @property
    def label(self) -> str:
        pct = f"{self.strength_pct:g}"
        return f"{self.active_ingredient.name} {pct} {self.type}"


class LabelClaim(Base):
    __tablename__ = "label_claims"
    id: Mapped[int] = mapped_column(primary_key=True)
    formulation_id: Mapped[int] = mapped_column(ForeignKey("formulations.id"), index=True)
    crop: Mapped[str] = mapped_column(String(60), index=True)
    pest: Mapped[str] = mapped_column(String(120), index=True)
    dose_ai_g_ha_min: Mapped[float | None] = mapped_column(Float)
    dose_ai_g_ha_max: Mapped[float | None] = mapped_column(Float)
    dose_form_ha_min: Mapped[float | None] = mapped_column(Float)
    dose_form_ha_max: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(10), default="ml")  # ml or g of formulation
    water_l_ha: Mapped[float | None] = mapped_column(Float)
    phi_days: Mapped[int | None] = mapped_column(Integer)
    source_file: Mapped[str | None] = mapped_column(Text)
    page: Mapped[int | None] = mapped_column(Integer)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)  # hand-checked against the PDF page

    formulation: Mapped[Formulation] = relationship(back_populates="claims")


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str] = mapped_column(String(120), index=True)
    company: Mapped[str | None] = mapped_column(String(160))
    formulation_id: Mapped[int] = mapped_column(ForeignKey("formulations.id"), index=True)
    reg_no: Mapped[str | None] = mapped_column(String(60), index=True)
    pack_sizes: Mapped[list] = mapped_column(JSON, default=list)
    toxicity_colour: Mapped[str | None] = mapped_column(String(10))  # overrides the a.i. default
    mrp: Mapped[dict] = mapped_column(JSON, default=dict)  # {"100 ml": 250}
    label_image_url: Mapped[str | None] = mapped_column(Text)
    qr_id: Mapped[str | None] = mapped_column(String(120), index=True)

    formulation: Mapped[Formulation] = relationship()


class StateCropBan(Base):
    __tablename__ = "state_crop_bans"
    id: Mapped[int] = mapped_column(primary_key=True)
    state: Mapped[str] = mapped_column(String(60), index=True)
    crop: Mapped[str] = mapped_column(String(60), index=True)
    active_ingredient_id: Mapped[int] = mapped_column(ForeignKey("active_ingredients.id"))
    effective_from: Mapped[date | None] = mapped_column(Date)
    source_url: Mapped[str | None] = mapped_column(Text)

    active_ingredient: Mapped[ActiveIngredient] = relationship()


class ExportFlag(Base):
    __tablename__ = "export_flags"
    id: Mapped[int] = mapped_column(primary_key=True)
    crop: Mapped[str] = mapped_column(String(60), index=True)
    market: Mapped[str] = mapped_column(String(20))
    active_ingredient_id: Mapped[int] = mapped_column(ForeignKey("active_ingredients.id"))
    note: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text)

    active_ingredient: Mapped[ActiveIngredient] = relationship()


class Scan(Base):
    __tablename__ = "scans"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    batch: Mapped[str | None] = mapped_column(String(60), index=True)
    mfg_date: Mapped[date | None] = mapped_column(Date)
    exp_date: Mapped[date | None] = mapped_column(Date)
    qr_payload_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    image_hash: Mapped[str | None] = mapped_column(String(64))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    district: Mapped[str | None] = mapped_column(String(80), index=True)
    shop: Mapped[str | None] = mapped_column(String(160))
    crop: Mapped[str | None] = mapped_column(String(60))
    pest: Mapped[str | None] = mapped_column(String(120))
    extracted: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    verdict: Mapped[str | None] = mapped_column(String(10))
    fired_rules: Mapped[list] = mapped_column(JSON, default=list)


class SprayLog(Base):
    __tablename__ = "spray_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    plot_id: Mapped[str] = mapped_column(String(60), index=True)
    crop: Mapped[str] = mapped_column(String(60))
    state: Mapped[str | None] = mapped_column(String(60))
    pest: Mapped[str | None] = mapped_column(String(120))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    spray_date: Mapped[date] = mapped_column(Date)
    area_acre: Mapped[float | None] = mapped_column(Float)
    tanks: Mapped[int | None] = mapped_column(Integer)
    safe_harvest_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product: Mapped[Product] = relationship()


class BatchSignal(Base):
    __tablename__ = "batch_signals"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    batch: Mapped[str | None] = mapped_column(String(60), index=True)
    signal_type: Mapped[str] = mapped_column(String(40))  # date_conflict / cloned_qr / not_in_registry / farmer_report
    count: Mapped[int] = mapped_column(Integer, default=1)
    districts: Mapped[list] = mapped_column(JSON, default=list)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    score: Mapped[float] = mapped_column(Float, default=0)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)


class Price(Base):
    __tablename__ = "prices"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    pack_size: Mapped[str] = mapped_column(String(30))
    price: Mapped[float] = mapped_column(Float)
    district: Mapped[str | None] = mapped_column(String(80))
    seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(10), default="label")  # bill / label


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("scans.id"))
    reason: Mapped[str] = mapped_column(Text)
    photo_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProductSubmission(Base):
    """A farmer adds a product that is 'not in our catalogue yet'; an admin reviews the photo."""
    __tablename__ = "product_submissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    brand: Mapped[str] = mapped_column(String(120))
    active_ingredient: Mapped[str | None] = mapped_column(String(120))
    strength_pct: Mapped[float | None] = mapped_column(Float)
    formulation: Mapped[str | None] = mapped_column(String(10))
    reg_no: Mapped[str | None] = mapped_column(String(60))
    company: Mapped[str | None] = mapped_column(String(160))
    toxicity_colour: Mapped[str | None] = mapped_column(String(10))
    photo_url: Mapped[str | None] = mapped_column(Text)
    user_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / approved / rejected
    review_note: Mapped[str | None] = mapped_column(Text)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class BillCheck(Base):
    """One bill checked (for the 'money saved per farmer' impact metric)."""
    __tablename__ = "bill_checks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    district: Mapped[str | None] = mapped_column(String(80))
    total: Mapped[float] = mapped_column(Float, default=0)
    saving: Mapped[float] = mapped_column(Float, default=0)
    not_ok: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PassportView(Base):
    """A trader or exporter opened an MRL Passport (proxy for 'consignments sold with a passport')."""
    __tablename__ = "passport_views"
    id: Mapped[int] = mapped_column(primary_key=True)
    plot_id: Mapped[str] = mapped_column(String(60), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
