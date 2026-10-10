from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api import deps
from app.crud import crud_request
from app.schemas.request import AccessRequestResponse

router = APIRouter()

@router.post("/{request_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
def cancel_request(request_id: str, db: Session = Depends(deps.get_db), current_user = Depends(deps.get_current_user)):
    req = crud_request.get_request(db, request_id)
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
        
    if req.requester_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to cancel this request")
        
    try:
        crud_request.cancel_request(db, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return None
