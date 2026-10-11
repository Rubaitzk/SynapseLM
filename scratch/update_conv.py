import sys

file_path = 'backend/app/api/conversations.py'
with open(file_path, 'r') as f:
    content = f.read()

target1 = """@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conv_in: ConversationCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    if conv_in.team_id:
        # Verify user is in the team
        membership = crud_team.get_team_membership(db, team_id=conv_in.team_id, user_id=current_user.id)
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized to create conversations in this team")
    
    return crud_conversation.create_conversation(db, conv_in=conv_in, creator_id=current_user.id)"""

repl1 = """@router.post("/", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    conv_in: ConversationCreate,
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user),
):
    if conv_in.team_id:
        # Verify user is in the team
        membership = crud_team.get_team_membership(db, team_id=conv_in.team_id, user_id=current_user.id)
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized to create conversations in this team")
    
    conv = crud_conversation.create_conversation(db, conv_in=conv_in, creator_id=current_user.id)
    
    # Validate provider configuration synchronously
    from app.services.llm.orchestrator import get_provider
    get_provider(conv)
    
    return conv"""

target2 = """    # 2. Trigger AI orchestrator in background
    from app.services.llm.orchestrator import generate_assistant_response
    background_tasks.add_task(generate_assistant_response, db, conversation_id)
    
    return user_msg"""

repl2 = """    # 1.6 Synchronously validate provider before sending to background
    from app.services.llm.orchestrator import get_provider
    get_provider(conv)

    # 2. Trigger AI orchestrator in background
    from app.services.llm.orchestrator import generate_assistant_response
    background_tasks.add_task(generate_assistant_response, db, conversation_id)
    
    return user_msg"""

if target1 in content:
    content = content.replace(target1, repl1)
    print("Replaced target1")
else:
    print("Target1 not found")

if target2 in content:
    content = content.replace(target2, repl2)
    print("Replaced target2")
else:
    print("Target2 not found")

with open(file_path, 'w') as f:
    f.write(content)
