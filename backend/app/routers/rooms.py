import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Room, AuditLog, User
from ..schemas import RoomCreate, RoomUpdate, RoomResponse
from .auth import get_current_user

router = APIRouter(prefix="/api/rooms", tags=["rooms"])

def room_to_response(r: Room) -> dict:
    return {
        "id": r.id,
        "name": r.name,
        "building": r.building,
        "capacity": r.capacity,
        "is_computer_lab": r.is_computer_lab,
        "is_common": r.is_common,
        "available_hours": json.loads(r.available_hours or "[]"),
        "unavailable_hours": json.loads(r.unavailable_hours or "[]"),
        "notes": r.notes
    }

@router.get("", response_model=List[RoomResponse])
def list_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    rooms = db.query(Room).all()
    return [room_to_response(r) for r in rooms]

@router.post("", response_model=RoomResponse)
def create_room(
    req: RoomCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    room = Room(
        name=req.name,
        building=req.building,
        capacity=req.capacity,
        is_computer_lab=req.is_computer_lab,
        is_common=req.is_common,
        available_hours=json.dumps(req.available_hours),
        unavailable_hours=json.dumps(req.unavailable_hours),
        notes=req.notes
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"강의실 추가 ({room.building} {room.name})"
    )
    db.add(log)
    db.commit()

    return room_to_response(room)

@router.put("/{room_id}", response_model=RoomResponse)
def update_room(
    room_id: int,
    req: RoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="강의실을 찾을 수 없습니다.")

    room.name = req.name
    room.building = req.building
    room.capacity = req.capacity
    room.is_computer_lab = req.is_computer_lab
    room.is_common = req.is_common
    room.available_hours = json.dumps(req.available_hours)
    room.unavailable_hours = json.dumps(req.unavailable_hours)
    room.notes = req.notes

    db.commit()
    db.refresh(room)

    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"강의실 정보 수정 ({room.name})"
    )
    db.add(log)
    db.commit()

    return room_to_response(room)

@router.delete("/{room_id}", response_model=dict)
def delete_room(
    room_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="강의실을 찾을 수 없습니다.")

    name = room.name
    db.delete(room)
    db.commit()

    log = AuditLog(
        username=current_user.username,
        category="UPDATE",
        message=f"강의실 삭제 ({name})"
    )
    db.add(log)
    db.commit()

    return {"message": f"{name} 강의실이 삭제되었습니다."}
