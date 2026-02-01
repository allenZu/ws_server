# WebSocket 转发服务

这个服务用于三方角色的 WebSocket 转发：

- **B 端**：携带 token 连接后，可向 **C 端**发送 command 指令。
- **A 端**：可以向 **B 端**发送消息，**B 端**也可以向 **A 端**回复消息。
- **C 端**：接收 **B 端**的 command，并在 **B 端**断开时收到通知。

## 运行

```bash
pip install websockets
python server.py
```

环境变量：

- `B_TOKENS`（默认：`demo-token`）：B 端允许的 token，逗号分隔。
- `WS_HOST`（默认：`0.0.0.0`）
- `WS_PORT`（默认：`8765`）

## 协议约定

所有客户端连接后第一条消息必须注册：

```json
{"type":"register","role":"a"}
```

B 端注册：

```json
{"type":"register","role":"b","token":"demo-token"}
```

C 端注册：

```json
{"type":"register","role":"c"}
```

### B -> C command

```json
{"type":"command","command":"restart"}
```

### A <-> B 消息互发

```json
{"type":"message","to":"b","payload":"hello"}
```

B 回复 A：

```json
{"type":"message","to":"a","payload":"hi"}
```

### C 端通知

B 端连接成功：

```json
{"type":"b_connected","token":"demo-token"}
```

B 端断开：

```json
{"type":"b_disconnected","token":"demo-token"}
```

## B 端示例客户端

```bash
python b_client.py --token demo-token --command restart --message "hello a"
```

## 通讯安全建议

当前示例是演示用途，生产环境建议至少做到：

1. **启用 TLS（wss）**：通过反向代理（例如 Nginx）或直接在服务层接入 TLS，避免明文传输。
2. **强 Token 签发与轮换**：B 端 token 应为高强度随机字符串，定期轮换，必要时带过期时间。
3. **来源限制**：通过 IP 白名单、反向代理鉴权、或 mTLS 限制可连接的客户端来源。
4. **连接数与速率限制**：避免被滥用或 DoS。
5. **业务层鉴权**：对于 message/command 可加入签名、时间戳、防重放等机制。
