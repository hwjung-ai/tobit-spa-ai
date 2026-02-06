# Monitoring Dashboard Quick Start Guide

## Access the Dashboard

1. Go to **Admin** panel
2. Click on **Observability** tab
3. Dashboard loads automatically with real-time data

## Key Sections

### 1. System Health Overview (Top)
Shows at-a-glance metrics:
- **Total Rules**: Count of all CEP rules
- **Today Executions**: How many times rules ran today
- **Error Count**: Total errors today
- **Avg Duration**: Average execution time

### 2. Alert Channels (Left)
Status of notification channels (Slack, Email, SMS, etc.):
- **Green**: Healthy, no failures
- **Yellow**: Some failures detected
- **Red**: Significant failures

Click on a channel to see recent send attempts.

### 3. Rule Performance (Right)
Top 10 performing rules ranked by execution frequency:
- **Green badge**: Active rule
- **Error %**: Failure rate for this rule
- **Duration**: Average execution time

Click on a rule to view detailed analytics.

### 4. Error Timeline (Bottom Left)
Visual trend of errors over time:
- **Line chart**: Error count by hour
- **Buttons**: Switch between 1h, 6h, 24h, 7d views
- **Pie chart**: Error type breakdown

### 5. Error Distribution (Bottom Right)
Breakdown of error types:
- Timeout: Connection took too long
- Connection: Failed to connect
- Validation: Invalid data/configuration
- Authentication: Auth failed
- Other: Miscellaneous errors

### 6. Recent Errors (Bottom)
List of most recent errors:
- Shows rule name and error message
- Click to expand and see full details
- Red = critical, Yellow = validation issues

## Controls

### Auto-Refresh
- **Toggle**: Enable/disable automatic updates
- **Interval**: Choose how often to refresh
  - Every 10s: Most frequent updates
  - Every 30s: Default, balanced
  - Every 60s: Less frequent
  - Every 5m: Least frequent

Tip: Use slower intervals for overview, faster for active troubleshooting.

## Understanding the Colors

### Health Status
- **Green**: Excellent (error rate < 5%)
- **Yellow**: Warning (error rate 5-10%)
- **Red**: Critical (error rate > 10%)

### Severity Indicators
- **Red dot**: Critical error (usually timeout)
- **Orange dot**: Connection issue
- **Yellow dot**: Validation error
- **Gray dot**: Other error type

## Quick Tips

1. **High Error Rate?**
   - Check "Recent Errors" section
   - Click on problematic rule to see execution history
   - Review error messages in expanded view

2. **Channel Not Delivering?**
   - Check "Alert Channels" section
   - Look for red status badge
   - Review recent log in channel details

3. **Performance Degrading?**
   - Check "Performance Metrics" section
   - Compare avg duration with recent trends
   - Look for spikes in "Error Timeline"

4. **Rule Not Executing?**
   - Check if rule is "Active" (green badge in Rule Performance)
   - Verify rule has no errors in Error Timeline
   - Check channel health for notification failures

## Data Interpretation

### Execution Count
Shows how frequently a rule is being evaluated. Higher = more active monitoring.

### Error Rate
Percentage of executions that failed.
- 0% = Perfect
- <5% = Excellent
- 5-10% = Good
- 10%+ = Needs attention

### Avg Duration
Average time to execute a rule:
- <50ms = Excellent
- 50-100ms = Good
- 100-500ms = Acceptable
- >500ms = Slow

### Failure Rate (Channels)
Percentage of notifications that failed to send:
- 0% = Perfect delivery
- <5% = Great
- 5-10% = Acceptable
- >10% = Issues

## Troubleshooting

### Dashboard Not Loading Data?
1. Refresh the page
2. Check browser console (F12) for errors
3. Verify API endpoint is accessible
4. Wait 30 seconds for initial data load

### Charts Not Showing?
1. Disable auto-refresh
2. Manually refresh
3. Check if you have data (recent errors?)
4. Try different time period

### Data Seems Stale?
1. Check auto-refresh toggle is ON
2. Verify refresh interval is set
3. Check browser network tab for API calls
4. Refresh page manually

### Rules Not Appearing?
1. Verify rules exist in CEP builder
2. Check if rules are active
3. Ensure rules have been executed recently
4. Check database connection status

## Common Questions

**Q: How often is data updated?**
A: Default is 30 seconds. Change in "Auto-refresh" dropdown.

**Q: Why do I see "No errors"?**
A: Great! Your system is working well. You can leave the dashboard running to monitor for issues.

**Q: Can I export this data?**
A: Currently view only. Export feature coming soon.

**Q: What data is shown?**
A: Last 24 hours for most metrics. Error timeline can show 1h to 7d.

**Q: Can I customize the dashboard?**
A: Currently default layout. Custom dashboards coming soon.

## Performance Notes

The dashboard is optimized for:
- Real-time monitoring of active systems
- Quick problem identification
- Trend analysis
- Multi-channel visibility

It is NOT optimized for:
- Historical deep-dive analysis (use logs)
- Detailed rule configuration (use Rule Builder)
- Event investigation (use Event Explorer)

## Getting Help

Having issues? Check these resources:

1. **Full Documentation**: `/docs/MONITORING_DASHBOARD_GUIDE.md`
2. **API Reference**: `/docs/API.md`
3. **Troubleshooting**: See section above
4. **Support**: Contact admin team

---

**Last Updated**: 2026-02-06
**Version**: 1.0
