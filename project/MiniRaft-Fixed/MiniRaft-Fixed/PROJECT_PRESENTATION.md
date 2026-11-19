# MiniRaft Project Presentation

## 1. Title Slide

Project: MiniRaft - Fault-Tolerant Collaborative Drawing Board  
Course: Cloud Computing (CC)  
Team Size: 4  
Tech Stack: Node.js, Express, WebSocket, Docker, Docker Compose, Nginx

---

## 2. Problem Statement

Traditional single-server collaborative apps fail when the server crashes.

We wanted to build a system where:
- Multiple users can draw together in real time.
- Data remains consistent across servers.
- The system continues working even if one node fails.

---

## 3. Objective

Build a distributed, fault-tolerant whiteboard using RAFT consensus.

Key objectives:
- Real-time collaboration.
- Strong consistency for drawing operations.
- Leader election and automatic failover.
- Containerized deployment for easy cloud-style execution.

---

## 4. What Is RAFT (Simple)

RAFT is a consensus algorithm used by distributed systems to agree on the same sequence of operations.

In simple terms:
- One node is Leader.
- Others are Followers.
- Leader accepts writes and replicates to followers.
- Entry is committed only after majority acknowledgment.

---

## 5. Why RAFT In This Project

RAFT solves the core distributed problems:
- Prevents data mismatch between replicas.
- Avoids split-brain writes from multiple leaders.
- Supports recovery after node failure.
- Guarantees operation order consistency.

---

## 6. System Architecture

Flow:
Browser Clients -> Gateway -> RAFT Replicas (3 nodes)

Components:
- Frontend: drawing canvas UI.
- Gateway: WebSocket and routing layer.
- Replica1/2/3: RAFT consensus nodes.

Ports:
- Frontend: 3000
- Gateway: 4000
- Replicas: 5001, 5002, 5003

---

## 7. Service Responsibilities

Frontend:
- Captures draw/clear actions.
- Sends actions over WebSocket.
- Renders committed updates.

Gateway:
- Discovers current leader.
- Forwards write requests to leader.
- Queues requests during leader transition.

Replicas:
- Run elections.
- Replicate logs.
- Commit on majority.

---

## 8. RAFT Roles

Follower:
- Default role.
- Responds to leader heartbeats and RPCs.

Candidate:
- Starts election when timeout occurs.
- Requests votes from peers.

Leader:
- Accepts writes.
- Replicates entries.
- Sends heartbeats.

---

## 9. RAFT Core Terms

Term:
- Logical epoch number for elections.

Log Entry:
- One operation in order (in this app, one stroke or clear command).

Commit Index:
- Highest log entry known to be safely committed.

Quorum:
- Majority of nodes (in 3 nodes, quorum = 2).

---

## 10. Write Path (How One Stroke Is Saved)

1. User draws stroke in frontend.
2. Frontend sends stroke to gateway.
3. Gateway forwards to current leader.
4. Leader appends stroke to its log.
5. Leader sends AppendEntries to followers.
6. Followers acknowledge after validation.
7. Leader commits when majority confirms.
8. Committed update is sent back to clients.

---

## 11. Read and State Sync Behavior

- New clients connect to gateway.
- Gateway sends current committed strokes.
- Clients render same canvas state.
- Replicas keep logs aligned via RAFT replication.

---

## 12. Failure Handling

Case A: Follower fails
- Cluster still has majority (2/3).
- System continues accepting writes.

Case B: Leader fails
- Followers start election.
- New leader selected in next term.
- Gateway detects new leader and forwards there.

Case C: Failed node rejoins
- Rejoining follower catches up from leader log.

---

## 13. Correctness Guarantees Implemented

- Leader completeness through vote log up-to-date checks.
- Log matching via prevLogIndex and prevLogTerm validation.
- Commit safety using majority and term-aware commit advancement.
- Protection against committed entry overwrite.
- Serialized propose path to avoid race conditions.

---

## 14. Cloud Computing Concepts Covered

- Distributed systems design.
- Consensus and coordination.
- Fault tolerance and failover.
- High availability with majority nodes.
- Stateless gateway plus replicated state machines.
- Containerization and orchestration.
- Service networking in isolated Docker network.

---

## 15. DevOps and Deployment

Deployment model:
- Multi-container setup using docker-compose.

Benefits:
- One-command startup.
- Reproducible environment.
- Clear service separation.

Run command:
```bash
docker compose up --build
```

---

## 16. Monitoring and Verification Endpoints

Frontend:
- http://localhost:3000

Gateway status:
- http://localhost:4000/status

Replica status:
- http://localhost:5001/status
- http://localhost:5002/status
- http://localhost:5003/status

Replica logs:
- /log endpoints to verify replicated committed strokes.

---

## 17. Team Contribution Mapping

Member 1:
- Core RAFT algorithm and replica behavior.

Member 2:
- Gateway and real-time messaging path.

Member 3:
- Replica service integration and synchronization support.

Member 4:
- DevOps, testing workflows, and project documentation.

---

## 17A. Detailed Focus: Member 2 (Gateway and Realtime Messaging)

Member 2 owns the complete client-to-cluster communication layer.

Why this role is critical:
- Users never talk to replicas directly.
- Gateway hides leader changes from frontend users.
- Realtime behavior, low latency, and user experience mostly depend on this layer.

Primary file ownership:
- gateway/server.js

---

## 17B. Member 2 Responsibilities (Technical)

1. WebSocket session management
- Accept client connections.
- Track connected clients.
- Send initial canvas state on connect.

2. Realtime message handling
- Parse draw and clear commands from browser.
- Return ACK when operation is accepted.
- Return queued response when leader is temporarily unavailable.

3. Leader discovery and tracking
- Poll replica status endpoints.
- Accept leader only when node self-reports role=leader.
- Maintain currentLeaderId and currentLeaderUrl.

4. Write forwarding
- Forward stroke and clear requests to leader replica.
- Handle HTTP errors and stale-leader cases.
- Retry using leader hints when available.

5. Reliability and failover behavior
- Maintain bounded queue for temporary buffering.
- Flush queued operations after new leader is found.
- Prevent stroke loss during election windows.

6. Cluster status broadcasting
- Push term and leader updates to all connected clients.
- Keep frontend UI synchronized with backend topology.

---

## 17C. Member 2 Data Flow (Demo Explanation)

1. Client draws on canvas.
2. Frontend sends stroke to gateway via WebSocket.
3. Gateway checks leader availability.
4. If leader exists, gateway forwards to leader /stroke endpoint.
5. If no leader (during election), gateway queues request.
6. Once leader is discovered, queue is flushed in order.
7. ACK/queued state is sent back to frontend client.

Key point to tell examiner:
- Gateway is a smart communication coordinator, not just a proxy.

---

## 17D. Member 2 Failure Handling Cases

Case 1: Old leader is dead, gateway still has stale leader URL
- On forwarding failure, gateway clears leader state immediately.
- Triggers fresh leader discovery.
- Request is queued instead of dropped.

Case 2: Replica replies 503 with leader hint
- Gateway reads leaderId hint.
- Attempts forwarding to hinted leader directly.
- If that also fails, discovery loop continues.

Case 3: Queue flush interruption
- Failed queue item is put back at queue front.
- Preserves ordering and avoids silent data loss.

---

## 17E. Member 2 Viva-Ready Talking Points

Use these exact lines in demo:

- I implemented the gateway as a realtime coordination layer between frontend and RAFT replicas.
- My logic handles leader discovery, request forwarding, ACK/queue responses, and failover recovery.
- During leader election, client writes are buffered and replayed after new leader selection.
- This design improves user experience because clients continue drawing without manually switching servers.
- My contribution ensures high availability at the communication layer while preserving consistency guarantees from RAFT.

---

## 17F. Member 2 Evaluation Checklist (What To Show)

- Open two browser windows and draw simultaneously.
- Show that both receive updates in realtime.
- Stop current leader container and continue drawing.
- Explain that gateway queues writes briefly and re-forwards after election.
- Show gateway status endpoint and new leader ID.

This proves Member 2 contribution in reliability, realtime messaging, and user-facing continuity.

---

## 18. Demo Script (Step-by-Step)

1. Start all services using Docker Compose.
2. Open two browser windows and draw collaboratively.
3. Show gateway and replica status endpoints.
4. Stop one follower and continue drawing.
5. Stop current leader and show recovery after election.
6. Restart stopped node and show catch-up.
7. Conclude with consistency and fault-tolerance summary.

---

## 19. Expected Results

- Real-time shared drawing across users.
- Same committed state on all healthy replicas.
- Continued operation under single-node failure.
- Automatic leader failover without manual intervention.

---

## 20. Limitations

- In-memory log only (no durable disk persistence yet).
- Local/LAN deployment focus, not internet-hardened.
- No authentication or ACL for production use.

---

## 21. Future Improvements

- Persistent storage (snapshotting + WAL).
- Kubernetes deployment with health probes.
- TLS and authentication for secure access.
- Metrics dashboard (Prometheus + Grafana).
- More replicas and partition simulation tests.

---

## 22. Viva Questions and Short Answers

Q: Why only leader handles writes?  
A: To maintain one global write order and avoid conflicting updates.

Q: Why majority commit?  
A: Majority ensures committed data survives node failures.

Q: What happens if leader crashes?  
A: Followers elect a new leader and continue operations.

Q: Is this strongly consistent?  
A: Yes for committed writes, because RAFT enforces ordered majority agreement.

Q: Why Docker for this project?  
A: It simplifies multi-service deployment and makes execution reproducible.

---

## 23. Conclusion

MiniRaft demonstrates a practical cloud computing system where distributed consensus, failover, and real-time collaboration are implemented together.

Final takeaway:
- This is not just a drawing app.
- It is a fault-tolerant distributed application built on RAFT principles.
