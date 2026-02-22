# Frontend WebSocket Implementation Prompt for ManaHRMS

## Objective
Implement a production-grade WebSocket client for ManaHRMS frontend (React Native/React) that connects to the real-time WebSocket server, handles all event types, manages reconnections, and provides a seamless real-time experience.

---

## Connection Details

### WebSocket Endpoint
```
wss://api.manahrms.com/ws?token=JWT_TOKEN
```

**Protocol:** WebSocket Secure (WSS) for production, WS for development
**Authentication:** JWT token passed as query parameter
**Connection Type:** Persistent bidirectional connection

---

## Implementation Requirements

### 1. WebSocket Connection Manager

Create a WebSocket connection manager that:

- **Connects** using the JWT token from your authentication store
- **Handles connection lifecycle:** connect, disconnect, reconnect
- **Manages connection state:** connecting, connected, disconnected, error
- **Implements auto-reconnect** with exponential backoff strategy:
  - Initial delay: 1 second
  - Max delay: 30 seconds
  - Max attempts: 5 attempts before fallback
  - Reset attempts on successful connection
- **Stores connection instance** for message sending
- **Provides connection status** to components

### 2. Message Handling

Implement handlers for all event types:

#### A. CONNECTED Event
- **When received:** Immediately after successful connection
- **Action:** 
  - Update connection status to "connected"
  - Store connection metadata (subscription_plan, rooms)
  - Reset reconnection attempts
  - Show success notification (optional)

#### B. ATTENDANCE_MARKED Event
- **When received:** When any employee marks attendance (punch in/out)
- **Payload contains:**
  - `employee_name`: Name of employee
  - `action`: "LOGIN" or "LOGOUT"
  - `attendance_summary`: Updated attendance statistics
- **Actions:**
  - Show toast notification: "{employee_name} marked attendance ({action})"
  - Update attendance dashboard if visible
  - Refresh attendance list if on attendance screen
  - Play notification sound (optional)
  - Update attendance counters in real-time

#### C. TASK_STATUS_UPDATED Event
- **When received:** When task status is changed
- **Payload contains:**
  - `task_id`: ID of updated task
  - `task_name`: Name of the task
  - `employee_name`: Who updated it
  - `new_status`: New status (PENDING, IN_PROGRESS, COMPLETED, etc.)
  - `old_status`: Previous status
- **Actions:**
  - Show toast: "{employee_name} updated task '{task_name}' to {new_status}"
  - Update task in task list without refresh
  - If task detail view is open for this task, update it
  - Refresh task statistics/counters
  - Highlight the updated task in the list

#### D. TASK_ASSIGNED Event
- **When received:** When a new task is assigned to you
- **Payload contains:**
  - `task_id`: ID of assigned task
  - `task_name`: Name of the task
  - `assigned_by_name`: Who assigned it
- **Actions:**
  - Show prominent notification: "New task assigned: {task_name}"
  - Play notification sound
  - Show badge on tasks icon/menu
  - If on tasks screen, refresh task list
  - Navigate to task detail if user taps notification
  - Update task counter in navigation

#### E. EMPLOYEE_ACTIVITY Event
- **When received:** General employee activities (only for Enterprise plan)
- **Payload contains:**
  - `employee_name`: Employee who performed action
  - `action`: Type of activity (UPDATED_PROFILE, CREATED_TASK, etc.)
  - `details`: Additional activity details
- **Actions:**
  - Check subscription plan before showing
  - If Enterprise: Show in activity feed
  - Update activity timeline
  - Log to activity history

#### F. DASHBOARD_UPDATE Event
- **When received:** Dashboard statistics updates
- **Payload contains:**
  - `update_type`: Type of update (ATTENDANCE_STATS, TASK_STATS, etc.)
  - `data`: Updated statistics object
- **Actions:**
  - Update dashboard counters in real-time
  - Animate number changes
  - Refresh charts/graphs if visible
  - No toast notification (silent update)

#### G. PING/PONG Events
- **PING from server:** Respond immediately with PONG
- **PONG from server:** Connection is alive, reset timeout
- **Implementation:**
  - Handle ping/pong automatically
  - Use for connection health monitoring
  - Trigger reconnection if no pong received within timeout

#### H. ERROR Event
- **When received:** Server sends error message
- **Payload contains:**
  - `error_code`: Machine-readable error code
  - `message`: Human-readable error message
- **Actions:**
  - Log error for debugging
  - Show error notification if critical
  - Handle specific error codes:
    - `RATE_LIMIT_EXCEEDED`: Slow down message sending
    - `INVALID_TOKEN`: Re-authenticate user
    - `INTERNAL_ERROR`: Log and continue

### 3. Reconnection Strategy

Implement robust reconnection logic:

**Exponential Backoff:**
- Attempt 1: Wait 1 second
- Attempt 2: Wait 2 seconds
- Attempt 3: Wait 4 seconds
- Attempt 4: Wait 8 seconds
- Attempt 5: Wait 16 seconds
- Max: 30 seconds between attempts

**Reconnection Triggers:**
- Connection closed unexpectedly
- Network error
- No ping/pong response for 60+ seconds
- WebSocket error

**Fallback Strategy:**
- After 5 failed attempts, switch to REST polling
- Poll every 30 seconds for updates
- Retry WebSocket connection every 5 minutes
- Resume WebSocket when connection succeeds

**User Experience:**
- Show "Reconnecting..." indicator
- Don't block UI during reconnection
- Queue messages if needed
- Restore connection state on reconnect

### 4. State Management

**Connection State:**
- `connecting`: Initial connection attempt
- `connected`: Successfully connected
- `disconnected`: Not connected
- `reconnecting`: Attempting to reconnect
- `error`: Connection error occurred

**Store in:**
- Redux/Zustand store (if using state management)
- React Context (if using Context API)
- Local component state (for simple apps)

**Expose:**
- Connection status to all components
- Connection instance for sending messages
- Event handlers registration

### 5. UI/UX Implementation

**Connection Indicator:**
- Show connection status in header/navigation
- Green dot: Connected
- Yellow dot: Reconnecting
- Red dot: Disconnected
- Animated pulse during connection

**Notifications:**
- Toast notifications for important events
- Non-intrusive for dashboard updates
- Prominent for task assignments
- Sound notification for critical events (optional)

**Real-time Updates:**
- Update lists without full refresh
- Animate changes (fade in, highlight)
- Show "live" indicator
- Update counters smoothly

**Error Handling:**
- Show user-friendly error messages
- Don't expose technical details
- Provide retry options
- Log errors for debugging

### 6. Performance Optimization

**Message Queue:**
- Queue messages if connection is down
- Send queued messages on reconnect
- Limit queue size to prevent memory issues

**Event Debouncing:**
- Debounce rapid dashboard updates
- Batch similar events
- Throttle UI updates

**Memory Management:**
- Clean up event listeners on unmount
- Dispose WebSocket on component unmount
- Clear message queues appropriately

**Battery Optimization (Mobile):**
- Reduce ping frequency when app in background
- Pause WebSocket when app backgrounded (optional)
- Resume on app foreground

### 7. Security Considerations

**Token Management:**
- Store JWT securely (SecureStore/Keychain)
- Refresh token before expiration
- Re-authenticate if token invalid
- Never log token in console

**Connection Security:**
- Always use WSS in production
- Validate server certificates
- Don't connect over insecure networks (optional)

**Message Validation:**
- Validate all incoming messages
- Check event types
- Verify payload structure
- Sanitize data before display

### 8. Testing Requirements

**Test Scenarios:**
1. Successful connection
2. Connection failure handling
3. Reconnection with backoff
4. Message reception for each event type
5. Multiple rapid events
6. Network interruption
7. Token expiration during connection
8. App backgrounding/foregrounding
9. Multiple tabs/devices (if web)
10. Rate limiting response

**Test Cases:**
- Connect with valid token
- Connect with invalid token
- Handle server disconnection
- Handle network loss
- Receive all event types
- Handle malformed messages
- Reconnect after failure
- Clean up on unmount

### 9. Integration Points

**Where to Integrate:**

1. **App Initialization:**
   - Connect WebSocket after user login
   - Store connection in global state
   - Initialize event handlers

2. **Attendance Screen:**
   - Listen for ATTENDANCE_MARKED events
   - Update attendance list
   - Refresh statistics

3. **Tasks Screen:**
   - Listen for TASK_STATUS_UPDATED
   - Listen for TASK_ASSIGNED
   - Update task lists
   - Show assignment notifications

4. **Dashboard:**
   - Listen for DASHBOARD_UPDATE
   - Update all counters
   - Refresh charts

5. **Activity Feed (Enterprise):**
   - Listen for EMPLOYEE_ACTIVITY
   - Append to activity timeline
   - Filter by subscription plan

6. **Navigation/Header:**
   - Show connection status
   - Display notification badges
   - Show task assignment count

### 10. Error Scenarios to Handle

**Connection Errors:**
- Network unavailable
- Server unreachable
- SSL/TLS errors
- Authentication failures
- Rate limiting

**Message Errors:**
- Invalid JSON
- Missing required fields
- Unknown event types
- Malformed payloads

**State Errors:**
- Token expired during connection
- User logged out
- Subscription changed
- App backgrounded

### 11. Best Practices

**Code Organization:**
- Separate WebSocket logic into custom hook/service
- Create event handler registry
- Use TypeScript for type safety
- Implement proper error boundaries

**User Experience:**
- Show loading states
- Provide feedback for all actions
- Don't block UI during reconnection
- Graceful degradation if WebSocket fails

**Performance:**
- Minimize re-renders
- Use memoization for handlers
- Debounce rapid updates
- Clean up resources properly

**Monitoring:**
- Log connection events
- Track message counts
- Monitor reconnection frequency
- Track error rates

### 12. Implementation Checklist

**Phase 1: Basic Connection**
- [ ] Create WebSocket connection manager
- [ ] Implement connection with JWT
- [ ] Handle CONNECTED event
- [ ] Show connection status

**Phase 2: Event Handling**
- [ ] Implement ATTENDANCE_MARKED handler
- [ ] Implement TASK_STATUS_UPDATED handler
- [ ] Implement TASK_ASSIGNED handler
- [ ] Implement DASHBOARD_UPDATE handler
- [ ] Implement EMPLOYEE_ACTIVITY handler (Enterprise only)

**Phase 3: Reconnection**
- [ ] Implement exponential backoff
- [ ] Handle connection drops
- [ ] Implement fallback to REST polling
- [ ] Show reconnection status

**Phase 4: UI Integration**
- [ ] Add toast notifications
- [ ] Update lists in real-time
- [ ] Update dashboard counters
- [ ] Show notification badges

**Phase 5: Polish**
- [ ] Add sound notifications
- [ ] Animate updates
- [ ] Optimize performance
- [ ] Add error boundaries
- [ ] Test all scenarios

### 13. Example Event Flow

**Scenario: Employee marks attendance**

1. Employee punches in via mobile app
2. Backend emits ATTENDANCE_MARKED event
3. WebSocket server broadcasts to Admin/HR/Manager rooms
4. Frontend receives event:
   ```json
   {
     "event": "ATTENDANCE_MARKED",
     "tenant_id": "12",
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
5. Frontend actions:
   - Show toast: "Sai Pranathi marked attendance (LOGIN)"
   - Update attendance dashboard counter: 8 → 9
   - If on attendance screen, refresh list
   - Play notification sound (if enabled)

### 14. Subscription Plan Handling

**Check subscription plan from CONNECTED event:**
- `subscription_plan`: "basic", "pro", or "enterprise"

**Feature Gating:**
- **Basic:** Only show ATTENDANCE_MARKED events
- **Pro:** Show attendance + task events
- **Enterprise:** Show all events including activity feed

**Implementation:**
- Store subscription plan from CONNECTED event
- Filter events based on plan
- Show upgrade prompts for restricted features

### 15. Message Format Reference

**All messages follow this structure:**
```json
{
  "event": "EVENT_TYPE",
  "tenant_id": "string",
  "timestamp": "ISO8601 datetime",
  "message": "Human readable message (optional)",
  "data": { /* Event-specific data */ }
}
```

**Event-specific payloads:**
- See `WEBSOCKET_ARCHITECTURE.md` for detailed schemas
- All timestamps in ISO8601 format
- All IDs as strings in messages

### 16. Development Tips

**Testing:**
- Use WebSocket testing tools (websocket.org/echo.html)
- Test with network throttling
- Simulate connection drops
- Test with invalid tokens

**Debugging:**
- Log all received messages
- Log connection state changes
- Monitor reconnection attempts
- Track event handler execution

**Performance:**
- Profile message handling
- Monitor memory usage
- Check for memory leaks
- Optimize re-renders

---

## Success Criteria

Your implementation is successful when:

✅ WebSocket connects automatically after login
✅ All event types are received and handled correctly
✅ UI updates in real-time without manual refresh
✅ Reconnection works seamlessly
✅ Error handling is robust
✅ Performance is optimal
✅ User experience is smooth
✅ Works on both web and mobile
✅ Handles all edge cases
✅ Subscription plan gating works correctly

---

## Additional Resources

- WebSocket API documentation: MDN WebSocket
- React Native WebSocket: react-native-websocket
- Connection management patterns
- Error handling best practices
- Real-time UI update patterns

---

## Notes

- WebSocket connection is optional - app should work without it (fallback to REST)
- Don't block critical features if WebSocket fails
- Always validate messages before processing
- Handle token refresh during active connection
- Consider implementing message queuing for offline support
- Test thoroughly on slow networks
- Monitor connection health in production

---

**Ready to implement?** Use this prompt as your guide and implement the WebSocket client following all the requirements above. Good luck! 🚀

