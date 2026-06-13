import os, datetime
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from bson import ObjectId
from groq import Groq
from dotenv import load_dotenv
from database import init_db, db

load_dotenv()
init_db()

app = FastAPI(title="AskFirst API (MongoDB)")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class ThreadCreate(BaseModel):
    name: str

class MessageCreate(BaseModel):
    content: str

def to_json(doc):
    # Formats MongoDB documents to make them JSON-serializable by converting ObjectId to string
    if doc:
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if "thread_id" in doc:
            doc["thread_id"] = str(doc["thread_id"])
    return doc

@app.post("/threads", status_code=status.HTTP_201_CREATED)
def create_thread(data: ThreadCreate):
    thread_doc = {"name": data.name, "created_at": datetime.datetime.utcnow()}
    result = db.threads.insert_one(thread_doc)
    thread_doc["id"] = str(result.inserted_id)
    thread_doc.pop("_id", None)
    return thread_doc

@app.get("/threads")
def list_threads():
    return [to_json(t) for t in db.threads.find()]

@app.get("/threads/{id}/messages")
def get_messages(id: str):
    if not ObjectId.is_valid(id) or not db.threads.find_one({"_id": ObjectId(id)}):
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = list(db.messages.find({"thread_id": ObjectId(id)}).sort("timestamp", 1))
    return [to_json(m) for m in messages]

@app.post("/threads/{id}/chat")
def chat(id: str, data: MessageCreate):
    if not ObjectId.is_valid(id) or not db.threads.find_one({"_id": ObjectId(id)}):
        raise HTTPException(status_code=404, detail="Thread not found")

    db.messages.insert_one({
        "thread_id": ObjectId(id), "role": "user", "content": data.content, "timestamp": datetime.datetime.utcnow()
    })

    # Universal Memory: Fetch last 2 messages from each OTHER thread
    summaries = []
    for ot in db.threads.find({"_id": {"$ne": ObjectId(id)}}):
        msgs = list(db.messages.find({"thread_id": ot["_id"]}).sort("timestamp", -1).limit(2))
        msgs.reverse()
        if msgs:
            msg_desc = ", ".join([f"{m['role']}: '{m['content']}'" for m in msgs])
            summaries.append(f"In thread '{ot['name']}', the discussion was: {msg_desc}")

    summaries_context = "; ".join(summaries) if summaries else "No previous discussions."
    system_prompt = f"You are a helpful assistant. From previous conversations, you know: [{summaries_context}]"

    messages_payload = [{"role": "system", "content": system_prompt}]
    for m in db.messages.find({"thread_id": ObjectId(id)}).sort("timestamp", 1):
        messages_payload.append({"role": m["role"], "content": m["content"]})

    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages_payload,
        )
        reply = completion.choices[0].message.content
    except Exception as e:
        print(f"ERROR calling Groq API: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    db.messages.insert_one({
        "thread_id": ObjectId(id), "role": "assistant", "content": reply, "timestamp": datetime.datetime.utcnow()
    })
    return {"user": data.content, "assistant": reply}

@app.delete("/threads/{id}")
def delete_thread(id: str):
    if not ObjectId.is_valid(id) or db.threads.delete_one({"_id": ObjectId(id)}).deleted_count == 0:
        raise HTTPException(status_code=404, detail="Thread not found")
    db.messages.delete_many({"thread_id": ObjectId(id)})
    return {"message": f"Thread {id} deleted successfully"}
