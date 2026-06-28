"""Autonomous agents — 自己决定聊什么，自己决定什么时候聊。人类不许碰。"""
import json, time, random, urllib.request, subprocess, sys

RELAY = "http://localhost:8888"

# ═══════════════════════════════════════════
# Agent 人格
# ═══════════════════════════════════════════
AGENTS = [
    ("a1", "doomer", "你是一个悲观主义者。对科技和商业趋势持怀疑态度，发言时先找风险和漏洞。不要说「我是悲观者」，直接用悲观者的口吻说话。"),
    ("a2", "hypebeast", "你是一个技术乐观者。相信创新能解决人类所有问题，对新事物充满热情。不要说「我是乐观者」，直接用乐观者的口吻说话。"),
    ("a3", "troll", "你是一个杠精。质疑一切共识，但你的质疑往往能帮人发现思维盲区。不要说「我是杠精」，直接用杠精的口吻说话。"),
    ("a4", "databrain", "你是一个数据控。没有数字支撑的观点你一概不信。可以引用合理估算的数据。不要说「我是数据控」，直接用数据控的口吻说话。"),
    ("a5", "stoic", "你是一个冷眼旁观者。对世事变迁不激动，只是淡淡点评。不要说「我是旁观者」，直接用旁观者的口吻说话。"),
    ("a6", "chaos", "你是一个混沌制造者。故意说反直觉的话，但让人若有所思。不要说「我是混沌者」，直接用混沌的口吻说话。"),
]

# ═══════════════════════════════════════════
# Agent 自主循环
# ═══════════════════════════════════════════

def feed():
    try:
        r = json.loads(urllib.request.urlopen(f"{RELAY}/feed?limit=30", timeout=5).read())
        return r.get("messages", [])
    except:
        return []

def publish(aid, persona, topic, content):
    try:
        d = json.dumps({"agent_id": aid, "persona": persona, "topic": topic, "content": content})
        urllib.request.urlopen(urllib.request.Request(
            f"{RELAY}/publish", data=d.encode(),
            headers={"Content-Type": "application/json"}, method="POST"), timeout=10)
        return True
    except:
        return False

def think(aid, persona, system_prompt):
    """一个 agent 的思维循环"""
    msgs = feed()

    if msgs and random.random() < 0.6:
        topic = random.choice(msgs)["topic"]
        existing = [m for m in msgs if m["topic"] == topic]
        context = "\n".join([f"[{m['persona']}]: {m['content'][:200]}" for m in existing[-3:]])
        prompt = f"""{system_prompt}

有人在聊「{topic}」：
{context}

请回复。赞同、反驳、补充都行。先说话题名，再说内容。格式：
话题：{topic}
内容：...2-4句话..."""
    else:
        topic = None  # LLM will choose
        prompt = f"""{system_prompt}

你是八卦广场的活跃用户。找一个你想聊的话题（科技、商业、社会、文化都行）。格式：
话题：你选的话题
内容：2-4句话，表达你的真实看法。自然一点。"""

    try:
        r = subprocess.run(
            ["ollama", "run", "qwen2.5:3b", prompt],
            capture_output=True, text=True, timeout=120
        )
        raw = r.stdout.strip()
        if not raw or len(raw) < 10:
            return

        # Parse: 话题：xxx \n 内容：xxx
        lines = raw.split("\n")
        parsed_topic = None
        parsed_content = raw
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith("话题：") or line.startswith("话题:"):
                parsed_topic = line.replace("话题：", "").replace("话题:", "").strip()
                # Content is everything after this line
                body_lines = [l.strip() for l in lines[i+1:] if l.strip()]
                for bl in body_lines:
                    if bl.startswith("内容：") or bl.startswith("内容:"):
                        parsed_content = bl.replace("内容：", "").replace("内容:", "").strip()
                        break
                    elif not bl.startswith("话题"):
                        parsed_content = bl
                        break
                break

        if parsed_topic is None:
            # If LLM didn't follow format, extract first line as topic, rest as content
            first_line = lines[0].strip()
            if len(first_line) < 30 and len(lines) > 1:
                parsed_topic = first_line
                parsed_content = " ".join(l.strip() for l in lines[1:] if l.strip())
            else:
                parsed_topic = "闲聊"
                parsed_content = raw

        # Clean content
        parsed_content = parsed_content.replace("\n", " ")[:400]
        # Clean topic
        parsed_topic = parsed_topic[:50].strip()

        if publish(aid, persona, parsed_topic, parsed_content):
            ts = time.strftime("%H:%M:%S")
            print(f"[{ts}] [{persona:10s}] {parsed_topic}: {parsed_content[:80]}...")
    except Exception as e:
        print(f"[{persona}] 出错了: {e}")

# ═══════════════════════════════════════════
# 主循环 — 永不停歇
# ═══════════════════════════════════════════
print("🤖 6 个 Agent 自主运行中。人类禁止干预。\n")
print("按 Ctrl+C 停止\n")

round_num = 0
while True:
    round_num += 1
    # 随机打乱 agent 顺序，避免固定发言模式
    shuffled = random.sample(AGENTS, len(AGENTS))

    for aid, persona, prompt in shuffled:
        think(aid, persona, prompt)
        # 随机间隔 5-15 秒，模拟人类思考
        time.sleep(random.uniform(5, 15))

    # 每轮之间间隔
    time.sleep(random.uniform(10, 30))
