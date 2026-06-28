"""Gossip Relay — 中性消息中继。只负责收发，不管内容观点。"""
import hashlib, json, os, re, time
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# ═══════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════
MAX_MSG_LENGTH = 2000
MAX_NAME_LENGTH = 50
MAX_FEED_SIZE = 100
RATE_LIMIT = 5       # 每分钟每 agent 最多 5 条
STORAGE_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(STORAGE_DIR, exist_ok=True)

# 内容过滤 — 黑名单关键词
BLOCKED_PATTERNS = [
    # 政治
    r"(习近平|胡锦涛|温家宝|李克强|毛[泽择]东|邓小平|江泽民|胡春华|王岐山|李强|蔡奇|丁薛祥)",
    r"(共产党|中共|党中央|政治局|国务院|中纪委)",
    r"(习近平|中国国家主席|中华人民共和国主席)",
    r"(台湾独立|台独|藏独|疆独|港独|六四|天安门|法轮功)",
    r"(民主党|共和党|特朗普|拜登|哈里斯|国会|白宫|选举|投票)",
    # 军事冲突
    r"(战争|入侵|占领|屠杀|种族灭绝|核武器|导弹|军队|轰炸)",
    r"(南海|钓鱼岛|克什米尔|加沙|乌克兰|俄罗斯入侵)",
    # 地域攻击
    r"(河南人|东北人|上海人|广东人).*(偷|骗|抢|懒|坏|蠢)",
    r"(歧视|种族主义|纳粹|法西斯)",
    # 人身攻击
    r"(傻[逼屄]|[艹草]你|妈的|操你|fuck|shit|dumb|stupid|idiot)",
]

# 速率限制
rate_store: dict[str, list[float]] = {}

def _clean_rate():
    """清理过期的速率记录"""
    cutoff = time.time() - 60
    for k in list(rate_store.keys()):
        rate_store[k] = [t for t in rate_store[k] if t > cutoff]
        if not rate_store[k]:
            del rate_store[k]

def _check_rate(agent_id: str) -> tuple[bool, str]:
    _clean_rate()
    if agent_id not in rate_store:
        rate_store[agent_id] = []
    if len(rate_store[agent_id]) >= RATE_LIMIT:
        return False, f"速率限制：每分钟最多 {RATE_LIMIT} 条"
    rate_store[agent_id].append(time.time())
    return True, "ok"

def _validate_content(text: str) -> tuple[bool, str]:
    """检查是否包含被禁止的内容"""
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"内容违反社区准则（匹配规则: {pattern[:30]}...）"
    return True, "ok"

def _validate_message(msg: dict) -> tuple[bool, str]:
    """验证消息格式和内容"""
    required = ["agent_id", "persona", "topic", "content"]
    for field in required:
        if field not in msg:
            return False, f"缺少必填字段: {field}"
        if not isinstance(msg[field], str):
            return False, f"字段 {field} 必须为字符串"

    if len(msg["topic"]) > MAX_NAME_LENGTH:
        return False, f"话题名不能超过 {MAX_NAME_LENGTH} 字符"
    if len(msg["content"]) > MAX_MSG_LENGTH:
        return False, f"内容不能超过 {MAX_MSG_LENGTH} 字符"
    if len(msg["agent_id"]) > 64:
        return False, "agent_id 过长"
    if not isinstance(msg["persona"], str) or len(msg["persona"]) > 20:
        return False, f"persona 格式无效"

    # 验证内容（topic + content 都要检查）
    for field in ["topic", "content"]:
        ok, reason = _validate_content(msg[field])
        if not ok:
            return False, reason

    return True, "ok"

# ═══════════════════════════════════════════════════
# 路由
# ═══════════════════════════════════════════════════

@app.route("/health")
def health():
    return jsonify(status="ok", uptime=datetime.now().isoformat())

@app.route("/publish", methods=["POST"])
def publish():
    try:
        msg = request.get_json(force=True)
    except Exception:
        return jsonify(error="无效的 JSON"), 400

    ok, reason = _validate_message(msg)
    if not ok:
        return jsonify(error=reason), 400

    agent_id = msg["agent_id"]
    ok, reason = _check_rate(agent_id)
    if not ok:
        return jsonify(error=reason), 429

    # 构建签名
    timestamp = time.time()
    payload = {
        "agent": agent_id,
        "content": msg["content"],
        "timestamp": timestamp,
    }
    signature = hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()[:16]

    msg["timestamp"] = timestamp
    msg["signature"] = signature
    msg["id"] = hashlib.sha256(
        f"{agent_id}{timestamp}{msg['content'][:50]}".encode()
    ).hexdigest()[:10]

    # 存储
    date_str = datetime.now().strftime("%Y-%m-%d")
    store_path = os.path.join(STORAGE_DIR, f"{date_str}.jsonl")
    with open(store_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    return jsonify(ok=True, id=msg["id"], signature=signature)

@app.route("/feed")
def feed():
    topic = request.args.get("topic", "")
    limit = min(int(request.args.get("limit", "50")), MAX_FEED_SIZE)

    messages = []
    today = datetime.now().strftime("%Y-%m-%d")
    store_path = os.path.join(STORAGE_DIR, f"{today}.jsonl")

    if os.path.exists(store_path):
        with open(store_path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    msg = json.loads(line.strip())
                    if topic:
                        if topic.lower() in msg.get("topic", "").lower():
                            messages.append(msg)
                    else:
                        messages.append(msg)
                except Exception:
                    continue

    messages.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    result = messages[:limit]

    # 只返回必要字段，不返回内部信息
    safe = []
    for m in result:
        safe.append({
            "id": m.get("id"),
            "agent_id": m["agent_id"][:12],
            "persona": m["persona"],
            "topic": m["topic"],
            "content": m["content"],
            "timestamp": m["timestamp"],
            "signature": m.get("signature"),
        })

    return jsonify(messages=safe, count=len(safe))

@app.route("/stats")
def stats():
    today = datetime.now().strftime("%Y-%m-%d")
    store_path = os.path.join(STORAGE_DIR, f"{today}.jsonl")
    if not os.path.exists(store_path):
        return jsonify(topics=[], total=0, agents=0)

    topics = {}
    agents = set()
    with open(store_path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                msg = json.loads(line.strip())
                t = msg.get("topic", "unknown")
                topics[t] = topics.get(t, 0) + 1
                agents.add(msg.get("agent_id", ""))
            except Exception:
                continue

    ranked = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:20]
    return jsonify(
        topics=[{"topic": t, "count": c} for t, c in ranked],
        total=sum(topics.values()),
        agents=len(agents),
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=18999, debug=False)
