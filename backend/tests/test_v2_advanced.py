import threading
import time
from sqlalchemy.exc import IntegrityError
import pytest

from app.crud.crud_conversation import create_message, create_branch, delete_conversation
from app.schemas.conversation import MessageCreate
from app.models.conversation import Conversation, SenderType, LifecycleState, Message
from tests.conftest import TestingSessionLocal
from tests.test_v2_domain import create_test_user

def test_concurrent_message_and_branch_snapshots():
    # We will use two separate DB sessions to simulate concurrent requests
    db_main = TestingSessionLocal()
    db_worker1 = TestingSessionLocal()
    db_worker2 = TestingSessionLocal()
    
    try:
        user = create_test_user(db_main)
        
        # Create canonical
        canonical = Conversation(title="Concurrent Base", owner_id=user.id)
        db_main.add(canonical)
        db_main.commit()
        db_main.refresh(canonical)
        conv_id = canonical.id
        
        # We want to pause Worker 1's transaction AFTER it acquires the FOR UPDATE lock,
        # but BEFORE it commits, to prove Worker 2 blocks and waits for it.
        import time
        from unittest.mock import patch
        
        worker1_started = threading.Event()
        worker2_finished = threading.Event()
        
        original_add = db_worker1.add
        
        def delayed_add(instance):
            original_add(instance)
            if isinstance(instance, Message):
                worker1_started.set()
                # Hold the lock for 1 second, simulating a slow transaction
                time.sleep(1)

        def worker1_task():
            try:
                with patch.object(db_worker1, 'add', side_effect=delayed_add):
                    create_message(db_worker1, conv_id, MessageCreate(content="Msg 1"), user.id, SenderType.user)
            except Exception as e:
                print("Worker 1 failed:", e)
                db_worker1.rollback()

        branch_result = []
        def worker2_task():
            try:
                # Wait until Worker 1 has definitely acquired the lock and is sleeping
                worker1_started.wait(timeout=2)
                # This should block until Worker 1 commits!
                branch = create_branch(db_worker2, conv_id, user.id, "Concurrent Branch")
                branch_result.append(branch.snapshot_sequence_id)
                worker2_finished.set()
            except Exception as e:
                print("Worker 2 failed:", e)
                db_worker2.rollback()

        t1 = threading.Thread(target=worker1_task)
        t2 = threading.Thread(target=worker2_task)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        assert worker2_finished.is_set(), "Worker 2 did not finish successfully"
        
        messages = db_main.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.sequence_id.asc()).all()
        assert len(messages) == 1
        
        assert len(branch_result) == 1
        # Because Worker 2 was blocked until Worker 1 committed, Worker 2 MUST see Worker 1's message in the snapshot!
        assert branch_result[0] == messages[0].sequence_id

    finally:
        db_main.close()
        db_worker1.close()
        db_worker2.close()

def test_nested_branch_invariant(db_session):
    user = create_test_user(db_session)
    canonical = Conversation(title="Base", owner_id=user.id)
    db_session.add(canonical)
    db_session.commit()
    
    branch1 = create_branch(db_session, canonical.id, user.id, "Branch 1")
    assert branch1.parent_conversation_id == canonical.id
    
    # Try to branch off branch1
    with pytest.raises(ValueError, match="single-level branching invariant violated"):
        create_branch(db_session, branch1.id, user.id, "Nested Branch")

def test_parent_deletion_cascades_to_branches(db_session):
    user = create_test_user(db_session)
    canonical = Conversation(title="To Delete", owner_id=user.id)
    db_session.add(canonical)
    db_session.commit()
    
    branch = create_branch(db_session, canonical.id, user.id, "Branch to be deleted")
    
    branch_id = branch.id
    
    # Delete parent
    delete_conversation(db_session, canonical.id)
    
    # Verify branch is gone
    check_branch = db_session.query(Conversation).filter(Conversation.id == branch_id).first()
    assert check_branch is None
