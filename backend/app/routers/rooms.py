from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.response import success_response
from app.schemas.room import RoomCreate, RoomOut, RoomUpdate
from app.services import room_service

router = APIRouter(prefix="/api/v1/rooms", tags=["강의실 관리"])


@router.get("")
def list_rooms(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    rooms = room_service.list_rooms(db)
    return success_response(data=[RoomOut.model_validate(r).model_dump() for r in rooms])


@router.post("")
def create_room(
    body: RoomCreate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    room = room_service.create_room(db, body)
    return success_response(data=RoomOut.model_validate(room).model_dump(), status_code=201)


@router.put("/{room_id}")
def update_room(
    room_id: int,
    body: RoomUpdate,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    room = room_service.update_room(db, room_id, body)
    return success_response(data=RoomOut.model_validate(room).model_dump())


@router.delete("/{room_id}")
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    room_service.delete_room(db, room_id)
    return success_response(message="강의실 정보가 삭제되었습니다.")
