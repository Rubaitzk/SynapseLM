from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import crud_request
from app.schemas.request import AccessRequestResponse

router = APIRouter()

from app.core.realtime import manager

@router.post("/{request_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_request(request_id: str, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_user)):
    req = crud_request.get_request(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this request")
        
    try:
        crud_request.cancel_request(db, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    # Broadcast to parent conversation
    await manager.broadcast_to_conversation(req.share.conversation_id, {
        "event": "request.cancelled",
        "conversation_id": req.share.conversation_id,
        "request_id": req.id,
        "status": "cancelled"
    })
    
    return None
