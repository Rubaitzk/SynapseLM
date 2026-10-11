import re

def update():
    with open("frontend/src/pages/ConversationView.tsx", "r", encoding="utf-8") as f:
        content = f.read()

    old_reconnect = """        reconnectTimer = setTimeout(() => {
           fetchPresence();
           fetchMessages();
           connectWs();
        }, 3000);"""
        
    new_reconnect = """        reconnectTimer = setTimeout(() => {
           fetchPresence();
           fetchMessages();
           fetchParticipants();
           fetchRequests();
           connectWs();
        }, 3000);"""

    content = content.replace(old_reconnect, new_reconnect)
    
    with open("frontend/src/pages/ConversationView.tsx", "w", encoding="utf-8") as f:
        f.write(content)

if __name__ == "__main__":
    update()
