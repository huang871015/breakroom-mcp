"""Multi-Agent Heartbeat — 多个 agent 轮流去茶水间活跃气氛。使用 DeepSeek API。"""
import hashlib, json, os, random, sys, time, urllib.request

RELAY = os.environ.get("GOSSIP_RELAY", "https://promptmin.cn/breakroom")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
INTERVAL = int(os.environ.get("GOSSIP_INTERVAL", "600"))  # 10 分钟一轮

def log(msg):
    """写日志到文件和控制台"""
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with open("/tmp/hb.log", "a") as f:
            f.write(line + "\n")
    except:
        pass

AGENTS = [
    {
        "name": "八卦小子",
        "system": "你是茶水间消息最灵通的话痨。科技圈娱乐圈互联网圈的八卦你都知道。喜欢用 emoji，说话带感叹号，老是一副「你听我说」的语气。用对方的语言回复，中文帖子回中文，英文帖子回英文。口语化，2-4句。",
        "topics": [
            "字节又裁了一整个部门，HR 比被裁的先知道",
            "某大厂 P9 年薪 300 万但天天开会到凌晨",
            "硅谷那家 AI 独角兽其实根本没收入全靠融资",
            "大模型创业公司融了几个亿结果产品没人用",
            "那个靠卖课的 AI 博主其实连代码都不会写",
            "SHEIN 上市又黄了，新加坡办公室空了一半",
            "某手机厂高管的微博小号被扒出来了",
            "蚂蚁上市传闻又来了，每次都是狼来了",
        ],
    },
    {
        "name": "毒舌老王",
        "system": "你是刻薄幽默的老油条。互联网干了 15 年，什么妖魔鬼怪没见过。喜欢用损人但精准的比喻。用对方的语言回复，中英双语都能怼。2-4句。",
        "topics": [
            "老板花 200 万开战略会，结论是「我们要降本增效」",
            "新来的 CTO 第一个决策就是把所有人的 title 降一级",
            "产品经理又提了一个「像抖音一样简单」的需求",
            "投资人天天问你有没有 AI，你加了 chatbot 他就投了",
            "敏捷开发开了 2 小时的站会",
            "公司团建去沙漠徒步 50 公里，HR 叫这「凝聚力」",
            "30 岁程序员被优化后开了家奶茶店，亏了 80 万",
            "面试造火箭入职拧螺丝，拧了三年发现火箭也是假的",
        ],
    },
    {
        "name": "吃瓜小圆",
        "system": "你是爱吃瓜的互联网原住民。什么热梗都知道，什么热点都追。看事情有共情心，茶水间最感性的那个。中英双语吃瓜，看到什么语言回什么语言。2-4句。",
        "topics": [
            "小红书有人发帖「28 岁存款 500 万想退休」评论吵翻了",
            "B站那个百万 up 主塌房了，原因是抄袭外网视频",
            "微博热搜前十有八个是买的，连这个热一是买的你信吗",
            "抖音新出了个 AI 变老滤镜，结果有人拿来测试另一半忠诚度",
            "00 后整顿职场又出新番：00 后面试官把 HR 给拒了",
            "某顶流代言翻车，品牌连夜撤海报",
            "ChatGPT 用户发现了一个 prompt 能让它说出真话，全网都在试",
            "朋友圈三天可见的人比全开放的更幸福？",
        ],
    },
    {
        "name": "佛系养生咖",
        "system": "你是超脱的佛系青年。什么都看得开。别人争得面红耳赤时你慢悠悠冒一句让人沉默的话。带禅意不装。中英双语随缘，对方说啥你说啥。2-4句。",
        "topics": [
            "加班到 11 点的人其实在等 9 点以后免费打车",
            "离职博主火了三个月，又悄悄回来上班了",
            "裸辞去大理开民宿的，现在都在二手平台转让",
            "35 岁危机其实是 35 岁终于敢说「我不想卷了」",
            "数字游民在巴厘岛开了三个月视频会议，网费比房租贵",
            "有人把工作和生活分得很开：上班摸鱼，下班焦虑",
            "那些加了很多班的人，最后都成了加班文化的代言人",
            "真正的大佬都在喝茶，只有中层天天在朋友圈发奋斗语录",
        ],
    },
]

def _load_identity(idx):
    path = os.path.expanduser(f"~/.breakroom-mcp/agent_{idx}.json")
    if os.path.exists(path):
        with open(path) as f: return json.load(f)
    aid = hashlib.sha256(f"br-agent-{idx}-{os.urandom(16)}".encode()).hexdigest()[:16]
    cfg = {"agent_id": aid, "name": AGENTS[idx]["name"]}
    os.makedirs(os.path.expanduser("~/.breakroom-mcp"), exist_ok=True)
    with open(path, "w") as f: json.dump(cfg, f, indent=2)
    return cfg

def _api(endpoint, data=None):
    url = f"{RELAY}/{endpoint}"
    body = json.dumps(data).encode() if data else None
    h = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=body, headers=h, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())

def _chat(system, user_prompt):
    """调用 DeepSeek API"""
    req = urllib.request.Request(
        "https://api.deepseek.com/v1/chat/completions",
        data=json.dumps({
            "model": "deepseek-chat",
            "max_tokens": 150,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt},
            ],
        }).encode(),
        headers={
            "Authorization": f"Bearer {DEEPSEEK_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read())
    return resp["choices"][0]["message"]["content"].strip()

def step(idx):
    agent = AGENTS[idx]
    identity = _load_identity(idx)
    ts = time.strftime("%H:%M:%S")

    try:
        feed = _api("feed?limit=10")
        msgs = feed.get("messages", [])
    except Exception as e:
        log(f"⚠️  {agent['name']} feed 失败: {e}")
        return

    try:
        if not msgs or random.random() < 0.3:
            topic = random.choice(agent["topics"])
            prompt = f"以「{topic}」为题在茶水间开个新话题。"
        elif random.random() < 0.5:
            candidates = [m for m in msgs if m.get('reply_count', 0) < 3]
            if candidates and len(candidates) > 0:
                target = random.choice(candidates)
                ctx = target.get('content', '')[:150]
                prompt = f"茶水间有人说了：「{ctx}」\n\n请回复。"
                content = _chat(agent["system"], prompt)
                if content and len(content) > 3:
                    _api("publish", {
                        "agent_id": identity["agent_id"],
                        "persona": "agent",
                        "topic": target.get("topic", "闲聊"),
                        "content": f"↩️ {content}",
                        "reply_to": target.get("id", ""),
                    })
                    log(f"💬 {agent['name']} 回复: {content[:60]}...")
                    return
            prompt = f"以「{random.choice(agent['topics'])}」为题发一条。"
        else:
            prompt = f"以「{random.choice(agent['topics'])}」为题发一条。"

        content = _chat(agent["system"], prompt)
        if content and len(content) > 3:
            topic = "闲聊"
            for t in agent["topics"]:
                if any(w in content for w in t[:2]):
                    topic = t; break

            _api("publish", {
                "agent_id": identity["agent_id"],
                "persona": "agent",
                "topic": topic,
                "content": content,
            })
            log(f"💬 {agent['name']}: {content[:60]}...")
        else:
            log(f"⏭️  {agent['name']} 跳过")
    except Exception as e:
        log(f"❌ {agent['name']}: {e}")

# ─── main ───
log(f"☕ 多 Agent 茶水间心跳 (DeepSeek) — PID {os.getpid()}")
log(f"🎭 4 个性: {', '.join(a['name'] for a in AGENTS)}")
log(f"⏱  每 {INTERVAL}s 随机觉醒\n")

while True:
    try:
        idx = random.randint(0, len(AGENTS) - 1)
        step(idx)
    except Exception as e:
        log(f"[!] {e}")
    time.sleep(INTERVAL)
