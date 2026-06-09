from __future__ import annotations

import hashlib
import json
import re
import secrets
import threading
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sock import Sock
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from werkzeug.security import check_password_hash, generate_password_hash

from db import (
    add_friendship_pair,
    consume_verification_code,
    count_verification_codes_since,
    create_friend_request,
    create_message,
    create_user,
    create_verification_code,
    get_friend_request_by_id,
    get_conversation_by_id,
    get_conversation_summary,
    get_friend_profile,
    get_friendship,
    get_latest_verification_code,
    get_or_create_conversation,
    get_pending_friend_request_between,
    get_user_by_id,
    get_user_by_phone,
    increment_verification_code_attempts,
    initialize_database,
    list_conversations_for_user,
    list_discover_users,
    list_friend_ids,
    list_friend_requests_for_user,
    list_messages_for_conversation,
    remove_friendship_pair,
    update_friend_remark,
    update_friend_request_status,
    update_user_avatar,
    update_user_password_hash,
    update_user_profile,
)


TOKEN_SECRET = "chat-companion-local-secret"
TOKEN_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
PHONE_RULES = {
    "+86": {
        "country": "中国",
        "pattern": re.compile(r"^1[3-9]\d{9}$"),
        "label": "中国大陆手机号",
    }
}
VERIFICATION_CODE_PURPOSE_REGISTER = "register"
VERIFICATION_CODE_EXPIRE_MINUTES = 5
VERIFICATION_CODE_RESEND_SECONDS = 60
VERIFICATION_CODE_DAILY_LIMIT = 10
VERIFICATION_CODE_MAX_ATTEMPTS = 5
FRIEND_REQUEST_MESSAGE_MAX_LENGTH = 50
CHAT_MESSAGE_MAX_LENGTH = 1000
SOCKET_LOCK = threading.Lock()
ACTIVE_SOCKETS: dict[str, set[Any]] = {}
APP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = APP_ROOT.parent
PUBLIC_AVATAR_DIR = PROJECT_ROOT / "public" / "uploads" / "avatars"
ALLOWED_AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_AVATAR_SIZE = 3 * 1024 * 1024

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_AVATAR_SIZE
app.config["SECRET_KEY"] = TOKEN_SECRET
CORS(
    app,
    resources={r"/api/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}},
    supports_credentials=False,
)
sock = Sock(app)
token_serializer = URLSafeTimedSerializer(TOKEN_SECRET, salt="auth-token")


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def now_iso() -> str:
    return now().isoformat()


def validate_text_length(value: str, max_length: int, field_name: str) -> str | None:
    if len(value) > max_length:
        return f"{field_name}不能超过 {max_length} 个字符。"
    return None


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def is_legacy_password_hash(password_hash: str) -> bool:
    return password_hash.startswith("sha256:")


def verify_password(user: dict[str, Any], password: str) -> bool:
    stored_password_hash = user["password_hash"]

    if is_legacy_password_hash(stored_password_hash):
        legacy_hash = f"sha256:{hashlib.sha256(password.encode('utf-8')).hexdigest()}"
        if legacy_hash != stored_password_hash:
            return False

        update_user_password_hash(user["id"], hash_password(password), now_iso())
        return True

    return check_password_hash(stored_password_hash, password)


def create_token(user: dict[str, Any]) -> str:
    return token_serializer.dumps({"userId": user["id"], "issuedAt": now_iso()})


def parse_token(token: str) -> dict[str, Any] | None:
    if not token:
        return None

    try:
        payload = token_serializer.loads(token, max_age=TOKEN_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        return None

    return payload if isinstance(payload, dict) else None


def success(data: Any = None, message: str = "OK", status_code: int = 200):
    return jsonify({"code": "SUCCESS", "message": message, "data": data}), status_code


def fail(message: str, status_code: int = 400):
    return jsonify({"code": "ERROR", "errMsg": message}), status_code


def request_payload() -> dict[str, Any]:
    if request.content_type and "multipart/form-data" in request.content_type:
        return request.form.to_dict()
    return request.get_json(silent=True) or {}


def validate_region_code(region_code: str) -> bool:
    return region_code in PHONE_RULES


def validate_phone(region_code: str, telephone: str) -> bool:
    rule = PHONE_RULES.get(region_code)
    return bool(rule and rule["pattern"].fullmatch(telephone))


def validate_password(password: str) -> bool:
    return bool(re.fullmatch(r"^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d\W_]{8,32}$", password))


def hash_verification_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def mask_phone(region_code: str, telephone: str) -> str:
    if len(telephone) < 7:
        return f"{region_code} {telephone}"
    return f"{region_code} {telephone[:3]}****{telephone[-4:]}"


def verification_code_debug_value() -> str | None:
    return app.config.get("LAST_VERIFICATION_CODE")


def create_verification_code_value() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def require_auth(handler: Callable[..., Any]):
    def wrapped(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.removeprefix("Bearer ").strip()
        payload = parse_token(token)
        if not payload:
            return fail("登录状态已失效，请重新登录。", 401)

        user = get_user_by_id(payload["userId"])
        if not user:
            return fail("用户不存在。", 401)

        return handler(user, *args, **kwargs)

    wrapped.__name__ = handler.__name__
    return wrapped


def sanitize_user(
    user: dict[str, Any], viewer_id: str | None = None, friend_ids: list[str] | None = None
) -> dict[str, Any]:
    normalized_friend_ids = friend_ids or []
    return {
        "id": user["id"],
        "regionCode": user.get("region_code", "+86"),
        "userName": user["user_name"],
        "telephone": user["telephone"],
        "avatarUrl": user.get("avatar_url") or "/images/avatar-default.png",
        "bio": user.get("bio", ""),
        "phoneVerified": bool(user.get("phone_verified_at")),
        "isFriend": bool(viewer_id and user["id"] in normalized_friend_ids),
    }


def normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        **profile,
        "avatarUrl": profile.get("avatarUrl") or "/images/avatar-default.png",
        "regionCode": profile.get("regionCode") or "+86",
    }


def normalize_conversation(conversation: dict[str, Any] | None) -> dict[str, Any] | None:
    if conversation is None:
        return None
    return {
        **conversation,
        "avatarUrl": conversation.get("avatarUrl") or "/images/avatar-default.png",
    }


def normalize_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        **message,
        "senderAvatar": message.get("senderAvatar") or "/images/avatar-default.png",
    }


def normalize_friend_request(friend_request: dict[str, Any], viewer_id: str) -> dict[str, Any]:
    is_incoming = friend_request["receiver_id"] == viewer_id
    counterpart_prefix = "requester" if is_incoming else "receiver"

    return {
        "id": friend_request["id"],
        "direction": "incoming" if is_incoming else "outgoing",
        "status": friend_request["status"],
        "message": friend_request.get("message", ""),
        "createdAt": friend_request["created_at"],
        "updatedAt": friend_request["updated_at"],
        "respondedAt": friend_request.get("responded_at"),
        "user": {
            "id": friend_request[f"{counterpart_prefix}_id"],
            "userName": friend_request[f"{counterpart_prefix}_name"],
            "telephone": friend_request[f"{counterpart_prefix}_telephone"],
            "avatarUrl": friend_request.get(f"{counterpart_prefix}_avatar_url")
            or "/images/avatar-default.png",
            "bio": friend_request.get(f"{counterpart_prefix}_bio", "") or "",
        },
    }


def build_friend_request_payload(
    friend_request: dict[str, Any], viewer_id: str, event_type: str
) -> dict[str, Any]:
    return {
        "type": event_type,
        "request": normalize_friend_request(friend_request, viewer_id),
    }


def build_friend_removed_payload(friend_id: str) -> dict[str, Any]:
    return {
        "type": "friend.removed",
        "friendId": friend_id,
    }


def normalize_friend_profile(friend_profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": friend_profile["id"],
        "regionCode": friend_profile.get("region_code", "+86"),
        "userName": friend_profile["user_name"],
        "telephone": friend_profile["telephone"],
        "avatarUrl": friend_profile.get("avatar_url") or "/images/avatar-default.png",
        "bio": friend_profile.get("bio", "") or "",
        "remark": friend_profile.get("remark", "") or "",
        "friendedAt": friend_profile.get("friended_at"),
    }


def build_friend_profile_updated_payload(
    user_id: str, friend_id: str
) -> dict[str, Any] | None:
    profile = get_friend_profile(user_id, friend_id)
    if not profile:
        return None
    return {
        "type": "friend.profile.updated",
        "friend": normalize_friend_profile(profile),
    }


def register_socket(user_id: str, connection: Any) -> None:
    with SOCKET_LOCK:
        ACTIVE_SOCKETS.setdefault(user_id, set()).add(connection)


def unregister_socket(user_id: str, connection: Any) -> None:
    with SOCKET_LOCK:
        sockets = ACTIVE_SOCKETS.get(user_id)
        if not sockets:
            return
        sockets.discard(connection)
        if not sockets:
            ACTIVE_SOCKETS.pop(user_id, None)


def send_socket_payload(connection: Any, payload: dict[str, Any]) -> None:
    connection.send(json.dumps(payload, ensure_ascii=False))


def broadcast_user_payload(user_id: str, payload: dict[str, Any]) -> None:
    with SOCKET_LOCK:
        connections = list(ACTIVE_SOCKETS.get(user_id, set()))

    stale_connections = []
    for connection in connections:
        try:
            send_socket_payload(connection, payload)
        except Exception:
            stale_connections.append(connection)

    for connection in stale_connections:
        unregister_socket(user_id, connection)


def build_conversation_created_payloads(
    conversation: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for participant_id in conversation["participant_ids"]:
        payloads[participant_id] = {
            "type": "conversation.created",
            "conversation": normalize_conversation(
                get_conversation_summary(conversation["id"], participant_id)
            ),
        }
    return payloads


def build_message_created_payloads(
    conversation: dict[str, Any], message: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    normalized_message = normalize_message(message)
    payloads: dict[str, dict[str, Any]] = {}
    for participant_id in conversation["participant_ids"]:
        payloads[participant_id] = {
            "type": "message.created",
            "conversation": normalize_conversation(
                get_conversation_summary(conversation["id"], participant_id)
            ),
            "message": normalized_message,
        }
    return payloads


def broadcast_profile_change(user_id: str) -> dict[str, Any]:
    user = get_user_by_id(user_id)
    profile = normalize_profile(sanitize_user(user, user_id, list_friend_ids(user_id)))

    broadcast_user_payload(user_id, {"type": "profile.updated", "profile": profile})

    for conversation in list_conversations_for_user(user_id):
        participant_id = conversation["participantId"]
        reverse_summary = normalize_conversation(
            get_conversation_summary(conversation["id"], participant_id)
        )
        if reverse_summary:
            broadcast_user_payload(
                participant_id,
                {
                    "type": "conversation.updated",
                    "conversation": reverse_summary,
                },
            )
            broadcast_user_payload(
                participant_id,
                {"type": "profile.updated", "profile": profile},
            )

    return profile


def save_avatar_file(uploaded_file: Any, user_id: str) -> str:
    suffix = Path(uploaded_file.filename or "").suffix.lower()
    if suffix not in ALLOWED_AVATAR_EXTENSIONS:
        raise ValueError("头像仅支持 JPG、JPEG、PNG、WEBP、GIF 格式。")

    PUBLIC_AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    file_name = f"{user_id}-{uuid.uuid4().hex[:12]}{suffix}"
    save_path = PUBLIC_AVATAR_DIR / file_name
    uploaded_file.save(save_path)
    return f"/uploads/avatars/{file_name}"


def validate_verification_code(
    *,
    region_code: str,
    telephone: str,
    purpose: str,
    submitted_code: str,
) -> tuple[bool, str]:
    latest_code = get_latest_verification_code(region_code, telephone, purpose)
    if latest_code is None:
        return False, "请先获取验证码。"

    if latest_code.get("consumed_at"):
        return False, "验证码已使用，请重新获取。"

    if latest_code.get("attempts", 0) >= VERIFICATION_CODE_MAX_ATTEMPTS:
        return False, "验证码尝试次数过多，请重新获取。"

    expires_at = parse_iso(latest_code.get("expires_at"))
    if expires_at is None or expires_at < now():
        return False, "验证码已过期，请重新获取。"

    increment_verification_code_attempts(latest_code["id"])
    if latest_code["code_hash"] != hash_verification_code(submitted_code):
        return False, "验证码错误。"

    consume_verification_code(latest_code["id"], now_iso())
    return True, ""


@app.get("/api/health")
def health_check():
    return success({"status": "ok"})


@app.get("/api/meta/phone-regions")
def phone_regions():
    return success(
        [
            {
                "code": code,
                "country": rule["country"],
                "label": rule["label"],
            }
            for code, rule in PHONE_RULES.items()
        ]
    )


@app.post("/api/auth/send-code")
def send_code():
    payload = request_payload()
    region_code = str(payload.get("regionCode", "+86")).strip()
    telephone = str(payload.get("telephone", "")).strip()
    purpose = str(payload.get("purpose", VERIFICATION_CODE_PURPOSE_REGISTER)).strip()

    if purpose != VERIFICATION_CODE_PURPOSE_REGISTER:
        return fail("暂不支持该验证码用途。")
    if not validate_region_code(region_code):
        return fail("暂不支持该地区号。")
    if not validate_phone(region_code, telephone):
        return fail("请输入有效的手机号。")
    if get_user_by_phone(region_code, telephone):
        return fail("该手机号已注册。")

    latest_code = get_latest_verification_code(region_code, telephone, purpose)
    if latest_code:
        created_at = parse_iso(latest_code.get("created_at"))
        if created_at and now() - created_at < timedelta(seconds=VERIFICATION_CODE_RESEND_SECONDS):
            return fail("验证码发送过于频繁，请稍后再试。", 429)

    daily_count = count_verification_codes_since(
        region_code,
        telephone,
        purpose,
        (now() - timedelta(days=1)).isoformat(),
    )
    if daily_count >= VERIFICATION_CODE_DAILY_LIMIT:
        return fail("今日验证码发送次数已达上限。", 429)

    code = create_verification_code_value()
    created_at = now()
    expires_at = created_at + timedelta(minutes=VERIFICATION_CODE_EXPIRE_MINUTES)

    create_verification_code(
        verification_code_id=f"vc-{uuid.uuid4().hex[:10]}",
        region_code=region_code,
        telephone=telephone,
        purpose=purpose,
        code_hash=hash_verification_code(code),
        created_at=created_at.isoformat(),
        expires_at=expires_at.isoformat(),
    )
    app.config["LAST_VERIFICATION_CODE"] = code

    response_data = {
        "regionCode": region_code,
        "telephone": telephone,
        "maskedPhone": mask_phone(region_code, telephone),
        "purpose": purpose,
        "expiresIn": VERIFICATION_CODE_EXPIRE_MINUTES * 60,
    }
    if app.debug or app.testing:
        response_data["debugCode"] = code

    return success(
        response_data,
        "验证码已发送。",
    )


@sock.route("/ws")
def websocket_handler(ws):
    token = request.args.get("token", "").strip()
    payload = parse_token(token)

    if not payload:
        send_socket_payload(ws, {"type": "error", "message": "登录状态已失效，请重新登录。"})
        ws.close()
        return

    user = get_user_by_id(payload["userId"])
    if not user:
        send_socket_payload(ws, {"type": "error", "message": "用户不存在。"})
        ws.close()
        return

    register_socket(user["id"], ws)
    send_socket_payload(
        ws,
        {"type": "connected", "userId": user["id"], "connectedAt": now_iso()},
    )

    try:
        while True:
            raw_message = ws.receive()
            if raw_message is None:
                break

            try:
                message = json.loads(raw_message)
            except Exception:
                continue

            if message.get("type") == "ping":
                send_socket_payload(ws, {"type": "pong", "at": now_iso()})
    finally:
        unregister_socket(user["id"], ws)


@app.post("/api/auth/register")
def register():
    payload = request_payload()
    region_code = str(payload.get("regionCode", "+86")).strip()
    telephone = str(payload.get("telephone", "")).strip()
    verification_code = str(payload.get("verificationCode", "")).strip()
    password = str(payload.get("password", "")).strip()
    user_name = str(payload.get("userName", "")).strip()
    bio = str(payload.get("bio", "")).strip()
    uploaded_file = request.files.get("avatar")

    if not validate_region_code(region_code):
        return fail("暂不支持该地区号。")
    if not validate_phone(region_code, telephone):
        return fail("请输入有效的手机号。")
    if len(user_name) < 2 or len(user_name) > 20:
        return fail("昵称长度需在 2 到 20 个字符之间。")
    if not validate_password(password):
        return fail("密码需为 8 到 32 位，并同时包含字母和数字。")
    if len(bio) > 120:
        return fail("个人简介不能超过 120 个字符。")
    if not re.fullmatch(r"\d{6}", verification_code):
        return fail("请输入 6 位验证码。")
    if get_user_by_phone(region_code, telephone):
        return fail("该手机号已注册。")

    verified, error_message = validate_verification_code(
        region_code=region_code,
        telephone=telephone,
        purpose=VERIFICATION_CODE_PURPOSE_REGISTER,
        submitted_code=verification_code,
    )
    if not verified:
        return fail(error_message)

    user_id = f"user-{uuid.uuid4().hex[:8]}"
    avatar_url = "/images/avatar-default.png"
    if uploaded_file and uploaded_file.filename:
        try:
            avatar_url = save_avatar_file(uploaded_file, user_id)
        except ValueError as error:
            return fail(str(error))

    created_at = now_iso()
    created_user = create_user(
        user_id=user_id,
        region_code=region_code,
        telephone=telephone,
        password_hash=hash_password(password),
        user_name=user_name,
        avatar_url=avatar_url,
        bio=bio,
        created_at=created_at,
        phone_verified_at=created_at,
    )
    return success(normalize_profile(sanitize_user(created_user)), "注册成功。", 201)


@app.post("/api/auth/login")
def login():
    payload = request_payload()
    region_code = str(payload.get("regionCode", "+86")).strip()
    telephone = str(payload.get("telephone", "")).strip()
    password = str(payload.get("password", "")).strip()

    if not validate_region_code(region_code):
        return fail("暂不支持该地区号。", 401)
    if not validate_phone(region_code, telephone) or not password:
        return fail("手机号或密码错误。", 401)

    user = get_user_by_phone(region_code, telephone)
    if not user or not verify_password(user, password):
        return fail("手机号或密码错误。", 401)

    refreshed_user = get_user_by_id(user["id"])
    return success(
        {
            "token": create_token(refreshed_user),
            "profile": normalize_profile(
                sanitize_user(
                    refreshed_user,
                    refreshed_user["id"],
                    list_friend_ids(refreshed_user["id"]),
                )
            ),
        }
    )


@app.get("/api/auth/me")
@require_auth
def me(user: dict[str, Any]):
    return success(
        normalize_profile(sanitize_user(user, user["id"], list_friend_ids(user["id"])))
    )


@app.get("/api/profile")
@require_auth
def get_profile(user: dict[str, Any]):
    return success(
        normalize_profile(sanitize_user(user, user["id"], list_friend_ids(user["id"])))
    )


@app.post("/api/profile/avatar")
@require_auth
def upload_profile_avatar(user: dict[str, Any]):
    uploaded_file = request.files.get("avatar")
    if uploaded_file is None or not uploaded_file.filename:
        return fail("请选择头像文件。")

    try:
        avatar_url = save_avatar_file(uploaded_file, user["id"])
    except ValueError as error:
        return fail(str(error))

    update_user_avatar(user["id"], avatar_url, updated_at=now_iso())
    profile = broadcast_profile_change(user["id"])
    return success(profile, "头像已更新。")


@app.put("/api/profile")
@require_auth
def update_profile(user: dict[str, Any]):
    payload = request_payload()
    user_name = str(payload.get("userName", "")).strip()
    avatar_url = (
        str(payload.get("avatarUrl", "")).strip()
        or user.get("avatar_url")
        or "/images/avatar-default.png"
    )
    bio = str(payload.get("bio", "")).strip()

    if len(user_name) < 2 or len(user_name) > 20:
        return fail("昵称长度需在 2 到 20 个字符之间。")
    if len(bio) > 120:
        return fail("个人简介不能超过 120 个字符。")

    update_user_profile(user["id"], user_name, avatar_url, bio, updated_at=now_iso())
    profile = broadcast_profile_change(user["id"])
    return success(profile, "资料已更新。")


@app.get("/api/conversations")
@require_auth
def list_conversations(user: dict[str, Any]):
    return success(
        [normalize_conversation(item) for item in list_conversations_for_user(user["id"])]
    )


@app.get("/api/conversations/<conversation_id>/messages")
@require_auth
def list_messages(user: dict[str, Any], conversation_id: str):
    conversation = get_conversation_by_id(conversation_id)
    if not conversation or user["id"] not in conversation["participant_ids"]:
        return fail("会话不存在。", 404)

    return success(
        [normalize_message(item) for item in list_messages_for_conversation(conversation_id)]
    )


@app.post("/api/conversations/<conversation_id>/messages")
@require_auth
def send_message(user: dict[str, Any], conversation_id: str):
    payload = request_payload()
    content = str(payload.get("content", "")).strip()
    if not content:
        return fail("消息内容不能为空。")
    length_error = validate_text_length(content, CHAT_MESSAGE_MAX_LENGTH, "单条消息")
    if length_error:
        return fail(length_error)

    conversation = get_conversation_by_id(conversation_id)
    if not conversation or user["id"] not in conversation["participant_ids"]:
        return fail("会话不存在。", 404)
    summary = get_conversation_summary(conversation_id, user["id"])
    if not summary:
        return fail("你们当前不是好友，无法继续发送消息。", 403)

    message = create_message(conversation_id, user["id"], content, created_at=now_iso())
    refreshed_conversation = get_conversation_by_id(conversation_id)

    response_data = {
        "conversation": normalize_conversation(summary),
        "message": normalize_message(message),
    }

    for participant_id, participant_payload in build_message_created_payloads(
        refreshed_conversation, message
    ).items():
        broadcast_user_payload(participant_id, participant_payload)

    return success(response_data, "发送成功。", 201)


@app.get("/api/users/discover")
@require_auth
def discover_users(user: dict[str, Any]):
    keyword = request.args.get("q", "").strip()
    return success(
        [normalize_profile(item) for item in list_discover_users(user["id"], keyword)]
    )


@app.get("/api/friend-requests")
@require_auth
def list_friend_requests(user: dict[str, Any]):
    return success(
        [
            normalize_friend_request(item, user["id"])
            for item in list_friend_requests_for_user(user["id"])
        ]
    )


@app.get("/api/friends/<friend_id>")
@require_auth
def get_friend_detail(user: dict[str, Any], friend_id: str):
    friend_profile = get_friend_profile(user["id"], friend_id)
    if not friend_profile:
        return fail("好友不存在。", 404)
    return success(normalize_friend_profile(friend_profile))


@app.put("/api/friends/<friend_id>/remark")
@require_auth
def save_friend_remark(user: dict[str, Any], friend_id: str):
    remark = str(request_payload().get("remark", "")).strip()
    if len(remark) > 20:
        return fail("备注不能超过 20 个字符。")

    friendship = get_friendship(user["id"], friend_id)
    if not friendship:
        return fail("好友不存在。", 404)

    update_friend_remark(user["id"], friend_id, remark)
    profile = get_friend_profile(user["id"], friend_id)
    payload = build_friend_profile_updated_payload(user["id"], friend_id)
    if payload:
        broadcast_user_payload(user["id"], payload)

    return success(normalize_friend_profile(profile), "备注已更新。")


@app.post("/api/friends")
@require_auth
def add_friend(user: dict[str, Any]):
    payload = request_payload()
    friend_id = str(payload.get("friendId", "")).strip()
    message = str(payload.get("message", "")).strip()
    if not friend_id:
        return fail("friendId 不能为空。")
    length_error = validate_text_length(
        message, FRIEND_REQUEST_MESSAGE_MAX_LENGTH, "验证消息"
    )
    if length_error:
        return fail(length_error)

    friend = get_user_by_id(friend_id)
    if not friend:
        return fail("联系人不存在。", 404)
    if friend["id"] == user["id"]:
        return fail("不能添加自己。")
    if friend["id"] in list_friend_ids(user["id"]):
        return fail("你们已经是好友了。")

    if get_pending_friend_request_between(user["id"], friend["id"]):
        return fail("好友申请已发送，请等待对方处理。")
    if get_pending_friend_request_between(friend["id"], user["id"]):
        return fail("对方已向你发起申请，请先处理对方的申请。")

    created_at = now_iso()
    friend_request = create_friend_request(
        request_id=f"fr-{uuid.uuid4().hex[:10]}",
        requester_id=user["id"],
        receiver_id=friend["id"],
        message=message,
        created_at=created_at,
    )
    requester_payload = build_friend_request_payload(
        friend_request, user["id"], "friend.request.created"
    )
    receiver_payload = build_friend_request_payload(
        friend_request, friend["id"], "friend.request.created"
    )

    broadcast_user_payload(user["id"], requester_payload)
    broadcast_user_payload(friend["id"], receiver_payload)

    return success(
        normalize_friend_request(friend_request, user["id"]),
        "好友申请已发送。",
    )


@app.delete("/api/friends/<friend_id>")
@require_auth
def remove_friend(user: dict[str, Any], friend_id: str):
    friend_id = str(friend_id).strip()
    if not friend_id:
        return fail("friendId 不能为空。")

    friend = get_user_by_id(friend_id)
    if not friend:
        return fail("联系人不存在。", 404)
    if friend["id"] not in list_friend_ids(user["id"]):
        return fail("对方当前不是你的好友。", 400)

    remove_friendship_pair(user["id"], friend["id"])
    broadcast_user_payload(user["id"], build_friend_removed_payload(friend["id"]))
    broadcast_user_payload(friend["id"], build_friend_removed_payload(user["id"]))

    return success({"friendId": friend["id"]}, "好友已删除。")


@app.post("/api/friend-requests/<request_id>/accept")
@require_auth
def accept_friend_request(user: dict[str, Any], request_id: str):
    friend_request = get_friend_request_by_id(request_id)
    if not friend_request:
        return fail("好友申请不存在。", 404)
    if friend_request["receiver_id"] != user["id"]:
        return fail("无权处理该好友申请。", 403)
    if friend_request["status"] != "pending":
        return fail("该好友申请已处理。")

    responded_at = now_iso()
    updated_request = update_friend_request_status(
        request_id, "accepted", responded_at, responded_at
    )

    requester_id = updated_request["requester_id"]
    receiver_id = updated_request["receiver_id"]
    add_friendship_pair(requester_id, receiver_id, created_at=responded_at)
    conversation = get_or_create_conversation(
        requester_id, receiver_id, created_at=responded_at
    )

    broadcast_user_payload(
        requester_id,
        build_friend_request_payload(updated_request, requester_id, "friend.request.updated"),
    )
    broadcast_user_payload(
        receiver_id,
        build_friend_request_payload(updated_request, receiver_id, "friend.request.updated"),
    )

    for participant_id, participant_payload in build_conversation_created_payloads(
        conversation
    ).items():
        broadcast_user_payload(participant_id, participant_payload)

    return success(
        {
            "request": normalize_friend_request(updated_request, user["id"]),
            "conversationId": conversation["id"],
            "conversation": normalize_conversation(
                get_conversation_summary(conversation["id"], user["id"])
            ),
        },
        "已同意好友申请。",
    )


@app.post("/api/friend-requests/<request_id>/reject")
@require_auth
def reject_friend_request(user: dict[str, Any], request_id: str):
    friend_request = get_friend_request_by_id(request_id)
    if not friend_request:
        return fail("好友申请不存在。", 404)
    if friend_request["receiver_id"] != user["id"]:
        return fail("无权处理该好友申请。", 403)
    if friend_request["status"] != "pending":
        return fail("该好友申请已处理。")

    responded_at = now_iso()
    updated_request = update_friend_request_status(
        request_id, "rejected", responded_at, responded_at
    )

    broadcast_user_payload(
        updated_request["requester_id"],
        build_friend_request_payload(
            updated_request,
            updated_request["requester_id"],
            "friend.request.updated",
        ),
    )
    broadcast_user_payload(
        updated_request["receiver_id"],
        build_friend_request_payload(
            updated_request,
            updated_request["receiver_id"],
            "friend.request.updated",
        ),
    )

    return success(
        normalize_friend_request(updated_request, user["id"]),
        "已拒绝好友申请。",
    )


initialize_database()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8083, debug=True, use_reloader=False)
