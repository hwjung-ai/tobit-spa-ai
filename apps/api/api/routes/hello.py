from fastapi import APIRouter

from schemas.common import ResponseEnvelope

router = APIRouter()


@router.get("/hello")
def hello():
    return ResponseEnvelope.success(data={"hello": "tobit-spa-ai"})
