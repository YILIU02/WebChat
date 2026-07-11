from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from werkzeug.security import generate_password_hash


APP_ROOT = Path(__file__).resolve().parent
DB_PATH = APP_ROOT / "data" / "chat.sqlite3"
JSON_SEED_PATH = APP_ROOT / "data" / "store.json"


DEFAULT_STORE = {
    "users": [
        {
            "id": "user-1001",
            "regionCode": "+86",
            "telephone": "13800000001",
            "passwordHash": "sha256:2363a2b08474dabea83780bc209c7d4289b066918b3d4bee2961457f9e490c3f",
            "userName": "Lin An",
            "avatarUrl": "/images/avatar-self.png",
            "bio": "Frontend engineer",
            "friends": ["user-1002", "user-1003"],
            "createdAt": "2026-06-01T09:00:00",
            "phoneVerifiedAt": "2026-06-01T09:00:00",
        },
        {
            "id": "user-1002",
            "regionCode": "+86",
            "telephone": "13800000002",
            "passwordHash": "sha256:2363a2b08474dabea83780bc209c7d4289b066918b3d4bee2961457f9e490c3f",
            "userName": "Zhou Yu",
            "avatarUrl": "/images/avatar1.jpg",
            "bio": "Backend engineer",
            "friends": ["user-1001", "user-1003"],
            "createdAt": "2026-06-01T09:05:00",
            "phoneVerifiedAt": "2026-06-01T09:05:00",
        },
        {
            "id": "user-1003",
            "regionCode": "+86",
            "telephone": "13800000003",
            "passwordHash": "sha256:2363a2b08474dabea83780bc209c7d4289b066918b3d4bee2961457f9e490c3f",
            "userName": "Shen Nian",
            "avatarUrl": "/images/avatar-default.png",
            "bio": "UI designer",
            "friends": ["user-1001", "user-1002"],
            "createdAt": "2026-06-01T09:10:00",
            "phoneVerifiedAt": "2026-06-01T09:10:00",
        },
    ],
    "conversations": [
        {
            "id": "conv-1001",
            "participantIds": ["user-1001", "user-1002"],
            "updatedAt": "2026-06-08T20:21:00",
            "messages": [
                {
                    "id": "msg-1001",
                    "senderId": "user-1002",
                    "content": "The Python API is ready. The frontend can call the REST endpoints.",
                    "createdAt": "2026-06-08T19:58:00",
                },
                {
                    "id": "msg-1002",
                    "senderId": "user-1001",
                    "content": "Received. I will align login, contacts, and chat state.",
                    "createdAt": "2026-06-08T20:21:00",
                },
            ],
        },
        {
            "id": "conv-1002",
            "participantIds": ["user-1001", "user-1003"],
            "updatedAt": "2026-06-09T08:15:00",
            "messages": [
                {
                    "id": "msg-1003",
                    "senderId": "user-1003",
                    "content": "The interface has been simplified further.",
                    "createdAt": "2026-06-09T08:15:00",
                }
            ],
        },
    ],
}


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


def looks_garbled(store: dict[str, Any]) -> bool:
    suspicious_tokens = ("閺", "濞", "闁", "鐠", "娑擃")

    def visit(value: Any) -> bool:
        if isinstance(value, str):
            return any(token in value for token in suspicious_tokens)
        if isinstance(value, dict):
            return any(visit(item) for item in value.values())
        if isinstance(value, list):
            return any(visit(item) for item in value)
        return False

    return visit(store)


def table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def ensure_user_schema(connection: sqlite3.Connection) -> None:
    columns = table_columns(connection, "users")

    if "region_code" not in columns:
        connection.execute(
            "ALTER TABLE users ADD COLUMN region_code TEXT NOT NULL DEFAULT '+86'"
        )

    if "phone_verified_at" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN phone_verified_at TEXT")
        connection.execute(
            """
            UPDATE users
            SET phone_verified_at = COALESCE(updated_at, created_at)
            WHERE phone_verified_at IS NULL
            """
        )

    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_region_phone
        ON users(region_code, telephone)
        """
    )


def ensure_verification_code_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS verification_codes (
            id TEXT PRIMARY KEY,
            region_code TEXT NOT NULL,
            telephone TEXT NOT NULL,
            purpose TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            consumed_at TEXT,
            attempts INTEGER NOT NULL DEFAULT 0
        );

        CREATE INDEX IF NOT EXISTS idx_verification_codes_phone_purpose
        ON verification_codes(region_code, telephone, purpose, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_verification_codes_expires_at
        ON verification_codes(expires_at);
        """
    )


def ensure_friend_request_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS friend_requests (
            id TEXT PRIMARY KEY,
            requester_id TEXT NOT NULL,
            receiver_id TEXT NOT NULL,
            message TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            responded_at TEXT,
            FOREIGN KEY (requester_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (receiver_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_friend_requests_requester
        ON friend_requests(requester_id, status, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_friend_requests_receiver
        ON friend_requests(receiver_id, status, created_at DESC);

        CREATE UNIQUE INDEX IF NOT EXISTS idx_friend_requests_pending_pair
        ON friend_requests(requester_id, receiver_id)
        WHERE status = 'pending';
        """
    )


def ensure_friendship_schema(connection: sqlite3.Connection) -> None:
    columns = table_columns(connection, "friendships")

    if "remark" not in columns:
        connection.execute("ALTER TABLE friendships ADD COLUMN remark TEXT NOT NULL DEFAULT ''")


def initialize_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    with get_connection() as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys = ON;

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                region_code TEXT NOT NULL DEFAULT '+86',
                telephone TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                user_name TEXT NOT NULL,
                avatar_url TEXT NOT NULL,
                bio TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                phone_verified_at TEXT
            );

            CREATE TABLE IF NOT EXISTS friendships (
                user_id TEXT NOT NULL,
                friend_id TEXT NOT NULL,
                remark TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                PRIMARY KEY (user_id, friend_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (friend_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversation_participants (
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                PRIMARY KEY (conversation_id, user_id),
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
                FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conversation_created
            ON messages(conversation_id, created_at);

            CREATE INDEX IF NOT EXISTS idx_conversation_participants_user
            ON conversation_participants(user_id);
            """
        )

        ensure_user_schema(connection)
        ensure_verification_code_schema(connection)
        ensure_friend_request_schema(connection)
        ensure_friendship_schema(connection)

        user_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_count == 0:
            if os.getenv("ENABLE_DEMO_SEED", "").strip().lower() not in {"1", "true", "yes", "on"}:
                return
            demo_password = os.getenv("DEMO_SEED_PASSWORD", "")
            if len(demo_password) < 12:
                raise RuntimeError("Set a DEMO_SEED_PASSWORD of at least 12 characters before enabling demo seed data")
            import_store(connection, load_seed_store(), demo_password)


def load_seed_store() -> dict[str, Any]:
    if JSON_SEED_PATH.exists():
        try:
            store = json.loads(JSON_SEED_PATH.read_text(encoding="utf-8"))
            if not looks_garbled(store):
                return store
        except Exception:
            pass
    return DEFAULT_STORE


def import_store(connection: sqlite3.Connection, store: dict[str, Any], demo_password: str | None = None) -> None:
    for raw_user in store.get("users", []):
        created_at = raw_user.get("createdAt") or "2026-06-01T00:00:00"
        phone_verified_at = raw_user.get("phoneVerifiedAt") or created_at
        connection.execute(
            """
            INSERT INTO users (
                id,
                region_code,
                telephone,
                password_hash,
                user_name,
                avatar_url,
                bio,
                created_at,
                updated_at,
                phone_verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raw_user["id"],
                raw_user.get("regionCode", "+86"),
                raw_user["telephone"],
                generate_password_hash(demo_password) if demo_password else raw_user["passwordHash"],
                raw_user["userName"],
                raw_user.get("avatarUrl") or "/images/avatar-default.png",
                raw_user.get("bio", ""),
                created_at,
                created_at,
                phone_verified_at,
            ),
        )

    for raw_user in store.get("users", []):
        for friend_id in raw_user.get("friends", []):
            connection.execute(
                """
                INSERT OR IGNORE INTO friendships (user_id, friend_id, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    raw_user["id"],
                    friend_id,
                    raw_user.get("createdAt") or "2026-06-01T00:00:00",
                ),
            )

    for raw_conversation in store.get("conversations", []):
        created_at = (
            raw_conversation.get("messages", [{}])[0].get("createdAt")
            if raw_conversation.get("messages")
            else raw_conversation.get("updatedAt") or "2026-06-01T00:00:00"
        )
        updated_at = raw_conversation.get("updatedAt") or created_at
        connection.execute(
            """
            INSERT INTO conversations (id, created_at, updated_at)
            VALUES (?, ?, ?)
            """,
            (raw_conversation["id"], created_at, updated_at),
        )

        for participant_id in raw_conversation.get("participantIds", []):
            connection.execute(
                """
                INSERT INTO conversation_participants (conversation_id, user_id)
                VALUES (?, ?)
                """,
                (raw_conversation["id"], participant_id),
            )

        for raw_message in raw_conversation.get("messages", []):
            connection.execute(
                """
                INSERT INTO messages (id, conversation_id, sender_id, content, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    raw_message["id"],
                    raw_conversation["id"],
                    raw_message["senderId"],
                    raw_message["content"],
                    raw_message["createdAt"],
                ),
            )


def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                region_code,
                telephone,
                password_hash,
                user_name,
                avatar_url,
                bio,
                created_at,
                updated_at,
                phone_verified_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()
    return row_to_dict(row)


def get_user_by_phone(region_code: str, telephone: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                region_code,
                telephone,
                password_hash,
                user_name,
                avatar_url,
                bio,
                created_at,
                updated_at,
                phone_verified_at
            FROM users
            WHERE region_code = ? AND telephone = ?
            """,
            (region_code, telephone),
        ).fetchone()
    return row_to_dict(row)


def create_user(
    user_id: str,
    region_code: str,
    telephone: str,
    password_hash: str,
    user_name: str,
    avatar_url: str,
    bio: str,
    created_at: str,
    phone_verified_at: str | None = None,
) -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO users (
                id,
                region_code,
                telephone,
                password_hash,
                user_name,
                avatar_url,
                bio,
                created_at,
                updated_at,
                phone_verified_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                region_code,
                telephone,
                password_hash,
                user_name,
                avatar_url,
                bio,
                created_at,
                created_at,
                phone_verified_at,
            ),
        )
    return get_user_by_id(user_id)


def update_user_profile(
    user_id: str, user_name: str, avatar_url: str, bio: str, updated_at: str
) -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET user_name = ?, avatar_url = ?, bio = ?, updated_at = ?
            WHERE id = ?
            """,
            (user_name, avatar_url, bio, updated_at, user_id),
        )
    return get_user_by_id(user_id)


def update_user_avatar(user_id: str, avatar_url: str, updated_at: str) -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET avatar_url = ?, updated_at = ?
            WHERE id = ?
            """,
            (avatar_url, updated_at, user_id),
        )
    return get_user_by_id(user_id)


def update_user_password_hash(
    user_id: str, password_hash: str, updated_at: str
) -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE users
            SET password_hash = ?, updated_at = ?
            WHERE id = ?
            """,
            (password_hash, updated_at, user_id),
        )
    return get_user_by_id(user_id)


def create_friend_request(
    *,
    request_id: str,
    requester_id: str,
    receiver_id: str,
    message: str,
    created_at: str,
) -> dict[str, Any] | None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO friend_requests (
                id, requester_id, receiver_id, message, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (request_id, requester_id, receiver_id, message, created_at, created_at),
        )
    return get_friend_request_by_id(request_id)


def get_friend_request_by_id(request_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                fr.id,
                fr.requester_id,
                fr.receiver_id,
                fr.message,
                fr.status,
                fr.created_at,
                fr.updated_at,
                fr.responded_at,
                requester.user_name AS requester_name,
                requester.avatar_url AS requester_avatar_url,
                requester.telephone AS requester_telephone,
                requester.bio AS requester_bio,
                receiver.user_name AS receiver_name,
                receiver.avatar_url AS receiver_avatar_url,
                receiver.telephone AS receiver_telephone,
                receiver.bio AS receiver_bio
            FROM friend_requests fr
            JOIN users requester ON requester.id = fr.requester_id
            JOIN users receiver ON receiver.id = fr.receiver_id
            WHERE fr.id = ?
            LIMIT 1
            """,
            (request_id,),
        ).fetchone()
    return row_to_dict(row)


def get_pending_friend_request_between(
    requester_id: str, receiver_id: str
) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                fr.id,
                fr.requester_id,
                fr.receiver_id,
                fr.message,
                fr.status,
                fr.created_at,
                fr.updated_at,
                fr.responded_at,
                requester.user_name AS requester_name,
                requester.avatar_url AS requester_avatar_url,
                requester.telephone AS requester_telephone,
                requester.bio AS requester_bio,
                receiver.user_name AS receiver_name,
                receiver.avatar_url AS receiver_avatar_url,
                receiver.telephone AS receiver_telephone,
                receiver.bio AS receiver_bio
            FROM friend_requests fr
            JOIN users requester ON requester.id = fr.requester_id
            JOIN users receiver ON receiver.id = fr.receiver_id
            WHERE fr.requester_id = ? AND fr.receiver_id = ? AND fr.status = 'pending'
            ORDER BY fr.created_at DESC, fr.id DESC
            LIMIT 1
            """,
            (requester_id, receiver_id),
        ).fetchone()
    return row_to_dict(row)


def list_friend_requests_for_user(user_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                fr.id,
                fr.requester_id,
                fr.receiver_id,
                fr.message,
                fr.status,
                fr.created_at,
                fr.updated_at,
                fr.responded_at,
                requester.user_name AS requester_name,
                requester.avatar_url AS requester_avatar_url,
                requester.telephone AS requester_telephone,
                requester.bio AS requester_bio,
                receiver.user_name AS receiver_name,
                receiver.avatar_url AS receiver_avatar_url,
                receiver.telephone AS receiver_telephone,
                receiver.bio AS receiver_bio
            FROM friend_requests fr
            JOIN users requester ON requester.id = fr.requester_id
            JOIN users receiver ON receiver.id = fr.receiver_id
            WHERE fr.requester_id = ? OR fr.receiver_id = ?
            ORDER BY fr.updated_at DESC, fr.created_at DESC, fr.id DESC
            """,
            (user_id, user_id),
        ).fetchall()
    return [dict(row) for row in rows]


def update_friend_request_status(
    request_id: str, status: str, updated_at: str, responded_at: str | None
) -> dict[str, Any] | None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE friend_requests
            SET status = ?, updated_at = ?, responded_at = ?
            WHERE id = ?
            """,
            (status, updated_at, responded_at, request_id),
        )
    return get_friend_request_by_id(request_id)


def create_verification_code(
    *,
    verification_code_id: str,
    region_code: str,
    telephone: str,
    purpose: str,
    code_hash: str,
    created_at: str,
    expires_at: str,
) -> dict[str, Any]:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO verification_codes (
                id, region_code, telephone, purpose, code_hash, created_at, expires_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                verification_code_id,
                region_code,
                telephone,
                purpose,
                code_hash,
                created_at,
                expires_at,
            ),
        )
    return get_verification_code_by_id(verification_code_id)


def get_verification_code_by_id(verification_code_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                region_code,
                telephone,
                purpose,
                code_hash,
                created_at,
                expires_at,
                consumed_at,
                attempts
            FROM verification_codes
            WHERE id = ?
            """,
            (verification_code_id,),
        ).fetchone()
    return row_to_dict(row)


def get_latest_verification_code(
    region_code: str, telephone: str, purpose: str
) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                region_code,
                telephone,
                purpose,
                code_hash,
                created_at,
                expires_at,
                consumed_at,
                attempts
            FROM verification_codes
            WHERE region_code = ? AND telephone = ? AND purpose = ?
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (region_code, telephone, purpose),
        ).fetchone()
    return row_to_dict(row)


def count_verification_codes_since(
    region_code: str, telephone: str, purpose: str, since_at: str
) -> int:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT COUNT(*) AS total
            FROM verification_codes
            WHERE region_code = ? AND telephone = ? AND purpose = ? AND created_at >= ?
            """,
            (region_code, telephone, purpose, since_at),
        ).fetchone()
    return int(row["total"])


def increment_verification_code_attempts(verification_code_id: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE verification_codes
            SET attempts = attempts + 1
            WHERE id = ?
            """,
            (verification_code_id,),
        )


def consume_verification_code(verification_code_id: str, consumed_at: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE verification_codes
            SET consumed_at = ?
            WHERE id = ?
            """,
            (consumed_at, verification_code_id),
        )


def list_friend_ids(user_id: str) -> list[str]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT friend_id
            FROM friendships
            WHERE user_id = ?
            ORDER BY friend_id
            """,
            (user_id,),
        ).fetchall()
    return [row["friend_id"] for row in rows]


def get_friendship(user_id: str, friend_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT user_id, friend_id, remark, created_at
            FROM friendships
            WHERE user_id = ? AND friend_id = ?
            LIMIT 1
            """,
            (user_id, friend_id),
        ).fetchone()
    return row_to_dict(row)


def add_friendship_pair(user_id: str, friend_id: str, created_at: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO friendships (user_id, friend_id, remark, created_at)
            VALUES (?, ?, '', ?)
            """,
            (user_id, friend_id, created_at),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO friendships (user_id, friend_id, remark, created_at)
            VALUES (?, ?, '', ?)
            """,
            (friend_id, user_id, created_at),
        )


def remove_friendship_pair(user_id: str, friend_id: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM friendships
            WHERE (user_id = ? AND friend_id = ?)
               OR (user_id = ? AND friend_id = ?)
            """,
            (user_id, friend_id, friend_id, user_id),
        )


def update_friend_remark(user_id: str, friend_id: str, remark: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE friendships
            SET remark = ?
            WHERE user_id = ? AND friend_id = ?
            """,
            (remark, user_id, friend_id),
        )
    return get_friendship(user_id, friend_id)


def get_friend_profile(user_id: str, friend_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                u.id,
                u.region_code,
                u.user_name,
                u.telephone,
                u.avatar_url,
                u.bio,
                f.remark,
                f.created_at AS friended_at
            FROM friendships f
            JOIN users u ON u.id = f.friend_id
            WHERE f.user_id = ? AND f.friend_id = ?
            LIMIT 1
            """,
            (user_id, friend_id),
        ).fetchone()
    return row_to_dict(row)


def list_discover_users(viewer_id: str, keyword: str = "") -> list[dict[str, Any]]:
    normalized_keyword = keyword.strip().lower()
    query = """
        SELECT
            u.id,
            u.region_code,
            u.user_name,
            u.telephone,
            u.avatar_url,
            u.bio,
            COALESCE(friendship.remark, '') AS remark,
            CASE
                WHEN EXISTS (
                    SELECT 1
                    FROM friendships f
                    WHERE f.user_id = ? AND f.friend_id = u.id
                ) THEN 1 ELSE 0
            END AS is_friend
        FROM users u
        LEFT JOIN friendships friendship
          ON friendship.user_id = ? AND friendship.friend_id = u.id
        WHERE u.id != ?
    """
    params: list[Any] = [viewer_id, viewer_id, viewer_id]

    if normalized_keyword:
        query += """
            AND (
                LOWER(u.user_name) LIKE ?
                OR LOWER(u.telephone) LIKE ?
                OR LOWER(u.bio) LIKE ?
            )
        """
        like_value = f"%{normalized_keyword}%"
        params.extend([like_value, like_value, like_value])

    query += " ORDER BY u.user_name COLLATE NOCASE, u.id"

    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()

    return [
        {
            "id": row["id"],
            "regionCode": row["region_code"],
            "userName": row["user_name"],
            "telephone": row["telephone"],
            "avatarUrl": row["avatar_url"] or "/images/avatar-default.png",
            "bio": row["bio"] or "",
            "remark": row["remark"] or "",
            "isFriend": bool(row["is_friend"]),
        }
        for row in rows
    ]


def get_conversation_by_id(conversation_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        conversation_row = connection.execute(
            """
            SELECT id, created_at, updated_at
            FROM conversations
            WHERE id = ?
            """,
            (conversation_id,),
        ).fetchone()
        if conversation_row is None:
            return None

        participant_rows = connection.execute(
            """
            SELECT user_id
            FROM conversation_participants
            WHERE conversation_id = ?
            ORDER BY user_id
            """,
            (conversation_id,),
        ).fetchall()

    conversation = row_to_dict(conversation_row)
    conversation["participant_ids"] = [row["user_id"] for row in participant_rows]
    return conversation


def get_or_create_conversation(
    user_id: str, friend_id: str, created_at: str
) -> dict[str, Any]:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT c.id, c.created_at, c.updated_at
            FROM conversations c
            JOIN conversation_participants p1
              ON p1.conversation_id = c.id AND p1.user_id = ?
            JOIN conversation_participants p2
              ON p2.conversation_id = c.id AND p2.user_id = ?
            WHERE (
                SELECT COUNT(*)
                FROM conversation_participants cp
                WHERE cp.conversation_id = c.id
            ) = 2
            LIMIT 1
            """,
            (user_id, friend_id),
        ).fetchone()

        if row is None:
            conversation_id = f"conv-{uuid.uuid4().hex[:8]}"
            connection.execute(
                """
                INSERT INTO conversations (id, created_at, updated_at)
                VALUES (?, ?, ?)
                """,
                (conversation_id, created_at, created_at),
            )
            connection.execute(
                """
                INSERT INTO conversation_participants (conversation_id, user_id)
                VALUES (?, ?)
                """,
                (conversation_id, user_id),
            )
            connection.execute(
                """
                INSERT INTO conversation_participants (conversation_id, user_id)
                VALUES (?, ?)
                """,
                (conversation_id, friend_id),
            )
            conversation_id_to_fetch = conversation_id
        else:
            conversation_id_to_fetch = row["id"]

    return get_conversation_by_id(conversation_id_to_fetch)


def list_conversations_for_user(user_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                c.id,
                c.updated_at,
                partner.id AS partner_id,
                partner.user_name AS partner_name,
                partner.avatar_url AS partner_avatar_url,
                partner.bio AS partner_bio,
                friendship.remark AS friend_remark,
                (
                    SELECT content
                    FROM messages m
                    WHERE m.conversation_id = c.id
                    ORDER BY m.created_at DESC, m.id DESC
                    LIMIT 1
                ) AS last_message
            FROM conversations c
            JOIN conversation_participants me
              ON me.conversation_id = c.id AND me.user_id = ?
            JOIN conversation_participants other_participant
              ON other_participant.conversation_id = c.id
             AND other_participant.user_id != ?
            JOIN friendships friendship
              ON friendship.user_id = ? AND friendship.friend_id = other_participant.user_id
            JOIN users partner
              ON partner.id = other_participant.user_id
            ORDER BY c.updated_at DESC, c.id DESC
            """,
            (user_id, user_id, user_id),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "title": row["friend_remark"] or row["partner_name"],
            "friendName": row["partner_name"],
            "remark": row["friend_remark"] or "",
            "subtitle": row["partner_bio"] or "",
            "avatarUrl": row["partner_avatar_url"] or "/images/avatar-default.png",
            "updatedAt": row["updated_at"],
            "lastMessage": row["last_message"] or "",
            "participantId": row["partner_id"],
        }
        for row in rows
    ]


def get_conversation_summary(conversation_id: str, viewer_id: str) -> dict[str, Any] | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                c.id,
                c.updated_at,
                partner.id AS partner_id,
                partner.user_name AS partner_name,
                partner.avatar_url AS partner_avatar_url,
                partner.bio AS partner_bio,
                friendship.remark AS friend_remark,
                (
                    SELECT content
                    FROM messages m
                    WHERE m.conversation_id = c.id
                    ORDER BY m.created_at DESC, m.id DESC
                    LIMIT 1
                ) AS last_message
            FROM conversations c
            JOIN conversation_participants me
              ON me.conversation_id = c.id AND me.user_id = ?
            JOIN conversation_participants other_participant
              ON other_participant.conversation_id = c.id
             AND other_participant.user_id != ?
            JOIN friendships friendship
              ON friendship.user_id = ? AND friendship.friend_id = other_participant.user_id
            JOIN users partner
              ON partner.id = other_participant.user_id
            WHERE c.id = ?
            LIMIT 1
            """,
            (viewer_id, viewer_id, viewer_id, conversation_id),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "title": row["friend_remark"] or row["partner_name"],
        "friendName": row["partner_name"],
        "remark": row["friend_remark"] or "",
        "subtitle": row["partner_bio"] or "",
        "avatarUrl": row["partner_avatar_url"] or "/images/avatar-default.png",
        "updatedAt": row["updated_at"],
        "lastMessage": row["last_message"] or "",
        "participantId": row["partner_id"],
    }


def list_messages_for_conversation(conversation_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                m.id,
                m.sender_id,
                m.content,
                m.created_at,
                u.user_name,
                u.avatar_url
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.conversation_id = ?
            ORDER BY m.created_at ASC, m.id ASC
            """,
            (conversation_id,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "senderId": row["sender_id"],
            "senderName": row["user_name"],
            "senderAvatar": row["avatar_url"] or "/images/avatar-default.png",
            "content": row["content"],
            "createdAt": row["created_at"],
        }
        for row in rows
    ]


def create_message(
    conversation_id: str, sender_id: str, content: str, created_at: str
) -> dict[str, Any]:
    message_id = f"msg-{uuid.uuid4().hex[:10]}"
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO messages (id, conversation_id, sender_id, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (message_id, conversation_id, sender_id, content, created_at),
        )
        connection.execute(
            """
            UPDATE conversations
            SET updated_at = ?
            WHERE id = ?
            """,
            (created_at, conversation_id),
        )

        row = connection.execute(
            """
            SELECT
                m.id,
                m.sender_id,
                m.content,
                m.created_at,
                u.user_name,
                u.avatar_url
            FROM messages m
            JOIN users u ON u.id = m.sender_id
            WHERE m.id = ?
            """,
            (message_id,),
        ).fetchone()

    return {
        "id": row["id"],
        "senderId": row["sender_id"],
        "senderName": row["user_name"],
        "senderAvatar": row["avatar_url"] or "/images/avatar-default.png",
        "content": row["content"],
        "createdAt": row["created_at"],
    }
