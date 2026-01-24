# OPS Orchestration System - User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Basic Operations](#basic-operations)
4. [Advanced Features](#advanced-features)
5. [Monitoring and Debugging](#monitoring-and-debugging)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Introduction

The OPS Orchestration System is a powerful platform that combines AI-driven planning with structured execution pipelines to provide intelligent IT operations management. This guide will help you understand how to effectively use the system for various tasks.

### Key Features

- **AI-Powered Planning**: Uses LLMs to understand natural language queries and create execution plans
- **Stage-Based Execution**: Modular execution pipeline with route planning, validation, execution, composition, and presentation
- **Asset Management**: Centralized management of prompts, policies, queries, mappings, and screens
- **Regression Analysis**: Powerful tools to analyze performance and behavior changes over time
- **Real-time Monitoring**: Comprehensive traceability and logging for all operations

### System Architecture

```
User Query → CI Planner → Stage Executor → Asset Registry → Response Generation
    ↓         ↓           ↓           ↓               ↓
Route Plan → Validation → Execution → Composition → Presentation
    ↓                                       ↓
Replan Logic ← Control Loop ← Audit Logging ← Output
```

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 16+
- PostgreSQL 12+
- Redis 6+

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tobit-spa-ai
   ```

2. **Backend Setup**
   ```bash
   cd apps/api
   pip install -r requirements.txt
   alembic upgrade head
   python scripts/seed.py
   ```

3. **Frontend Setup**
   ```bash
   cd apps/web
   npm install
   npm run build
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### First Query

1. Start the backend server:
   ```bash
   cd apps/api
   python -m uvicorn main:app --reload
   ```

2. Start the frontend:
   ```bash
   cd apps/web
   npm run dev
   ```

3. Access the application at `http://localhost:3000`

4. Ask your first question:
   ```
   "서버 상태를 확인해주세요"
   ```

## Basic Operations

### 1. Query Execution

#### Simple Queries
Start with basic queries about your infrastructure:

```
"서버 상태를 확인해주세요"
"CPU 사용률을 알려줘"
"메모리 사용량은 어때?"
```

#### Complex Queries
The system can handle multi-step queries:

```
"srv-erp-01 서버의 CPU 사용률과 메모리 사용량을 확인하고,
이상이 있으면 관련 경고 이벤트를 보여줘"
```

#### Data Analysis Queries
Perform complex data analysis:

```
"최근 24시간 동안의 CPU 사용률 평균과 최대값을 계산해줘"
"각 서버의 에러 발생 빈도를 분석해줘"
```

### 2. Asset Management

#### Viewing Assets
Navigate to `Admin > Assets` to view all available assets:
- **Prompts**: AI prompts for specific tasks
- **Policies**: Business rules and constraints
- **Queries**: Data queries and aggregations
- **Mappings**: Data transformation rules
- **Screens**: UI components and layouts
- **Sources / Schemas / Resolvers**: 데이터 연결 설정은 `Data` 메뉴에서 관리 (Admin에서는 읽기 전용 요약)

#### Asset Versions
Each asset supports versioning:
- **Published**: Currently active version
- **Draft**: Work-in-progress version
- **Archived**: Historical version

### 3. Trace Inspection

#### Accessing Traces
Every query execution creates a trace that can be accessed:
1. From the results panel
2. Via the Inspector page
3. Through API endpoints

#### Understanding Traces
Traces show:
- **Route**: How the query was processed (direct/orch/reject)
- **Stage Inputs/Outputs**: What happened at each stage
- **Execution Metrics**: Duration, status, and diagnostics
- **Asset Usage**: Which assets were used
- **Replan Events**: Any replanning decisions

## Advanced Features

### 1. Stage In/Out Panel

The Stage In/Out panel provides detailed visibility into each execution stage:

#### Features
- **Collapsible Sections**: Expand/collapse individual stages
- **JSON Viewer**: Syntax-highlighted JSON display
- **Diagnostics**: Warnings, errors, and performance metrics
- **Metadata**: Execution time, status, and reference counts

#### Usage
1. Open any trace in the Inspector
2. Click "Show Stage Details"
3. Navigate between stages to see inputs and outputs

### 2. Replan Event Timeline

The timeline visualization shows replan events:

#### Features
- **Timeline View**: Horizontal timeline of events
- **Filter by Type**: Filter by error, timeout, policy_violation, etc.
- **Event Details**: Click on events for detailed information
- **Patch Diff**: See what changed before and after replan

### 3. Asset Override Testing

Test different asset versions without affecting production:

#### Steps
1. Open the Asset Override modal
2. Select assets to override
3. Choose versions for testing
4. Run test with baseline comparison

#### Use Cases
- A/B testing different prompts
- Performance testing new policies
- Validation query changes
- UI screen variations

### 4. Regression Analysis

Compare different execution versions to detect regressions:

#### Types of Analysis
1. **Stage-Level**: Compare individual stage performance
2. **Asset Impact**: Analyze asset version changes
3. **Time Series**: Compare performance over time

#### Analysis Workflow
1. Select baseline trace
2. Select comparison trace
3. Run regression analysis
4. Review reports and recommendations

## Monitoring and Debugging

### 1. Performance Monitoring

#### Key Metrics
- **Response Time**: Total query execution time
- **Stage Durations**: Time spent in each stage
- **Asset Performance**: Individual asset execution times
- **Error Rates**: Frequency of errors and warnings

#### Performance Dashboard
Access the OPS dashboard to view:
- Real-time metrics
- Historical trends
- Performance alerts
- Resource utilization

### 2. Audit Logging

All operations are logged with:
- Timestamps
- User information
- Resource changes
- Decision reasons

#### Accessing Logs
1. Navigate to `Inspector > Audit Logs`
2. Filter by trace, resource type, or time range
3. Export logs for analysis

### 3. Error Handling

#### Common Errors
1. **Timeout Errors**: Queries taking too long
2. **Asset Not Found**: Missing or unavailable assets
3. **Validation Errors**: Invalid query or parameters
4. **Rejection**: Query rejected by policy

#### Error Resolution
1. Check the error details in the trace
2. Review audit logs for context
3. Test with simplified queries
4. Update assets or policies as needed

## Best Practices

### 1. Query Optimization

#### Good Queries
- Specific and clear
- Include relevant context
- Use proper time ranges
- Break complex queries into steps

#### Bad Queries
- Overly broad or ambiguous
- Missing context
- Extremely complex nesting
- Requesting too much data

### 2. Asset Management

#### Version Control
- Use semantic versioning
- Document changes
- Keep versions stable
- Archive old versions

#### Asset Selection
- Choose appropriate assets for each task
- Test changes before deploying
- Monitor performance impact
- Update regularly

### 3. Performance Tuning

#### Settings to Adjust
- **Timeout Values**: Adjust based on query complexity
- **Parallel Execution**: Enable for complex queries
- **Cache Settings**: Configure for frequently accessed data
- **Resource Limits**: Set appropriate limits

#### Monitoring Tips
- Track response times
- Monitor error rates
- Check resource usage
- Review regression reports

### 4. Security Considerations

#### Best Practices
- Use API keys securely
- Implement proper authentication
- Regular security updates
- Access control for sensitive data

## Troubleshooting

### 1. Common Issues

#### Queries Not Working
1. **Check Syntax**: Ensure proper punctuation and context
2. **Verify Assets**: Confirm required assets are available
3. **Test Simplified**: Try simpler version of query
4. **Check Logs**: Review error messages in traces

#### Performance Issues
1. **Slow Responses**: Check resource usage and timeouts
2. **High Memory**: Optimize queries and limit data
3. **Timeout Errors**: Increase timeout or simplify queries
4. **Resource Contention**: Scale resources or optimize queries

#### Asset Problems
1. **Missing Assets**: Check asset registry and versions
2. **Outdated Versions**: Update to latest published versions
3. **Permission Issues**: Verify asset access permissions
4. **Override Issues**: Check asset override settings

### 2. Debug Steps

#### Debug Flow
1. **Check Trace**: Review the execution trace
2. **Review Logs**: Check audit logs for details
3. **Test Isolation**: Test components individually
4. **Validate Data**: Confirm input data is correct

#### Tools
- **Inspector**: Detailed trace analysis
- **Timeline**: Replan event visualization
- **Asset Tester**: Test asset overrides
- **Regression**: Compare different versions

### 3. Getting Help

#### Support Channels
1. **Documentation**: Check API docs and user guides
2. **Community**: Join discussion forums
3. **Support**: Contact support team for issues
4. **GitHub**: Report bugs or feature requests

#### Reporting Issues
When reporting issues, include:
- System version and environment
- Steps to reproduce
- Expected vs actual behavior
- Error messages and traces
- Relevant configuration

## Advanced Topics

### 1. Custom Assets

Creating custom assets for specific needs:

#### Prompts
- Write clear, specific instructions
- Include examples when helpful
- Handle edge cases
- Test thoroughly before deployment

#### Policies
- Define business rules clearly
- Include validation logic
- Document exceptions
- Review regularly

### 2. Integration Patterns

#### Webhook Integration
Set up webhooks for:
- Real-time notifications
- Error alerts
- Performance monitoring
- External system integration

#### API Integration
Use the API for:
- Automated workflows
- Custom dashboards
- Data export
- Third-party applications

### 3. Extending the System

#### Adding Stages
Extend the execution pipeline:
1. Define stage schema
2. Implement stage logic
3. Add to orchestrator
4. Test thoroughly

#### Custom Tools
Create custom execution tools:
1. Define tool interface
2. Implement business logic
3. Register with executor
4. Document usage

## Conclusion

The OPS Orchestration System provides powerful tools for managing IT operations with AI assistance. By following this guide and best practices, you can effectively leverage the system to improve efficiency, visibility, and performance in your operations.

For the latest updates and additional resources, visit the documentation portal and community forums.
