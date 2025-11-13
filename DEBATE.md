# Protocol-focused debate questions — mentor guide

Purpose: focused technical questions and short answers about how the components in Assignments 1 & 2 communicate across protocols. Use these to probe students' understanding of network protocols, message framing, reliability, security, and performance trade-offs when building their features.

Guidance: For each question, ask students to point to the exact lines/files in their repo (e.g., `bklv-backend/server.py`, `client_api.py`, `optimizations/*`, `bklv-frontend/public/preload.js`). Expect them to describe both their implementation and an alternative approach.

---

1) What transport/protocol did you choose for client↔server communication (HTTP/REST, WebSocket, raw TCP, gRPC)? Why is that appropriate for the features in this assignment?

Answer: The correct explanation identifies the chosen transport (for example: HTTP REST for request/response operations and WebSocket for real-time notifications). Justification should include: simplicity and wide client compatibility (HTTP), lower-latency bidirectional messaging (WebSocket), or binary efficiency and strong typing (gRPC). Students should mention constraints: browser/Electron environment favors HTTP or WebSocket; a raw TCP protocol requires a native client and more firewall/NAT handling.

Pointers: Show `*_api.py` for REST endpoints and any WebSocket server code. Discuss how Electron preload affects allowed transports.

2) How do you frame messages at the application layer? Describe the serialization format and why you chose it (JSON, protobuf, custom binary).

Answer: Preferred: JSON for human-readable simplicity and quick debugging; protobuf/MessagePack for compactness and schema evolution. The answer should mention trade-offs: JSON is verbose but easy to inspect; protobuf reduces bandwidth and enforces schemas but needs codegen.

Test/Check: Point to where requests are encoded/decoded in `client_api.py` and `server_api.py`.

3) How do you handle framing and partial reads for streaming or chunked uploads?

Answer: Correct approaches: use HTTP chunked transfer (Content-Length absent, chunked encoding) or implement application-level framing (length-prefix each chunk or use multipart/form-data). For resumable uploads, track chunk indices and checksums. Students should explain how their server reads bytes safely (looping reads, buffer assembly) and verifies final size/hash.

Implementation hint: show upload endpoints and file write logic; mention using temp files and atomic rename.

4) For long-running or real-time features (updates, heartbeats, notifications) which protocol did you use and how do you ensure timely delivery?

Answer: Use WebSocket or Server-Sent Events for server-to-client pushes; use a keepalive/heartbeat mechanism to detect dead peers. Explain heartbeat interval, timeout, and failure detection policy. Discuss trade-offs: WebSocket keeps a persistent connection (lower latency), but needs reconnection/backoff handling.

Practical check: locate `optimizations/adaptive_heartbeat.py` and explain how heartbeat interval adapts to observed RTT or failures.

5) Explain exactly how you implemented retries and idempotency for operations (e.g., file uploads or metadata updates). How does the server avoid duplicate side-effects on retries?

Answer: Correct solution: make operations idempotent via unique request IDs or object versioning. For uploads, use an upload-id + chunk indexes, or compute client-side hash and treat repeated upload with same hash as dedup. On the server, use dedup keys and check if an operation is already applied before applying it again.

Code pointers: show where request IDs or content hashes are created/checked.

6) How do you do error reporting in the protocol? Describe status codes, error payloads, and retry guidance encoded in responses.

Answer: Use HTTP status codes for REST (200/201, 4xx for client errors, 5xx for server errors); include a JSON error object with code, message, and optionally retry_after. For custom protocols, define numeric error codes and human-friendly messages. Good practice: include correlation IDs to trace the failing request.

7) How do you secure the transport? Where do you apply TLS, authentication headers, and token validation?

Answer: Use TLS for all client-server traffic to ensure confidentiality/integrity. Apply token-based authentication (Bearer tokens or session cookies) validated on each request. For Electron apps, use a secure preload and avoid exposing raw tokens to the renderer process. Ensure server verifies token signatures and expirations and applies proper scoping/authorization.

Checklist: point to where TLS is configured (if in Docker or reverse proxy) and where token validation happens in server code.

8) How do you handle CORS and origin checks for the frontend (Electron vs. browser) when using REST APIs?

Answer: Electron typically runs a local file/packaged renderer and can avoid CORS by using the preload bridge; when running in a browser, the server must set CORS headers (Access-Control-Allow-Origin) appropriately or use same-origin. Preload script should offer a narrow API to the renderer and call the server from the main/preload layer rather than allowing direct cross-origin XHR from the page.

9) If you used WebSocket or a persistent TCP connection, how do you handle reconnection and exponential backoff? Describe a safe reconnection algorithm.

Answer: Use exponential backoff with jitter (e.g., base delay 500ms, multiply by 2 up to a cap, add random jitter). On reconnect, reauthenticate and resync state (e.g., request missed messages using last-seen sequence number). Avoid synchronized reconnection storms by adding randomization.

10) Describe how you implemented message ordering and delivery guarantees (at-most-once, at-least-once, exactly-once). Which guarantees did you pick and why?

Answer: Most simple systems use at-most-once (best-effort) or at-least-once with deduplication. Exactly-once is expensive and typically implemented by idempotent operations + dedup keys. Students should state their chosen guarantee and how they ensured it (sequence numbers + ack receipts, or request IDs + server-side dedup store).

11) When transferring large files, how do you avoid head-of-line blocking and enable parallelism? Explain chunking, pipelining, or multipart strategies.

Answer: Use chunked uploads with independent chunk IDs and allow parallel chunk uploading. Server assembles chunks and verifies the final manifest hash. Pipelining small control messages and uploading chunks in parallel improves throughput and avoids a single slow chunk blocking the rest.

12) How does the client detect partial/corrupted transfers? What checksums or integrity checks did you implement?

Answer: Use per-chunk checksums (e.g., SHA-256) and an overall file hash. After upload, server validates chunk checksums and final hash. If mismatch, request retransmission for affected chunks.

13) How do you design API versioning and backward compatibility for protocol changes?

Answer: Include a version in endpoint URLs (e.g., /api/v1/) or in request headers. Use additive changes in message schemas, deprecate fields, and maintain compatibility by ignoring unknown fields. For breaking changes, introduce a new major version and support old versions for a migration window.

14) Describe how you would instrument and trace requests across services to measure latency and diagnose failures.

Answer: Add correlation IDs to each client request (e.g., X-Request-ID). Propagate this ID across internal calls and include it in logs. Optionally integrate distributed tracing (OpenTelemetry) to measure spans for client send, server receive, processing, DB write, and response. Collect metrics (histograms for latencies) and error rates.

15) What backpressure or flow-control mechanisms exist between producer and consumer in your protocol? How do you prevent the server from being overwhelmed by many clients sending large payloads?

Answer: Use HTTP request size limits, per-connection limits, and rate limiting. For streaming protocols, implement window-based flow control or application-level credits so the producer only sends what the consumer can accept. For uploads, accept only a fixed number of concurrent uploads per user and queue extra requests.

16) How do you design graceful shutdown so in-flight requests and uploads are handled safely?

Answer: On shutdown, stop accepting new connections, notify clients (if possible), let in-flight requests finish or checkpoint state (e.g., mark partially received chunks), and persist any volatile state. Use a timeout after which remaining operations are canceled and retried on the next start.

17) When using a message broker (e.g., for notifications), what QoS model and durability settings would you choose for notifications vs. critical events (like ownership transfer)?

Answer: Use at-most-once or best-effort for ephemeral notifications (e.g., presence updates), and at-least-once with durable storage for critical events. Configure persistence, acknowledgements, and TTL as appropriate.

18) How does NAT/firewall traversal affect your chosen protocol? Which transports are more NAT-friendly, and what workarounds exist for P2P features?

Answer: HTTP(S) and WebSocket over TLS are NAT/firewall-friendly since they use outbound TCP/TLS connections. Raw TCP servers behind NAT require port forwarding. For P2P, use STUN/TURN/ICE to handle NAT traversal or use a relay server.

19) How do you plan testing for protocol correctness? Provide two concrete tests that verify critical properties.

Answer: Test 1: Idempotent retry test — send the same request twice with same request ID and verify single side-effect. Test 2: Chunk loss/retransmit test — simulate dropped chunk(s) and ensure client resends only missing chunks and server assembles correct final hash. Both should be automated integration tests.

20) For performance tuning, which three protocol-level knobs would you measure and tune first for improved throughput and latency?

Answer: (1) Message/chunk size (to balance overhead vs. latency); (2) concurrency (how many parallel uploads per client or max outstanding requests); (3) keepalive/heartbeat intervals and retransmission timeouts. Measure and tune these with controlled benchmarks.

---

Quick facilitation checklist
- Ask students to show the exact code handling: framing, reading loop, checksum verification, and retry logic.
- Require that they describe: transport choice, message serialization, integrity checks, and retry/idempotency strategy.
- If any of these are missing, ask for a short design sketch and one failing test that proves the current behavior.

If you'd like, I can convert these into a printable checklist or create a short set of automated tests that validate basic protocol properties using small Python test scripts.
