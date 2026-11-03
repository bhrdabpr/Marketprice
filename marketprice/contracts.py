"""Dated, seller-reviewed rule bundles. Evidence is declared, not independently verified."""

import hashlib
import json
from datetime import date

from pydantic import Field

from .models import Profile, StrictModel


class SellerContract(StrictModel):
    seller_reference: str = Field(min_length=1, max_length=128)
    currency: str
    valid_from: date
    valid_until: date
    reviewed_on: date
    reviewed_by: str = Field(min_length=1)
    evidence_reference: str = Field(min_length=1)
    profile: Profile


def load_contract(content: bytes, *, as_of: date, currency: str):
    if len(content) > 65536:
        raise ValueError("Contract bundle exceeds 64 KiB")
    contract = SellerContract.model_validate(json.loads(content))
    if not contract.valid_from <= as_of <= contract.valid_until or contract.reviewed_on > as_of:
        raise ValueError("Contract is expired, not effective, or reviewed in the future")
    if contract.currency != currency:
        raise ValueError("Contract currency does not match this catalog")
    if contract.profile.effective_date != contract.valid_from.isoformat():
        raise ValueError("Profile effective date must match contract valid_from")
    return contract, hashlib.sha256(content).hexdigest()
