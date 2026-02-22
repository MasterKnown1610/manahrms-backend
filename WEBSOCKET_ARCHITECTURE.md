# ManaHRMS WebSocket Real-time Architecture

## Overview

Production-grade WebSocket architecture for multi-tenant SaaS HRMS platform enabling real-time updates for attendance, tasks, and employee activities.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
│  (Web Dashboard / Mobile App - React Native)                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ WebSocket (wss://)
                       │ JWT Authentication
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI WebSocket Server                        │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         Connection Manager                          │    │
│  │  - Tenant-based room isolation                     │    │
│  │  - Role-based routing                              │    │
│  │  - User-specific channels                          │    │
│  └──────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────┐    │
│  │         Event Handlers                               │    │
│  │  - Attendance events                                 │    │
│  │  - Task events                                       │    │
│  │  - Activity events                                   │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Redis Pub/Sub
                       │ (Horizontal Scaling)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    Redis Server                             │
│  Channels: tenant:{id}, tenant:{id}:role:{role}            │
└─────────────────────────────────────────────────────────────┘
                       │
                       │ Event Triggers
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              Business Logic Services                        │
│  - AttendanceService                                         │
│  - TaskService                                              │
│  - EmployeeService                                          │
└─────────────────────────────────────────────────────────────┘
```

## Connection Flow

### 1. WebSocket Connection

**Endpoint:** `wss://api.manahrms.com/ws?token=JWT_TOKEN`

**Authentication:**
- JWT token passed as query parameter
- Token validated on connection
- User and company status verified

**On Successful Connection:**
```json
{
  "event": "CONNECTED",
  "tenant_id": "12",
  "message": "Connected to ManaHRMS WebSocket",
  "connection_id": "12:123:1234567890.123",
  "subscription_plan": "pro",
  "rooms": [
    "tenant:12",
    "tenant:12:role:ADMIN",
    "tenant:12:user:123"
  ],
  "timestamp": "2026-02-22T13:00:00Z"
}
```

### 2. Room Assignment

Each connection automatically joins:
- **Tenant Room**: `tenant:{tenant_id}` - All users in company
- **Role Room**: `tenant:{tenant_id}:role:{role}` - Users with same role
- **User Room**: `tenant:{tenant_id}:user:{user_id}` - Personal notifications

## Event Types

### 1. ATTENDANCE_MARKED

**Triggered:** When employee punches in/out

**Payload:**
```json
{
  "event": "ATTENDANCE_MARKED",
  "tenant_id": "12",
  "employee_id": "123",
  "employee_name": "Sai Pranathi",
  "action": "LOGIN",
  "timestamp": "2026-02-22T09:00:00Z",
  "message": "Sai Pranathi marked attendance (LOGIN)",
  "attendance_summary": {
    "total_present": 15,
    "present_today": 8
  }
}
```

**Broadcast To:**
- `tenant:{tenant_id}:role:ADMIN`
- `tenant:{tenant_id}:role:HR`
- `tenant:{tenant_id}:role:MANAGER`

### 2. TASK_STATUS_UPDATED

**Triggered:** When task status changes

**Payload:**
```json
{
  "event": "TASK_STATUS_UPDATED",
  "tenant_id": "12",
  "task_id": "TASK123",
  "task_name": "Attendance Tracking",
  "employee_name": "Sai Pranathi",
  "new_status": "IN_PROGRESS",
  "old_status": "PENDING",
  "timestamp": "2026-02-22T10:30:00Z",
  "message": "Sai Pranathi updated task 'Attendance Tracking' to IN_PROGRESS"
}
```

**Broadcast To:**
- Assigned Manager
- Admin room
- Task creator personal room

### 3. TASK_ASSIGNED

**Triggered:** When admin assigns task to employee

**Payload:**
```json
{
  "event": "TASK_ASSIGNED",
  "tenant_id": "12",
  "task_id": "TASK555",
  "task_name": "UI Design",
  "assigned_to": "123",
  "assigned_by": "456",
  "assigned_by_name": "Admin Name",
  "timestamp": "2026-02-22T11:00:00Z",
  "message": "New task assigned: UI Design"
}
```

**Broadcast To:**
- `tenant:{tenant_id}:user:{assigned_to}` (Personal notification)

### 4. EMPLOYEE_ACTIVITY

**Triggered:** General employee activities

**Payload:**
```json
{
  "event": "EMPLOYEE_ACTIVITY",
  "tenant_id": "12",
  "employee_id": "123",
  "employee_name": "Sai Pranathi",
  "action": "UPDATED_PROFILE",
  "details": {
    "field": "email",
    "old_value": "old@example.com",
    "new_value": "new@example.com"
  },
  "timestamp": "2026-02-22T12:00:00Z"
}
```

**Broadcast To:**
- Admin room (always)
- Enterprise plan subscribers only

### 5. DASHBOARD_UPDATE

**Triggered:** Dashboard statistics updates

**Payload:**
```json
{
  "event": "DASHBOARD_UPDATE",
  "tenant_id": "12",
  "update_type": "ATTENDANCE_STATS",
  "data": {
    "total_employees": 50,
    "present_today": 45,
    "absent_today": 5
  },
  "timestamp": "2026-02-22T13:00:00Z"
}
```

**Broadcast To:**
- Admin room
- HR room

## Subscription Plan Feature Gating

### Basic Plan
- ✅ Attendance notifications only

### Pro Plan
- ✅ Attendance notifications
- ✅ Task status updates
- ✅ Task assignment notifications

### Enterprise Plan
- ✅ All Pro features
- ✅ Employee activity feed
- ✅ Real-time dashboard analytics
- ✅ Advanced activity tracking

## Implementation

### Backend Integration

**Example: Emit attendance event**
```python
from app.api.v1.services.websocket_service import websocket_service

# In attendance service after punch in
await websocket_service.emit_attendance_marked(
    db=db,
    tenant_id=company_id,
    employee_id=employee_id,
    employee_name=employee.full_name,
    action="LOGIN",
    attendance_summary={"total_present": 15}
)
```

**Example: Emit task assignment**
```python
await websocket_service.emit_task_assigned(
    db=db,
    tenant_id=company_id,
    task_id=task.id,
    task_name=task.title,
    assigned_to=employee_id,
    assigned_by=current_user.id,
    assigned_by_name=current_user.full_name
)
```

### Frontend Integration (React Native Example)

```javascript
import { useEffect, useRef } from 'react';

const useWebSocket = (token) => {
  const ws = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = () => {
    try {
      const wsUrl = `wss://api.manahrms.com/ws?token=${token}`;
      ws.current = new WebSocket(wsUrl);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        reconnectAttempts.current = 0;
      };

      ws.current.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        attemptReconnect();
      };
    } catch (error) {
      console.error('WebSocket connection error:', error);
      attemptReconnect();
    }
  };

  const attemptReconnect = () => {
    if (reconnectAttempts.current < maxReconnectAttempts) {
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
      reconnectAttempts.current++;
      
      reconnectTimeoutRef.current = setTimeout(() => {
        console.log(`Reconnecting... Attempt ${reconnectAttempts.current}`);
        connect();
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
      // Fallback to REST polling
    }
  };

  const handleWebSocketMessage = (message) => {
    switch (message.event) {
      case 'ATTENDANCE_MARKED':
        showToast(`${message.employee_name} marked attendance (${message.action})`);
        updateAttendanceDashboard(message.attendance_summary);
        break;
      
      case 'TASK_STATUS_UPDATED':
        showToast(`${message.employee_name} updated task '${message.task_name}' to ${message.new_status}`);
        updateTaskStatus(message.task_id, message.new_status);
        break;
      
      case 'TASK_ASSIGNED':
        showToast(`New task assigned: ${message.task_name}`);
        playNotificationSound();
        refreshTaskList();
        break;
      
      case 'EMPLOYEE_ACTIVITY':
        if (subscriptionPlan === 'enterprise') {
          updateActivityFeed(message);
        }
        break;
      
      case 'DASHBOARD_UPDATE':
        updateDashboardStats(message.data);
        break;
      
      case 'PING':
        // Respond to ping
        ws.current?.send(JSON.stringify({ event: 'PONG' }));
        break;
      
      default:
        console.log('Unknown event:', message.event);
    }
  };

  useEffect(() => {
    if (token) {
      connect();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [token]);

  return ws.current;
};

export default useWebSocket;
```

## Security

### Authentication
- JWT token validated on every connection
- Token expiration checked
- User and company active status verified

### Rate Limiting
- 100 messages per 60 seconds per connection
- Automatic disconnection on limit exceeded

### Tenant Isolation
- Strict tenant-based room isolation
- No cross-tenant message broadcasting
- Role-based access control

### Encryption
- WSS (WebSocket Secure) required in production
- Sensitive payloads can be encrypted
- JWT tokens in query params (consider header for production)

## Scalability

### Horizontal Scaling
- Redis Pub/Sub enables multiple server instances
- Each instance subscribes to tenant channels
- Messages broadcast across all instances

### Connection Limits
- Supports 10,000+ concurrent connections per instance
- Connection pooling and resource management
- Automatic cleanup of disconnected clients

### Performance
- Heartbeat/ping-pong every 30 seconds
- Connection timeout: 60 seconds
- Efficient room-based broadcasting

## Monitoring

### Metrics to Track
- Active connections per tenant
- Messages per second
- Event type distribution
- Connection duration
- Reconnection rate

### Logging
- Connection/disconnection events
- Event broadcasts
- Error tracking
- Rate limit violations

## Error Handling

### Connection Errors
- Automatic reconnection with exponential backoff
- Fallback to REST polling if WebSocket unavailable
- Graceful degradation

### Message Errors
- Invalid JSON handling
- Unknown event types
- Rate limit exceeded
- Internal server errors

## Testing

### Test Scenarios
1. Multiple users from same tenant
2. Cross-tenant isolation
3. Role-based message routing
4. Subscription plan feature gating
5. Reconnection handling
6. Rate limiting
7. Redis Pub/Sub across instances

## Configuration

### Environment Variables
```env
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_password
REDIS_DB=0
```

### Redis Setup
```bash
# Install Redis
# Ubuntu/Debian
sudo apt-get install redis-server

# macOS
brew install redis

# Start Redis
redis-server
```

## Deployment

### Production Checklist
- [ ] Enable WSS (WebSocket Secure)
- [ ] Configure Redis for high availability
- [ ] Set up connection monitoring
- [ ] Configure rate limiting
- [ ] Enable logging and metrics
- [ ] Test horizontal scaling
- [ ] Set up failover mechanisms
- [ ] Configure load balancer for WebSocket

### Load Balancer Configuration
- Sticky sessions required for WebSocket
- Health checks for WebSocket endpoints
- Timeout configuration (longer than 60s)

## API Reference

### WebSocket Endpoint
```
wss://api.manahrms.com/ws?token=JWT_TOKEN
```

### Message Format
```json
{
  "event": "EVENT_TYPE",
  "tenant_id": "string",
  "timestamp": "ISO8601",
  "data": {},
  "message": "Human readable message"
}
```

### Client Messages
- `PING`: Client ping (server responds with PONG)
- `PONG`: Response to server ping

### Server Messages
- `CONNECTED`: Connection established
- `PING`: Server ping (client should respond with PONG)
- `PONG`: Response to client ping
- `ERROR`: Error message
- Event-specific messages (ATTENDANCE_MARKED, etc.)

## Best Practices

1. **Always use WSS in production**
2. **Implement reconnection logic with exponential backoff**
3. **Handle connection state gracefully**
4. **Validate all incoming messages**
5. **Monitor connection health**
6. **Use Redis for multi-instance deployments**
7. **Implement proper error handling**
8. **Respect rate limits**
9. **Log important events**
10. **Test failover scenarios**

