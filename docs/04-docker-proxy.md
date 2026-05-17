# Docker Socket Proxy

## Purpose

Security boundary between Node-RED and the Docker daemon. Translates HTTP requests to Docker API calls, enabling fine-grained permission control without exposing the full Docker socket.

## Configuration

**Image:** `tecnativa/docker-socket-proxy`
**Container:** `docker_api_proxy`
**Internal Port:** 2375 (no external exposure)
**Memory:** 32 MB

### Volume Mount

```
/var/run/docker.sock:/var/run/docker.sock:ro
```

Socket mounted **read-only**. The proxy itself enforces which API endpoints are accessible.

### Environment Flags

| Flag | Value | Purpose |
|------|-------|---------|
| `CONTAINERS` | 1 | List/manage containers |
| `POST` | 1 | Create containers and networks |
| `DELETE` | 1 | Remove containers (kill switch) |
| `NETWORKS` | 1 | Connect containers to `iot_infralab_net` |
| `IMAGES` | 1 | Verify `general-iot-sensor` image exists |
| `EXEC` | 1 | Execute commands inside containers |
| `INFO` | 1 | Telegraf queries Docker daemon info |
| `GET` | 1 | Read-only queries |

## Why Proxy Over Direct Socket Mount

| Approach | Risk Level | Rationale |
|----------|-----------|-----------|
| **Socket proxy** (chosen) | Low | Enables only specific API verbs. POST but not DELETE can be disabled independently. |
| Direct `/var/run/docker.sock` mount | Critical | Gives Node-RED root-equivalent Docker daemon access. No filtering possible. |
| Unix socket in volume | High | Any container with socket access can control the daemon completely. |

The proxy allows Node-RED to create/start/stop/remove containers and exec commands without giving it control over images, volumes, or other sensitive API surfaces.

## Security Considerations

- **No external ports** — proxy is completely hidden from host network
- **Read-only socket mount** — proxy cannot modify Docker socket
- **Delete enabled** — intentional for kill switch demonstration; can be disabled by removing `DELETE=1`
- **All communication is internal** to `iot_infralab_net`

## Consumers

| Service | Purpose |
|---------|---------|
| Node-RED | Container lifecycle, exec commands, network management |
| Telegraf | Docker stats collection (CPU, memory, network per container) |

## Related

- Node-RED Docker integration: [03-nodered-automation.md](03-nodered-automation.md)
- Security model: [15-security-model.md](15-security-model.md)
