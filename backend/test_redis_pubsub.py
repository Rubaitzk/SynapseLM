import asyncio
import json
import redis.asyncio as redis

async def main():
    r = redis.from_url("redis://localhost:6379/0", decode_responses=True)
    pubsub = r.pubsub()
    await pubsub.psubscribe("conversation:*")
    
    async def publisher():
        await asyncio.sleep(1)
        await r.publish("conversation:123", json.dumps({"event": "test"}))
        
    asyncio.create_task(publisher())
    
    async for message in pubsub.listen():
        print(message)
        if message["type"] == "pmessage":
            break

asyncio.run(main())
