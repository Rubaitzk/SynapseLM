# Domain Model

## Core Entities
- **User**: Represents a registered user.
- **Team**: Represents a group of users.
- **TeamMembership**: Link between User and Team.
- **Invitation**: Invitation to join a team.
- **Conversation**: A shared space for messages.
- **ConversationParticipant**: Link between User and Conversation.
- **Message**: Represents a chat message (user, assistant, system).
- **AIConfiguration**: Settings for AI interaction in a conversation.

## Relationships
- User -> TeamMembership, Invitations, Conversations created, ConversationParticipant
- Team -> TeamMembership, Invitations, Conversations
- Conversation -> ConversationParticipant, Messages
- Message -> sender (user/assistant/system)
