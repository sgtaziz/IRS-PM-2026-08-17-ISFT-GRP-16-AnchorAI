from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from anchorai import catalog
from anchorai.api.deps import SessionDep, require_role
from anchorai.catalog import CatalogView, Constraints, OfferIn, StaffIn, StaffRow
from anchorai.db.models import OfferCatalog, User

router = APIRouter()
Admin = Annotated[User, Depends(require_role("admin"))]


@router.get("", response_model=CatalogView)
def view(session: SessionDep):
    return catalog.view(session)


@router.post("/offers", response_model=OfferIn, status_code=201)
def create_offer(offer: OfferIn, session: SessionDep, user: Admin):
    if session.get(OfferCatalog, offer.offer_id) is not None:
        raise HTTPException(409, f"Offer {offer.offer_id} already exists")
    return catalog.upsert_offer(session, user, offer)


@router.put("/offers/{offer_id}", response_model=OfferIn)
def update_offer(offer_id: str, offer: OfferIn, session: SessionDep, user: Admin):
    if offer.offer_id != offer_id:
        raise HTTPException(400, "offer_id in the path and body must match")
    return catalog.upsert_offer(session, user, offer)


@router.delete("/offers/{offer_id}", status_code=204)
def delete_offer(offer_id: str, session: SessionDep, user: Admin):
    if not catalog.delete_offer(session, user, offer_id):
        raise HTTPException(404, f"Unknown offer {offer_id}")


@router.put("/staff/{user_id}", response_model=StaffRow)
def update_staff(user_id: int, change: StaffIn, session: SessionDep, user: Admin):
    row = catalog.update_staff(session, user, user_id, change)
    if row is None:
        raise HTTPException(404, f"No staff user {user_id}")
    return row


@router.put("/constraints", response_model=Constraints)
def update_constraints(change: Constraints, session: SessionDep, user: Admin):
    return catalog.update_constraints(session, user, change)
