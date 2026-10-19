from fastapi import APIRouter

from anchorai.api.deps import CurrentUser, SessionDep
from anchorai.optimisation import contacts

router = APIRouter()


@router.get("/mine")
def my_contacts(session: SessionDep, user: CurrentUser) -> list[dict]:
    return contacts.my_contacts(session, user)
