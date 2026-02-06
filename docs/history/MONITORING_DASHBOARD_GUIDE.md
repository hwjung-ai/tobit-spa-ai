# CEP Monitoring Dashboard Implementation Guide

## Overview

The monitoring dashboard provides real-time visibility into the CEP (Complex Event Processing) system. It displays system health, rule performance, alert channel status, error metrics, and execution trends.

**Implementation Date**: 2026-02-06

## Architecture

### Backend Components

#### API Endpoints (4 new endpoints)

All endpoints are located in `/apps/api/app/modules/cep_builder/router.py`

##### 1. GET `/cep/channels/status`

Returns notification channel health metrics for the last 24 hours.

**Response Structure**:
```json
{
  "data": {
    "channels": [
      {
        "type": "slack",
        "display_name": "Slack",
        "active": 3,
        "inactive": 1,
        "total_sent": 150,
        "total_failed": 5,
        "failure_rate": 0.033,
        "last_sent_at": "2024-02-06T10:30:00Z",
        "recent_logs": [...]
      }
    ],
    "period_hours": 24
  }
}
```

**Query Parameters**: None

**Use Cases**:
- Monitor notification delivery health
- Identify failing channels
- Track delivery statistics by channel type

##### 2. GET `/cep/stats/summary`

Provides overall system statistics.

**Response Structure**:
```json
{
  "data": {
    "stats": {
      "total_rules": 25,
      "active_rules": 22,
      "inactive_rules": 3,
      "today_execution_count": 5200,
      "today_error_count": 25,
      "today_error_rate": 0.0048,
      "today_avg_duration_ms": 47.3,
      "last_24h_execution_count": 12500,
      "timestamp": "2024-02-06T12:00:00Z"
    }
  }
}
```

**Query Parameters**: None

**Use Cases**:
- System health overview
- Performance trends
- Rule activation status
- Error rate monitoring

##### 3. GET `/cep/errors/timeline`

Returns error distribution and timeline data.

**Response Structure**:
```json
{
  "data": {
    "timeline": [
      {"timestamp": "2024-02-06T12:00:00Z", "error_count": 2},
      {"timestamp": "2024-02-06T13:00:00Z", "error_count": 5}
    ],
    "error_distribution": {
      "timeout": 8,
      "connection": 3,
      "validation": 2,
      "authentication": 1,
      "other": 1
    },
    "recent_errors": [
      {
        "exec_id": "uuid",
        "rule_id": "uuid",
        "rule_name": "CPU Alert",
        "triggered_at": "2024-02-06T13:30:00Z",
        "error_message": "Connection timeout",
        "duration_ms": 5000
      }
    ],
    "period": "24h",
    "total_errors": 15
  }
}
```

**Query Parameters**:
- `period`: Time period to analyze (1h, 6h, 24h, 7d) - Default: 24h

**Use Cases**:
- Error trend analysis
- Error categorization
- Root cause identification
- Performance diagnostics

##### 4. GET `/cep/rules/performance`

Returns performance metrics for all rules.

**Response Structure**:
```json
{
  "data": {
    "rules": [
      {
        "rule_id": "uuid",
        "rule_name": "Memory Alert",
        "is_active": true,
        "execution_count": 250,
        "error_count": 5,
        "error_rate": 0.02,
        "avg_duration_ms": 45.2
      }
    ],
    "total_rules": 25,
    "period_days": 7
  }
}
```

**Query Parameters**:
- `limit`: Maximum number of rules to return (1-50) - Default: 10

**Use Cases**:
- Rule performance ranking
- Identify problematic rules
- Resource usage analysis
- SLA monitoring

### Frontend Components

#### Directory Structure
```
apps/web/src/components/admin/observability/
├── DashboardPage.tsx          (Main container & layout)
├── SystemHealthChart.tsx      (Overall health metrics)
├── AlertChannelStatus.tsx     (Channel health & stats)
├── RuleStatsCard.tsx          (Rule performance list)
├── ExecutionTimeline.tsx      (Error timeline graph)
├── ErrorDistribution.tsx      (Error type breakdown)
├── PerformanceMetrics.tsx     (Detailed performance KPIs)
├── RecentErrors.tsx           (Recent error list with details)
└── __tests__/
    ├── RuleStatsCard.test.tsx
    └── SystemHealthChart.test.tsx
```

#### Component Details

##### 1. SystemHealthChart
- **Purpose**: Overview of system health status
- **Data Source**: `/cep/stats/summary`
- **Refresh Interval**: 30 seconds
- **Features**:
  - Total/Active rule counts with progress bars
  - Today's execution metrics
  - Error count and rate visualization
  - Average response time
  - Health status indicator

##### 2. AlertChannelStatus
- **Purpose**: Notification channel health monitoring
- **Data Source**: `/cep/channels/status`
- **Refresh Interval**: 30 seconds
- **Features**:
  - Per-channel status (Healthy/Degraded/Failing)
  - Active/Inactive counts
  - Total sent and failed metrics
  - Failure rate progress bars
  - Last sent timestamp

##### 3. RuleStatsCard
- **Purpose**: Top performing/problematic rules
- **Data Source**: `/cep/rules/performance`
- **Refresh Interval**: Manual (on-demand)
- **Features**:
  - Sorted by execution frequency
  - Active/inactive status badges
  - Error rate visualization
  - Clickable for rule details
  - Average duration metrics

##### 4. ExecutionTimeline
- **Purpose**: Error trend visualization
- **Data Source**: `/cep/errors/timeline`
- **Refresh Interval**: 60 seconds
- **Features**:
  - Line chart of error counts
  - Period selector (1h, 6h, 24h, 7d)
  - Error distribution summary
  - Recent error list with drill-down
  - Error categorization

##### 5. ErrorDistribution
- **Purpose**: Error type breakdown
- **Data Source**: `/cep/errors/timeline`
- **Refresh Interval**: 60 seconds
- **Features**:
  - Pie chart of error types
  - Percentage breakdown
  - Color-coded error types
  - Total error count

##### 6. PerformanceMetrics
- **Purpose**: Detailed performance KPIs
- **Data Source**: `/cep/stats/summary`
- **Refresh Interval**: 60 seconds
- **Features**:
  - Throughput metrics (exec/hour)
  - Average response time
  - Success/error rates
  - Execution statistics
  - Health assessment with indicators

##### 7. RecentErrors
- **Purpose**: Recent error details with exploration
- **Data Source**: `/cep/errors/timeline`
- **Refresh Interval**: 60 seconds
- **Features**:
  - Expandable error cards
  - Severity color coding
  - Error message display
  - Duration and timestamp
  - Full error details on expand

##### 8. DashboardPage
- **Purpose**: Main dashboard container
- **Features**:
  - Auto-refresh toggle
  - Configurable refresh interval (10s, 30s, 60s, 5m)
  - Responsive grid layout
  - Real-time update indicator
  - Component composition

## Data Flow

```
Frontend Components
        ↓
   API Requests
        ↓
Backend Endpoints
        ↓
Database Queries
        ↓
System State
```

### Request Flow for Stats Summary

1. Component mounts → `useEffect` triggers
2. Fetch `/cep/stats/summary`
3. Parse response and update state
4. Render with formatted data
5. Set refresh interval (30-300 seconds)
6. Cleanup on unmount

### Error Handling

- **Network Errors**: Display error message with retry option
- **Empty Data**: Show "No data" state with helpful message
- **Invalid Response**: Fall back to default values
- **API Failures**: Graceful degradation with error boundaries

## Usage

### For Users

1. Navigate to **Admin → Observability**
2. Dashboard loads with real-time data
3. Toggle **Auto-refresh** to enable/disable updates
4. Select refresh interval (10s to 5m)
5. Click on rules to view details
6. Expand error items to see full details
7. Monitor status indicators and metrics

### For Developers

#### Adding a New Component

1. Create component in `observability/` directory:
```tsx
import { useEffect, useState } from "react";

export default function NewComponent() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch data
  }, []);

  return <div>Component content</div>;
}
```

2. Add to DashboardPage:
```tsx
import NewComponent from "./NewComponent";

// In render:
<section>
  <NewComponent />
</section>
```

3. Create test file in `__tests__/` directory

#### Adding a New API Endpoint

1. Add to `router.py`:
```python
@router.get("/cep/new-metric")
def get_new_metric(session: Session = Depends(get_session)) -> ResponseEnvelope:
    # Implementation
    return ResponseEnvelope.success(data={"metric": value})
```

2. Create frontend component following the pattern above
3. Add tests for the endpoint

## Performance Considerations

### API Response Times
- `channels/status`: ~50-100ms (minimal database operations)
- `stats/summary`: ~100-200ms (aggregation queries)
- `errors/timeline`: ~150-300ms (time-range queries)
- `rules/performance`: ~200-400ms (complex aggregations)

### Frontend Optimization
- Components fetch only needed data
- No global state (each component manages state)
- Efficient re-renders with proper dependencies
- Chart rendering optimized with Recharts
- Lazy loading not needed (small payloads)

### Scaling Considerations

**For 1000+ rules**:
- Implement pagination in `rules/performance`
- Add database indexes on `triggered_at`
- Consider caching common queries
- Use time-based data partitioning

**For high-traffic systems**:
- Reduce refresh intervals on components
- Implement server-side caching (Redis)
- Add query result caching
- Consider materialized views for aggregations

## Monitoring and Debugging

### Debug Mode

Add to browser console:
```javascript
// Log all dashboard API calls
fetch = (new Proxy(fetch, {
  apply(target, thisArg, args) {
    if (args[0].includes('/cep/')) {
      console.log('[Dashboard API]', args[0]);
    }
    return target.apply(thisArg, args);
  }
}));
```

### Common Issues

**1. Data not updating**
- Check auto-refresh toggle
- Verify network tab for API errors
- Check browser console for errors
- Clear cache and reload

**2. Charts not rendering**
- Verify API returns data in expected format
- Check console for Recharts errors
- Ensure sufficient window width for charts
- Check browser RAM for memory pressure

**3. Missing rules/channels**
- Verify items are marked as active/inactive
- Check database connections
- Review backend logs
- Check API response structure

## Testing

### Unit Tests

Located in `__tests__/` directories:
- `RuleStatsCard.test.tsx`: Component rendering and data display
- `SystemHealthChart.test.tsx`: Stats loading and display

Run tests:
```bash
npm test -- observability
```

### Integration Tests

Located in `/apps/api/tests/test_monitoring_dashboard.py`

Test coverage:
- All 4 endpoints
- Data structure validation
- Error handling
- Parameter validation
- Pagination limits

Run tests:
```bash
pytest tests/test_monitoring_dashboard.py
```

### End-to-End Tests

Manual testing checklist:
- [ ] All components load without errors
- [ ] Auto-refresh toggles on/off
- [ ] Refresh intervals work correctly
- [ ] Data updates after refresh
- [ ] Error states display correctly
- [ ] Responsive layout on mobile
- [ ] Charts render properly
- [ ] Links and buttons functional

## API Documentation

### Response Envelope

All responses follow the standard ResponseEnvelope format:
```json
{
  "success": true,
  "code": 0,
  "message": "OK",
  "data": {
    // Endpoint-specific data
  }
}
```

### Error Responses

Errors return appropriate HTTP status codes:
- `400`: Invalid parameters
- `404`: Resource not found
- `500`: Server error
- `503`: Service unavailable

### Rate Limiting

No rate limiting on monitoring endpoints. Safe for frequent polling.

## Browser Compatibility

- Chrome/Chromium 90+
- Firefox 88+
- Safari 14+
- Edge 90+

Requires:
- ES2020+ JavaScript support
- CSS Grid and Flexbox
- Fetch API
- Dynamic imports

## Future Enhancements

1. **Export functionality**: CSV/JSON export of metrics
2. **Alerting**: Trigger alerts when thresholds exceeded
3. **Custom dashboards**: User-customizable layouts
4. **Drilldown analytics**: Deep dive into specific rules
5. **Comparative analysis**: Week-over-week metrics
6. **Predictive alerts**: ML-based anomaly detection
7. **Audit trail**: Track dashboard view history
8. **Custom metrics**: User-defined KPIs

## Support and Troubleshooting

### Common Questions

**Q: How frequently does data update?**
A: Default is 30 seconds for system metrics, 60 seconds for error analysis. Configurable in dashboard.

**Q: What data is stored for monitoring?**
A: Only execution logs and notification logs. Raw event payloads are not stored.

**Q: Can I access dashboard via API?**
A: Yes, all dashboard data is available via REST APIs without authentication required (if configured).

**Q: How long is historical data retained?**
A: Depends on database retention policy, typically 30-90 days.

## Related Documentation

- [CEP Engine Guide](/docs/BYTEWAX_INTEGRATION_GUIDE.md)
- [Notification System](/docs/IMPLEMENTATION_COMPLETE_SUMMARY.md)
- [API Reference](/docs/API.md)
- [Database Schema](/docs/DATABASE.md)

## File References

**Backend**:
- `/apps/api/app/modules/cep_builder/router.py` (Lines 1198-1440+)
- `/apps/api/tests/test_monitoring_dashboard.py`

**Frontend**:
- `/apps/web/src/app/admin/observability/page.tsx`
- `/apps/web/src/components/admin/observability/DashboardPage.tsx`
- `/apps/web/src/components/admin/observability/*.tsx` (7 components)
- `/apps/web/src/components/admin/observability/__tests__/*.test.tsx`

---

**Last Updated**: 2026-02-06
**Version**: 1.0
**Status**: Production Ready
