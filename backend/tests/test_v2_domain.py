import pytest
from datetime import datetime, timezone
import uuid
from sqlalchemy.exc import IntegrityError
from app.models.conversation import (
    Conversation, ConversationShare, ConversationAccessRequest, Message,
    LifecycleState, RequestStatus, SenderType
)
from app.models.user import User

def create_test_user(db_session, email=None):
    if email is None:
        email = f"test_{uuid.uuid4()}@test.com"
    user = User(id=str(uuid.uuid4()), email=email, username=email.split("@")[0], hashed_password="pwd")
    db_session.add(user)
    db_session.commit()
    return user

def test_conversation_branching_and_snapshot(db_session):
    user = create_test_user(db_session)
    
    # 1. Create canonical conversation
    canonical = Conversation(title="Canonical", owner_id=user.id)
    db_session.add(canonical)
    db_session.commit()
    
    # 2. Add some messages to canonical
    msg1 = Message(conversation_id=canonical.id, content="First", sender_type=SenderType.user)
    msg2 = Message(conversation_id=canonical.id, content="Second", sender_type=SenderType.user)
    db_session.add_all([msg1, msg2])
    db_session.commit()
    
    # Validate sequence_id was generated automatically by Postgres!
    assert msg1.sequence_id is not None
    assert msg2.sequence_id is not None
    assert msg2.sequence_id > msg1.sequence_id
    
    # 3. Create branch conversation
    branch = Conversation(
        title="Branch",
        parent_conversation_id=canonical.id,
        snapshot_sequence_id=msg1.sequence_id,
        owner_id=user.id
    )
    db_session.add(branch)
    db_session.commit()
    
    assert branch.id is not None
    assert branch.lifecycle_state == LifecycleState.active

def test_access_request_constraints(db_session):
    owner = create_test_user(db_session)
    requester = create_test_user(db_session)
    
    conv = Conversation(title="Shared", owner_id=owner.id)
    db_session.add(conv)
    db_session.commit()
    
    share = ConversationShare(
        conversation_id=conv.id,
        created_by=owner.id,
        token_hash=str(uuid.uuid4())
    )
    db_session.add(share)
    db_session.commit()
    
    branch = Conversation(
        title="Requester Branch",
        parent_conversation_id=conv.id,
        owner_id=requester.id
    )
    db_session.add(branch)
    db_session.commit()
    
    req1 = ConversationAccessRequest(
        share_id=share.id,
        requester_id=requester.id,
        branch_conversation_id=branch.id,
        status=RequestStatus.pending
    )
    db_session.add(req1)
    db_session.commit()
    
    # A user cannot have multiple pending requests for the same share
    req2 = ConversationAccessRequest(
        share_id=share.id,
        requester_id=requester.id,
        branch_conversation_id=branch.id,
        status=RequestStatus.pending
    )
    db_session.add(req2)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()

    # But they CAN have an accepted request and a pending request (or rejected, etc)
    # Let's change the first one to accepted and then we should be able to create another pending
    req1.status = RequestStatus.accepted
    db_session.commit()
    
    req3 = ConversationAccessRequest(
        share_id=share.id,
        requester_id=requester.id,
        branch_conversation_id=branch.id,
        status=RequestStatus.pending
    )
    db_session.add(req3)
    db_session.commit() # Should succeed

def test_branch_message_history(db_session):
    from app.crud.crud_conversation import get_messages, create_branch
    user = create_test_user(db_session)
    
    canonical = Conversation(title="Canonical for Messages", owner_id=user.id)
    db_session.add(canonical)
    db_session.commit()
    
    msg1 = Message(conversation_id=canonical.id, content="First in canonical", sender_type=SenderType.user)
    msg2 = Message(conversation_id=canonical.id, content="Second in canonical", sender_type=SenderType.user)
    db_session.add_all([msg1, msg2])
    db_session.commit()
    
    branch = create_branch(db_session, canonical.id, user.id, "Branch")
    
    msg3 = Message(conversation_id=canonical.id, content="Third in canonical", sender_type=SenderType.user)
    db_session.add(msg3)
    db_session.commit()
    
    msg4 = Message(conversation_id=branch.id, content="First in branch", sender_type=SenderType.user)
    db_session.add(msg4)
    db_session.commit()
    
    msgs, total = get_messages(db_session, branch.id, limit=100)
    
    assert total == 3
    assert len(msgs) == 3
    assert msgs[0].content == "First in canonical"
    assert msgs[1].content == "Second in canonical"
    assert msgs[2].content == "First in branch"
