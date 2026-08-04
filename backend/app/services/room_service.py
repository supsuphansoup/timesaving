from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.room import Room
from app.schemas.room import RoomCreate, RoomUpdate


def list_rooms(db: Session) -> list[Room]:
    return db.query(Room).all()


def get_room(db: Session, room_id: int) -> Room:
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="해당 강의실을 찾을 수 없습니다.")
    return room


def create_room(db: Session, data: RoomCreate) -> Room:
    existing = db.query(Room).filter(Room.room_name == data.room_name).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail={"error_code": "ER-08", "message": "중복된 데이터가 존재합니다."},
        )
    room = Room(**data.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


def update_room(db: Session, room_id: int, data: RoomUpdate) -> Room:
    room = get_room(db, room_id)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(room, field, value)
    db.commit()
    db.refresh(room)
    return room


def delete_room(db: Session, room_id: int) -> None:
    room = get_room(db, room_id)
    db.delete(room)
    db.commit()
