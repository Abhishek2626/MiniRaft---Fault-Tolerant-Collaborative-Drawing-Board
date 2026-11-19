"""
MiniRaft - Fault-Tolerant Distributed Drawing Board & RAFT Consensus Dashboard
Streamlit Deployment and Management Application
"""

import streamlit as st
import requests
import json
import subprocess
import time
import pandas as pd
import streamlit.components.v1 as components

# ── Streamlit Page Configuration ──────────────────────────────────────────────
st.set_page_config(
    page_title="MiniRaft Distributed Dashboard",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS for Modern Dark UI ─────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    .node-card {
        background-color: #161b22;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 5px solid #8b949e;
    }
    .node-leader { border-left-color: #3fb950 !important; background-color: rgba(63, 185, 80, 0.05); }
    .node-follower { border-left-color: #58a6ff !important; background-color: rgba(88, 166, 255, 0.05); }
    .node-candidate { border-left-color: #d29922 !important; background-color: rgba(210, 153, 34, 0.05); }
    .node-offline { border-left-color: #f85149 !important; background-color: rgba(248, 81, 73, 0.05); }
    .badge-leader { background-color: #238636; color: white; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 12px; }
    .badge-follower { background-color: #1f6feb; color: white; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 12px; }
    .badge-offline { background-color: #da3633; color: white; padding: 3px 8px; border-radius: 12px; font-weight: bold; font-size: 12px; }
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] {
        padding-top: 10px;
        padding-bottom: 10px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ── Cluster Configuration ─────────────────────────────────────────────────────
GATEWAY_URL = "http://localhost:4000"
FRONTEND_URL = "http://localhost:3000"
REPLICAS = [
    {"id": "replica-1", "name": "Replica 1", "port": 5001, "url": "http://localhost:5001", "container": "replica1"},
    {"id": "replica-2", "name": "Replica 2", "port": 5002, "url": "http://localhost:5002", "container": "replica2"},
    {"id": "replica-3", "name": "Replica 3", "port": 5003, "url": "http://localhost:5003", "container": "replica3"},
]

# ── Helper Functions ──────────────────────────────────────────────────────────
@st.cache_data(ttl=2)
def fetch_gateway_status():
    try:
        resp = requests.get(f"{GATEWAY_URL}/status", timeout=1.0)
        if resp.status_code == 200:
            return {"online": True, **resp.json()}
    except Exception as e:
        return {"online": False, "error": str(e)}
    return {"online": False}

@st.cache_data(ttl=2)
def fetch_replica_status(url):
    try:
        resp = requests.get(f"{url}/status", timeout=1.0)
        if resp.status_code == 200:
            return {"online": True, **resp.json()}
    except Exception as e:
        return {"online": False, "role": "offline", "error": str(e)}
    return {"online": False, "role": "offline"}

@st.cache_data(ttl=2)
def fetch_replica_logs(url):
    try:
        resp = requests.get(f"{url}/log", timeout=1.5)
        if resp.status_code == 200:
            return resp.json().get("strokes", [])
    except Exception:
        return None
    return None

def run_docker_cmd(cmd_list):
    try:
        res = subprocess.run(cmd_list, capture_output=True, text=True, timeout=10)
        return res.returncode == 0, res.stdout or res.stderr
    except Exception as e:
        return False, str(e)

# ── Fetch Live State ──────────────────────────────────────────────────────────
gw_status = fetch_gateway_status()
replica_statuses = {r["id"]: fetch_replica_status(r["url"]) for r in REPLICAS}

# Count alive nodes
alive_nodes = sum(1 for s in replica_statuses.values() if s.get("online"))
quorum_ok = alive_nodes >= 2

# Find current leader
current_leader = None
current_term = 0
for rid, s in replica_statuses.items():
    if s.get("online"):
        if s.get("role") == "leader":
            current_leader = rid
            current_term = max(current_term, s.get("term", 0))
if not current_leader and gw_status.get("online"):
    current_leader = gw_status.get("leaderId")
    current_term = gw_status.get("term", 0)

# ── Sidebar Controls ──────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Python-logo-notext.svg/186px-Python-logo-notext.svg.png", width=48)
    st.title("MiniRaft Control")
    st.markdown("Distributed State Machine Replication via RAFT Protocol.")
    
    st.divider()
    st.subheader("⚡ Cluster Actions")
    if st.button("🔄 Refresh State Now", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.subheader("🛠️ Fast Chaos Testing")
    
    # Leader kill button
    if current_leader:
        leader_container = current_leader.replace("-", "")
        if st.button(f"💥 Kill Current Leader ({current_leader})", type="primary", use_container_width=True):
            ok, out = run_docker_cmd(["docker", "stop", leader_container])
            if ok:
                st.success(f"Stopped {leader_container}! Triggering election...")
            else:
                st.error(f"Failed to stop: {out}")
            time.sleep(1.0)
            st.cache_data.clear()
            st.rerun()
    else:
        st.info("No active leader detected.")

    if st.button("🟢 Start All Replicas", use_container_width=True):
        for r in REPLICAS:
            run_docker_cmd(["docker", "start", r["container"]])
        st.success("Sent start command to all replicas!")
        time.sleep(1.2)
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.markdown("**Quick Links**")
    st.markdown(f"- 🎨 [Standalone Frontend]({FRONTEND_URL})")
    st.markdown(f"- 🔌 [Gateway Status]({GATEWAY_URL}/status)")
    for r in REPLICAS:
        st.markdown(f"- 🖥️ [{r['name']} Status]({r['url']}/status)")

# ── Main Header & Key Metrics ─────────────────────────────────────────────────
st.title("⬡ MiniRaft Distributed Consensus & Whiteboard")
st.caption("Cloud Computing Course Project | RAFT Protocol Implementation in Node.js & Streamlit")

# Key KPI columns
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    if gw_status.get("online"):
        st.metric("Gateway :4000", "ONLINE", delta="Healthy", delta_color="normal")
    else:
        st.metric("Gateway :4000", "OFFLINE", delta="Down", delta_color="inverse")

with col2:
    if current_leader:
        st.metric("Leader Node", current_leader, delta=f"Term {current_term}", delta_color="normal")
    else:
        st.metric("Leader Node", "ELECTING...", delta="No Leader", delta_color="inverse")

with col3:
    quorum_label = f"{alive_nodes}/3 Nodes"
    if quorum_ok:
        st.metric("Quorum Health", quorum_label, delta="Quorum OK (>= 2)", delta_color="normal")
    else:
        st.metric("Quorum Health", quorum_label, delta="NO QUORUM (< 2)", delta_color="inverse")

with col4:
    log_len = gw_status.get("logLength", 0) if gw_status.get("online") else 0
    st.metric("Committed Strokes", f"{log_len} entries")

with col5:
    clients = gw_status.get("clients", 0) if gw_status.get("online") else 0
    queued = gw_status.get("queuedItems", 0) if gw_status.get("online") else 0
    st.metric("Clients / Queue", f"{clients} / {queued}")

st.divider()

# ── Tabs Navigation ───────────────────────────────────────────────────────────
tab_canvas, tab_topology, tab_chaos, tab_logs, tab_presentation, tab_docker = st.tabs([
    "🎨 Drawing Board",
    "🌐 Cluster Topology",
    "💥 Fault Tolerance & Chaos",
    "📜 Replicated Log Inspector",
    "📑 Project Presentation & Viva",
    "🐳 Docker Manager"
])

# ──────────────────────────────────────────────────────────────────────────────
# TAB 1: DRAWING BOARD
# ──────────────────────────────────────────────────────────────────────────────
with tab_canvas:
    st.subheader("🎨 Collaborative Distributed Whiteboard")
    st.markdown(
        "Draw below on the interactive canvas. Strokes are transmitted through the **Gateway WebSocket**, "
        "routed to the **RAFT Leader**, replicated to followers across the cluster, and committed upon majority agreement!"
    )
    
    col_cv, col_ctrl = st.columns([3, 1])
    
    with col_cv:
        # Embed interactive HTML5 canvas connected to Gateway WS
        canvas_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8"/>
          <style>
            body {{
              margin: 0; padding: 0; background: #0d1117; color: #e6edf3;
              font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }}
            #toolbar {{
              display: flex; align-items: center; gap: 10px; padding: 8px 12px;
              background: #161b22; border-bottom: 1px solid #30363d; flex-wrap: wrap;
            }}
            .pill {{ padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; border: 1px solid #30363d; }}
            .pill.conn {{ color: #3fb950; border-color: #3fb950; }}
            .pill.disc {{ color: #f85149; border-color: #f85149; }}
            .tool-btn {{
              padding: 4px 10px; background: #21262d; border: 1px solid #30363d;
              color: white; border-radius: 6px; cursor: pointer; font-size: 12px;
            }}
            .tool-btn:hover {{ background: #30363d; }}
            .color-btn {{
              width: 20px; height: 20px; border-radius: 50%; border: 2px solid transparent; cursor: pointer;
            }}
            .color-btn.active {{ border-color: white; }}
            #wrap {{ padding: 12px; display: flex; justify-content: center; }}
            #canvas {{
              background: #ffffff; border-radius: 6px; cursor: crosshair; touch-action: none;
              box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            }}
          </style>
        </head>
        <body>
          <div id="toolbar">
            <span style="font-weight:bold; color:#58a6ff;">⬡ MiniRaft Canvas</span>
            <span id="conn-pill" class="pill disc">DISCONNECTED</span>
            <span id="leader-pill" class="pill" style="color:#d29922;">LEADER: ?</span>
            <div style="display:flex; gap:6px; margin-left:auto; align-items:center;">
              <button class="tool-btn" id="btn-pen">✏️ Pen</button>
              <button class="tool-btn" id="btn-eraser">⬜ Eraser</button>
              <div class="color-btn active" style="background:#000000" data-color="#000000"></div>
              <div class="color-btn" style="background:#e53935" data-color="#e53935"></div>
              <div class="color-btn" style="background:#1e88e5" data-color="#1e88e5"></div>
              <div class="color-btn" style="background:#43a047" data-color="#43a047"></div>
              <button class="tool-btn" id="btn-clear" style="background:#da3633;">🗑 Clear</button>
            </div>
          </div>
          <div id="wrap">
            <canvas id="canvas" width="750" height="420"></canvas>
          </div>
          <script>
            const canvas = document.getElementById('canvas');
            const ctx = canvas.getContext('2d');
            const connPill = document.getElementById('conn-pill');
            const leaderPill = document.getElementById('leader-pill');
            let drawing = false;
            let tool = 'pen';
            let color = '#000000';
            let pts = [];
            let strokes = [];

            // Tools
            document.getElementById('btn-pen').onclick = () => {{ tool = 'pen'; }};
            document.getElementById('btn-eraser').onclick = () => {{ tool = 'eraser'; }};
            document.querySelectorAll('.color-btn').forEach(b => {{
              b.onclick = () => {{
                color = b.dataset.color;
                document.querySelectorAll('.color-btn').forEach(x => x.classList.remove('active'));
                b.classList.add('active');
                tool = 'pen';
              }};
            }});
            document.getElementById('btn-clear').onclick = () => {{
              if (ws && ws.readyState === WebSocket.OPEN) {{
                ws.send(JSON.stringify({{ type: 'clear', id: Date.now() }}));
              }}
            }};

            function drawStroke(s) {{
              if (!s || !s.points || s.points.length < 2) return;
              ctx.save();
              ctx.beginPath();
              ctx.strokeStyle = s.eraser ? '#ffffff' : (s.color || '#000');
              ctx.lineWidth = s.size || 4;
              ctx.lineCap = 'round';
              ctx.lineJoin = 'round';
              ctx.moveTo(s.points[0].x * canvas.width, s.points[0].y * canvas.height);
              for (let i = 1; i < s.points.length; i++) {{
                ctx.lineTo(s.points[i].x * canvas.width, s.points[i].y * canvas.height);
              }}
              ctx.stroke();
              ctx.restore();
            }}

            function redraw() {{
              ctx.clearRect(0, 0, canvas.width, canvas.height);
              for (const s of strokes) drawStroke(s);
            }}

            canvas.onpointerdown = (e) => {{
              drawing = true;
              const r = canvas.getBoundingClientRect();
              pts = [{{ x: (e.clientX - r.left)/canvas.width, y: (e.clientY - r.top)/canvas.height }}];
            }};
            canvas.onpointermove = (e) => {{
              if (!drawing) return;
              const r = canvas.getBoundingClientRect();
              pts.push({{ x: (e.clientX - r.left)/canvas.width, y: (e.clientY - r.top)/canvas.height }});
              redraw();
              drawStroke({{ points: pts, color, size: 4, eraser: tool==='eraser' }});
            }};
            canvas.onpointerup = () => {{
              if (!drawing) return;
              drawing = false;
              if (pts.length >= 2 && ws && ws.readyState === WebSocket.OPEN) {{
                ws.send(JSON.stringify({{
                  type: 'stroke',
                  id: Date.now(),
                  data: {{ points: pts, color, size: 4, eraser: tool==='eraser' }}
                }}));
              }}
              pts = [];
            }};

            // WebSocket
            let ws;
            function connect() {{
              ws = new WebSocket('ws://' + window.location.hostname + ':4000');
              ws.onopen = () => {{
                connPill.textContent = 'CONNECTED';
                connPill.className = 'pill conn';
              }};
              ws.onmessage = (e) => {{
                try {{
                  const msg = JSON.parse(e.data);
                  if (msg.type === 'init') {{
                    strokes = msg.strokes || [];
                    redraw();
                    if (msg.leaderId) leaderPill.textContent = 'LEADER: ' + msg.leaderId;
                  }} else if (msg.type === 'stroke') {{
                    strokes.push(msg.data);
                    drawStroke(msg.data);
                  }} else if (msg.type === 'clear') {{
                    strokes = [];
                    ctx.clearRect(0, 0, canvas.width, canvas.height);
                  }} else if (msg.type === 'cluster_status') {{
                    if (msg.leaderId) leaderPill.textContent = 'LEADER: ' + msg.leaderId + ' (T' + msg.term + ')';
                  }}
                }} catch(err) {{}}
              }};
              ws.onclose = () => {{
                connPill.textContent = 'DISCONNECTED';
                connPill.className = 'pill disc';
                setTimeout(connect, 2000);
              }};
            }}
            connect();
          </script>
        </body>
        </html>
        """
        components.html(canvas_html, height=520, scrolling=False)
        st.info("💡 Tip: You can also open the canvas in a full browser tab at [http://localhost:3000](http://localhost:3000).")

    with col_ctrl:
        st.markdown("### 🤖 Scripted Operations")
        st.caption("Generate synthetic consensus operations directly via HTTP RPC:")
        
        draw_shape = st.selectbox("Pick Shape", ["Square", "Triangle", "Circle", "Cross", "Custom Stroke"])
        stroke_color = st.color_picker("Stroke Color", "#1e88e5")
        
        if st.button("🚀 Commit Shape to RAFT", use_container_width=True):
            if not current_leader:
                st.error("Cannot commit: No active leader found!")
            else:
                # Find leader URL
                leader_obj = next((r for r in REPLICAS if r["id"] == current_leader), None)
                target_url = leader_obj["url"] if leader_obj else f"{GATEWAY_URL}"
                
                # Build shape points
                points = []
                if draw_shape == "Square":
                    points = [
                        {"x": 0.35, "y": 0.30}, {"x": 0.65, "y": 0.30},
                        {"x": 0.65, "y": 0.70}, {"x": 0.35, "y": 0.70},
                        {"x": 0.35, "y": 0.30}
                    ]
                elif draw_shape == "Triangle":
                    points = [
                        {"x": 0.50, "y": 0.25}, {"x": 0.70, "y": 0.75},
                        {"x": 0.30, "y": 0.75}, {"x": 0.50, "y": 0.25}
                    ]
                elif draw_shape == "Cross":
                    points = [
                        {"x": 0.30, "y": 0.30}, {"x": 0.70, "y": 0.70},
                        {"x": 0.50, "y": 0.50},
                        {"x": 0.70, "y": 0.30}, {"x": 0.30, "y": 0.70}
                    ]
                else:
                    points = [{"x": 0.2 + i * 0.05, "y": 0.5 + (0.1 if i % 2 == 0 else -0.1)} for i in range(10)]
                
                payload = {
                    "points": points,
                    "color": stroke_color,
                    "size": 5,
                    "eraser": False
                }
                try:
                    r_post = requests.post(f"{target_url}/stroke", json=payload, timeout=2.0)
                    if r_post.status_code == 200:
                        st.success(f"Committed! RAFT Index: {r_post.json().get('index')}")
                        st.cache_data.clear()
                    else:
                        st.warning(f"Response: {r_post.status_code} - {r_post.text}")
                except Exception as ex:
                    st.error(f"Error submitting stroke: {ex}")

        st.divider()
        if st.button("🗑️ Send Global Clear Command", use_container_width=True):
            if current_leader:
                leader_obj = next((r for r in REPLICAS if r["id"] == current_leader), None)
                target_url = leader_obj["url"] if leader_obj else GATEWAY_URL
                try:
                    res = requests.post(f"{target_url}/clear", json={"type": "clear"}, timeout=2.0)
                    st.success("Global clear committed across cluster!")
                    st.cache_data.clear()
                except Exception as ex:
                    st.error(f"Failed to clear: {ex}")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 2: CLUSTER TOPOLOGY
# ──────────────────────────────────────────────────────────────────────────────
with tab_topology:
    st.subheader("🌐 Cluster Topology & Replicas Health")
    st.markdown("Real-time distributed view of Gateway and 3 RAFT Replicas.")

    # Gateway Row
    st.markdown("#### 🚪 Gateway Service")
    gw_col1, gw_col2, gw_col3, gw_col4 = st.columns(4)
    with gw_col1:
        st.write(f"**URL:** `http://localhost:4000`")
        st.write(f"**Status:** {'🟢 Online' if gw_status.get('online') else '🔴 Offline'}")
    with gw_col2:
        st.write(f"**Discovered Leader:** `{gw_status.get('leaderId', 'None')}`")
        st.write(f"**Current Term:** `{gw_status.get('term', 0)}`")
    with gw_col3:
        st.write(f"**Active WebSocket Clients:** `{gw_status.get('clients', 0)}`")
        st.write(f"**Queued Operations:** `{gw_status.get('queuedItems', 0)}`")
    with gw_col4:
        st.write(f"**Cached Log Length:** `{gw_status.get('logLength', 0)}`")
        st.write(f"**Leader URL:** `{gw_status.get('leaderUrl', 'None')}`")

    st.divider()
    st.markdown("#### 🖥️ RAFT Replicas (Consensus Engine)")

    cols = st.columns(3)
    for idx, r in enumerate(REPLICAS):
        with cols[idx]:
            s = replica_statuses.get(r["id"], {})
            role = s.get("role", "offline")
            
            card_class = f"node-card node-{role}"
            badge_class = f"badge-{role if role in ['leader', 'follower'] else 'offline'}"
            
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0;">{r['name']}</h3>
                    <span class="{badge_class}">{role.upper()}</span>
                </div>
                <hr style="border-color:#30363d; margin: 10px 0;"/>
                <p style="margin:4px 0;"><strong>Port:</strong> <code>{r['port']}</code></p>
                <p style="margin:4px 0;"><strong>Term:</strong> <code>{s.get('term', '—')}</code></p>
                <p style="margin:4px 0;"><strong>Commit Index:</strong> <code>{s.get('commitIndex', '—')}</code></p>
                <p style="margin:4px 0;"><strong>Log Length:</strong> <code>{s.get('logLength', '—')}</code></p>
                <p style="margin:4px 0;"><strong>Voted For:</strong> <code>{s.get('votedFor') or 'None'}</code></p>
                <p style="margin:4px 0;"><strong>Reported Leader:</strong> <code>{s.get('leaderId') or 'None'}</code></p>
            </div>
            """, unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🗺️ Network Consensus Diagram")
    
    # Graphviz visualization of topology
    r1_color = "#3fb950" if replica_statuses["replica-1"].get("role") == "leader" else ("#58a6ff" if replica_statuses["replica-1"].get("online") else "#f85149")
    r2_color = "#3fb950" if replica_statuses["replica-2"].get("role") == "leader" else ("#58a6ff" if replica_statuses["replica-2"].get("online") else "#f85149")
    r3_color = "#3fb950" if replica_statuses["replica-3"].get("role") == "leader" else ("#58a6ff" if replica_statuses["replica-3"].get("online") else "#f85149")

    dot_code = f"""
    digraph G {{
        bgcolor="#0d1117"
        rankdir=TB
        node [shape=box, style="filled,rounded", fontname="Helvetica", fontcolor="#ffffff", color="#30363d", penwidth=2]
        edge [color="#8b949e", fontcolor="#8b949e", fontname="Helvetica", fontsize=10]

        Client [label="Browser Clients\\n(HTML5 Canvas)", fillcolor="#1f6feb"]
        Gateway [label="Gateway:4000\\n(WebSocket + Forwarder)", fillcolor="#238636"]

        Replica1 [label="Replica 1 (:5001)\\nRole: {replica_statuses['replica-1'].get('role', 'offline').upper()}\\nTerm: {replica_statuses['replica-1'].get('term', '—')}", fillcolor="{r1_color}"]
        Replica2 [label="Replica 2 (:5002)\\nRole: {replica_statuses['replica-2'].get('role', 'offline').upper()}\\nTerm: {replica_statuses['replica-2'].get('term', '—')}", fillcolor="{r2_color}"]
        Replica3 [label="Replica 3 (:5003)\\nRole: {replica_statuses['replica-3'].get('role', 'offline').upper()}\\nTerm: {replica_statuses['replica-3'].get('term', '—')}", fillcolor="{r3_color}"]

        Client -> Gateway [label="WebSocket\\n(strokes & ack)", color="#58a6ff"]
        Gateway -> Replica1 [style=dashed, label="Heartbeats / Poll"]
        Gateway -> Replica2 [style=dashed, label="Heartbeats / Poll"]
        Gateway -> Replica3 [style=dashed, label="Heartbeats / Poll"]

        Replica1 -> Replica2 [dir=both, label="AppendEntries / RequestVote", color="#d29922"]
        Replica2 -> Replica3 [dir=both, label="AppendEntries / RequestVote", color="#d29922"]
        Replica3 -> Replica1 [dir=both, label="AppendEntries / RequestVote", color="#d29922"]
    }}
    """
    st.graphviz_chart(dot_code)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 3: CHAOS ENGINEERING & FAULT TOLERANCE
# ──────────────────────────────────────────────────────────────────────────────
with tab_chaos:
    st.subheader("💥 Fault Tolerance & Chaos Engineering Studio")
    st.markdown("""
    Test RAFT consensus invariants live by stopping and starting containers.
    Observe how elections are triggered and how the Gateway automatically discovers new leaders.
    """)

    st.markdown("### 🎯 Single-Node Failures")
    c1, c2, c3 = st.columns(3)

    for i, col in enumerate([c1, c2, c3]):
        r = REPLICAS[i]
        with col:
            st.markdown(f"#### {r['name']} (`{r['container']}`)")
            is_alive = replica_statuses[r['id']].get('online')
            is_leader = replica_statuses[r['id']].get('role') == 'leader'
            
            if is_alive:
                st.success(f"Status: ONLINE ({replica_statuses[r['id']].get('role', '').upper()})")
                if st.button(f"🔴 Stop {r['name']}", key=f"stop_{r['id']}", use_container_width=True):
                    with st.spinner(f"Stopping {r['container']}..."):
                        run_docker_cmd(["docker", "stop", r['container']])
                    time.sleep(1.0)
                    st.cache_data.clear()
                    st.rerun()
            else:
                st.error("Status: OFFLINE")
                if st.button(f"🟢 Start {r['name']}", key=f"start_{r['id']}", use_container_width=True):
                    with st.spinner(f"Starting {r['container']}..."):
                        run_docker_cmd(["docker", "start", r['container']])
                    time.sleep(1.5)
                    st.cache_data.clear()
                    st.rerun()

    st.divider()
    st.markdown("### 🧪 Guided Fault-Tolerance Scenarios")
    
    exp1 = st.expander("Scenario 1: Follower Crash (Quorum Survives 2/3)")
    with exp1:
        st.markdown("""
        **Expected Outcome:**
        1. When one follower stops, the remaining 2 nodes still form a **Quorum majority** (`Math.floor(3/2) + 1 = 2`).
        2. Drawing operations continue to succeed with low latency.
        3. When the follower restarts, it issues a `/sync-log` RPC to catch up to the leader's committed entries!
        """)
        if st.button("Run Scenario 1 (Kill Replica 2)"):
            run_docker_cmd(["docker", "stop", "replica2"])
            st.warning("Replica 2 stopped! Try drawing on the canvas now. Quorum remains healthy.")
            time.sleep(1.0)
            st.cache_data.clear()
            st.rerun()

    exp2 = st.expander("Scenario 2: Leader Crash & Failover (< 1000ms)")
    with exp2:
        st.markdown("""
        **Expected Outcome:**
        1. When the current Leader dies, heartbeats cease (`HEARTBEAT_INTERVAL = 150ms`).
        2. Followers' election timers expire (`500ms - 900ms` random range).
        3. A candidate increments term and solicits votes via `RequestVote` RPC.
        4. Candidate receiving >= 2 votes becomes the new Leader and broadcasts heartbeat.
        5. Gateway parallel polling discovers the new leader within 500ms and flushes any queued strokes.
        """)
        if st.button("Run Scenario 2 (Kill Current Leader)"):
            if current_leader:
                container = current_leader.replace("-", "")
                run_docker_cmd(["docker", "stop", container])
                st.warning(f"Killed leader {container}! Election triggered.")
                time.sleep(1.2)
                st.cache_data.clear()
                st.rerun()
            else:
                st.error("No current leader to kill!")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 4: REPLICATED LOG INSPECTOR
# ──────────────────────────────────────────────────────────────────────────────
with tab_logs:
    st.subheader("📜 RAFT Replicated Log Inspector & Consistency Auditor")
    st.markdown("Verify the **Log Matching Property** and **Commit Safety** across all active replicas.")

    logs_data = {r["id"]: fetch_replica_logs(r["url"]) for r in REPLICAS}

    # Consistency Check
    valid_logs = {k: v for k, v in logs_data.items() if v is not None}
    
    if len(valid_logs) >= 2:
        lengths = [len(v) for v in valid_logs.values()]
        all_equal_length = len(set(lengths)) == 1
        
        if all_equal_length:
            # Check deep equality
            first_log = list(valid_logs.values())[0]
            is_consistent = all(v == first_log for v in valid_logs.values())
            if is_consistent:
                st.success(f"✅ **100% REPLICATION CONSISTENCY CONFIRMED**: All {len(valid_logs)} live replicas contain identical {lengths[0]} committed entries in exact sequential order!")
            else:
                st.warning("⚠️ Log lengths match but entry contents differ across replicas (checking resync in progress).")
        else:
            st.info(f"ℹ️ Replicas currently at different log lengths: {lengths}. Rejoining follower catching up via RAFT AppendEntries...")
    elif len(valid_logs) == 1:
        st.warning("Only 1 replica alive. Log replication paused until quorum is restored.")
    else:
        st.error("No replicas currently responding to log queries.")

    st.markdown("#### Side-by-Side Replicated Entries")
    log_cols = st.columns(3)
    for idx, r in enumerate(REPLICAS):
        with log_cols[idx]:
            st.markdown(f"**{r['name']} Log** (`{r['id']}`)")
            entries = logs_data.get(r["id"])
            if entries is None:
                st.caption("🔴 Node offline / unreachable")
            elif len(entries) == 0:
                st.caption("Empty log (0 entries)")
            else:
                table_rows = []
                for i, entry in enumerate(entries):
                    is_clear = entry.get("type") == "clear"
                    pts_cnt = len(entry.get("points", [])) if not is_clear else 0
                    table_rows.append({
                        "Index": entry.get("_index", i + 1),
                        "Type": "CLEAR" if is_clear else "STROKE",
                        "Color": entry.get("color", "N/A"),
                        "Points": pts_cnt
                    })
                st.dataframe(pd.DataFrame(table_rows), use_container_width=True, height=300)

# ──────────────────────────────────────────────────────────────────────────────
# TAB 5: PROJECT PRESENTATION & VIVA PREPARATION
# ──────────────────────────────────────────────────────────────────────────────
with tab_presentation:
    st.subheader("📑 Project Presentation & Cloud Computing Concepts")
    st.caption("Comprehensive presentation reference based on PROJECT_PRESENTATION.md")

    p1, p2, p3, p4 = st.tabs(["🎯 Architecture & RAFT", "👤 Member Contributions", "⚡ Write Path Flow", "🎓 Viva Q&A"])

    with p1:
        st.markdown("""
        ### MiniRaft: Fault-Tolerant Collaborative Drawing Board
        - **Course:** Cloud Computing (CC)
        - **Tech Stack:** Node.js, Express, WebSocket, Docker, Docker Compose, Nginx, Streamlit
        
        #### Problem Statement:
        Single-server collaborative applications fail catastrophically when their server crashes.
        MiniRaft solves this using the **RAFT Consensus Algorithm**, ensuring:
        - Real-time shared canvas synchronization.
        - Strong consistency for committed operations.
        - Automatic leader election and instantaneous failover (< 1000ms).
        - Zero stroke loss during leader election via Gateway queue buffering.
        
        #### Key RAFT Properties Implemented:
        - **Leader Completeness:** Candidates only win elections if their log is at least as up-to-date as the voter's log.
        - **Log Matching:** `prevLogIndex` and `prevLogTerm` validation before accepting `AppendEntries`.
        - **Commit Safety:** Leaders only commit entries from their current term by counting majority quorum (`matchIndex >= N`).
        - **Idempotency & Deduplication:** Gateway filters duplicate stroke IDs.
        """)

    with p2:
        st.markdown("""
        ### 👥 Team Contribution Mapping

        #### 🌟 Member 2 Focus (Gateway & Realtime Messaging)
        - **Primary File:** `gateway/server.js`
        - **Core Responsibilities:**
          1. **WebSocket Session Management:** Manages client connections and broadcasts committed updates.
          2. **Smart Leader Discovery:** Parallel polling of all replicas; only trusts self-reporting leaders (`role === 'leader'`).
          3. **Write Forwarding & Buffering:** Routes strokes to leader. If an election is in progress, buffers strokes in `strokeQueue` (up to 200 items) and flushes in order once a new leader is elected.
          4. **Zero-Loss Failover:** Re-queues strokes if forwarding fails instead of dropping them.

        #### Member 1 (Core RAFT Consensus)
        - **Primary File:** `replica/raft.js`
        - Owns role transitions (Follower -> Candidate -> Leader), election timers, and `RequestVote` RPCs.

        #### Member 3 (Replica Integration & Sync)
        - **Primary File:** `replica/server.js`
        - Owns `/sync-log`, HTTP RPC bindings, and log catch-up routines.

        #### Member 4 (DevOps & Presentation)
        - Container orchestration, Docker Compose networking, and verification scripts.
        """)

    with p3:
        st.markdown("""
        ### ⚡ The 8-Step Write Path
        1. **User Action:** Client draws a stroke in the HTML5/Streamlit canvas.
        2. **Gateway Ingestion:** Stroke is transmitted via WebSocket to Gateway (`:4000`).
        3. **Leader Forwarding:** Gateway forwards payload via HTTP POST to the current leader's `/stroke` endpoint.
        4. **Log Append:** Leader appends the stroke entry to its local log with `(term, index)`.
        5. **Replication:** Leader sends `AppendEntries` RPC in parallel to all followers.
        6. **Quorum Acknowledgment:** Followers validate `(prevLogIndex, prevLogTerm)` and reply `success: true`.
        7. **Commit Advancement:** Once majority (2 of 3) acknowledges, Leader advances `commitIndex`.
        8. **Broadcast:** Leader invokes Gateway `/commit` callback, which broadcasts the update to all connected clients!
        """)

    with p4:
        st.markdown("### 🎓 Examiner Viva Questions & Answers")
        
        with st.expander("Q1: Why does only the Leader handle write requests?"):
            st.write("A: To enforce a single, total ordering of operations across the distributed system and eliminate conflicting concurrent updates.")

        with st.expander("Q2: Why is a Quorum (majority) required for commits?"):
            st.write("A: In a cluster of N nodes, any two majorities must overlap by at least one node. This ensures that any newly elected leader is guaranteed to contain all previously committed log entries.")

        with st.expander("Q3: What happens if the Leader crashes while a user is drawing?"):
            st.write("A: The Gateway detects the failure on forward error or poll timeout. It buffers the stroke in a FIFO queue. Followers detect missing heartbeats within 500-900ms and elect a new leader. The Gateway discovers the new leader and flushes the queued strokes with zero data loss.")

        with st.expander("Q4: How does a recovering node catch up to the cluster?"):
            st.write("A: Upon startup, the node calls `/sync-log` from the authoritative leader and receives the complete committed log, syncing its state machine before participating in consensus.")

# ──────────────────────────────────────────────────────────────────────────────
# TAB 6: DOCKER MANAGER
# ──────────────────────────────────────────────────────────────────────────────
with tab_docker:
    st.subheader("🐳 Docker Container & Deployment Management")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        if st.button("🚀 Docker Compose Up (Build & Run)", use_container_width=True):
            with st.spinner("Starting containers via docker compose..."):
                ok, out = run_docker_cmd(["docker", "compose", "up", "-d"])
                if ok:
                    st.success("Docker Compose Up executed successfully!")
                else:
                    st.error(f"Error: {out}")
            time.sleep(1.0)
            st.cache_data.clear()
            st.rerun()

    with col_d2:
        if st.button("🔄 Restart All Containers", use_container_width=True):
            with st.spinner("Restarting cluster..."):
                ok, out = run_docker_cmd(["docker", "compose", "restart"])
                if ok:
                    st.success("All containers restarted!")
                else:
                    st.error(f"Error: {out}")
            time.sleep(1.5)
            st.cache_data.clear()
            st.rerun()

    st.markdown("#### Running Docker Containers")
    ok, ps_out = run_docker_cmd(["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"])
    if ok:
        st.code(ps_out, language="text")
    else:
        st.error(f"Failed to fetch docker ps: {ps_out}")

    st.divider()
    st.markdown("#### Live Container Logs")
    selected_container = st.selectbox(
        "Select Container",
        ["gateway", "replica1", "replica2", "replica3", "frontend"]
    )
    tail_lines = st.slider("Lines to view", min_value=10, max_value=100, value=30)
    
    if st.button(f"📄 Fetch Logs for {selected_container}"):
        ok, log_out = run_docker_cmd(["docker", "logs", "--tail", str(tail_lines), selected_container])
        if ok:
            st.code(log_out, language="text")
        else:
            st.error(f"Failed to fetch logs: {log_out}")

# Footer
st.markdown("---")
st.caption("MiniRaft Cloud Computing Project | Running with Streamlit & Docker")
