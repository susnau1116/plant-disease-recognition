"""留言接口：未匹配问题提交、留言列表查询与回复。"""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from .. import database as db
from .. import schemas

router = APIRouter(tags=["留言"])

STATUS_PENDING = "pending"
STATUS_REPLIED = "replied"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _get(message_id: int) -> dict:
    row = db.query_one("SELECT * FROM messages WHERE id = ?", (message_id,))
    if row is None:
        raise HTTPException(status_code=404, detail="留言不存在")
    return row


@router.post("/messages", response_model=schemas.MessageItem, summary="提交留言")
def create_message(payload: schemas.MessageCreate):
    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="问题不能为空")
    contact = (payload.contact or "").strip() or None
    created_at = _now()
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO messages (question, contact, status, created_at) VALUES (?, ?, ?, ?)",
            (question, contact, STATUS_PENDING, created_at),
        )
        message_id = cur.lastrowid
    return _get(message_id)


@router.get("/messages", response_model=schemas.MessageListResponse, summary="留言列表")
def list_messages(
    status: Optional[str] = Query(None, pattern="^(pending|replied)$", description="按状态筛选"),
    ids: Optional[str] = Query(None, description="按留言 ID 筛选，逗号分隔"),
    limit: int = Query(50, ge=1, le=200, description="返回条数上限"),
):
    where = []
    params = []
    if status:
        where.append("status = ?")
        params.append(status)
    if ids:
        try:
            id_list = [int(i) for i in ids.split(",") if i.strip()]
        except ValueError:
            raise HTTPException(status_code=422, detail="ids 参数格式错误")
        if not id_list:
            return {"total": 0, "items": []}
        where.append(f"id IN ({','.join('?' for _ in id_list)})")
        params.extend(id_list)

    clause = f" WHERE {' AND '.join(where)}" if where else ""
    total = db.query_one(f"SELECT COUNT(*) AS n FROM messages{clause}", tuple(params))["n"]
    items = db.query(
        f"SELECT * FROM messages{clause} ORDER BY id DESC LIMIT ?",
        tuple(params) + (limit,),
    )
    return {"total": total, "items": items}


@router.get("/messages/{message_id}", response_model=schemas.MessageItem, summary="留言详情")
def get_message(message_id: int):
    return _get(message_id)


@router.post(
    "/messages/{message_id}/reply",
    response_model=schemas.MessageItem,
    summary="回复留言",
)
def reply_message(message_id: int, payload: schemas.MessageReply):
    reply = payload.reply.strip()
    if not reply:
        raise HTTPException(status_code=422, detail="回复内容不能为空")
    _get(message_id)
    with db.connect() as conn:
        conn.execute(
            "UPDATE messages SET reply = ?, status = ?, replied_at = ? WHERE id = ?",
            (reply, STATUS_REPLIED, _now(), message_id),
        )
    return _get(message_id)
