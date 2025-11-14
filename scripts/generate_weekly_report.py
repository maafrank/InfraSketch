#!/usr/bin/env python3
"""
Weekly Usage Report Generator for InfraSketch
Queries CloudWatch metrics and logs to generate a comprehensive usage report.
"""

import boto3
import json
from datetime import datetime, timedelta
from collections import defaultdict

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
logs = boto3.client('logs', region_name='us-east-1')


def get_metric_stats(namespace, metric_name, dimensions, start_time, end_time, stat='Sum'):
    """Get CloudWatch metric statistics."""
    try:
        response = cloudwatch.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=86400,  # Daily
            Statistics=[stat]
        )
        datapoints = response.get('Datapoints', [])
        if not datapoints:
            return 0

        if stat == 'Sum':
            return sum(dp[stat] for dp in datapoints)
        elif stat == 'Average':
            return sum(dp[stat] for dp in datapoints) / len(datapoints)
        else:
            return datapoints[-1][stat] if datapoints else 0
    except Exception as e:
        print(f"Error getting metric {metric_name}: {e}")
        return 0


def query_logs(query_string, start_time, end_time):
    """Query CloudWatch Logs Insights."""
    try:
        start_query_response = logs.start_query(
            logGroupName='/aws/lambda/infrasketch-backend',
            startTime=int(start_time.timestamp()),
            endTime=int(end_time.timestamp()),
            queryString=query_string
        )

        query_id = start_query_response['queryId']

        # Wait for query to complete
        import time
        while True:
            time.sleep(1)
            result = logs.get_query_results(queryId=query_id)
            if result['status'] == 'Complete':
                return result.get('results', [])
            elif result['status'] == 'Failed':
                return []
            # Continue waiting if Running or Scheduled
    except Exception as e:
        print(f"Error querying logs: {e}")
        return []


def generate_report():
    """Generate weekly usage report."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=7)

    print(f"Generating report for {start_time.date()} to {end_time.date()}")

    # 1. CloudFront Metrics
    cloudfront_requests = get_metric_stats(
        'AWS/CloudFront',
        'Requests',
        [
            {'Name': 'DistributionId', 'Value': 'E2YM028NUBX2QN'},
            {'Name': 'Region', 'Value': 'Global'}
        ],
        start_time,
        end_time
    )

    # 2. Lambda Metrics
    lambda_invocations = get_metric_stats(
        'AWS/Lambda',
        'Invocations',
        [{'Name': 'FunctionName', 'Value': 'infrasketch-backend'}],
        start_time,
        end_time
    )

    lambda_errors = get_metric_stats(
        'AWS/Lambda',
        'Errors',
        [{'Name': 'FunctionName', 'Value': 'infrasketch-backend'}],
        start_time,
        end_time
    )

    avg_duration = get_metric_stats(
        'AWS/Lambda',
        'Duration',
        [{'Name': 'FunctionName', 'Value': 'infrasketch-backend'}],
        start_time,
        end_time,
        stat='Average'
    )

    # 3. Application Events from Logs
    diagrams_created = query_logs(
        'fields @timestamp | filter event_type = "diagram_generated" | stats count() as total',
        start_time,
        end_time
    )

    chat_interactions = query_logs(
        'fields @timestamp | filter event_type = "chat_message" | stats count() as total',
        start_time,
        end_time
    )

    exports = query_logs(
        'fields @timestamp | filter event_type = "export_design_doc" | stats count() as total',
        start_time,
        end_time
    )

    unique_sessions = query_logs(
        'fields session_id | filter event_type in ["diagram_generated", "chat_message"] | stats count_distinct(session_id) as unique_sessions',
        start_time,
        end_time
    )

    unique_users = query_logs(
        'fields user_ip | filter event_type = "api_request" | stats count_distinct(user_ip) as unique_users',
        start_time,
        end_time
    )

    avg_diagram_complexity = query_logs(
        'fields metadata.node_count, metadata.edge_count | filter event_type = "diagram_generated" | stats avg(metadata.node_count) as avg_nodes, avg(metadata.edge_count) as avg_edges',
        start_time,
        end_time
    )

    # 4. Error Analysis
    top_errors = query_logs(
        'fields error | filter event_type = "api_error" | stats count() as error_count by error | sort error_count desc | limit 5',
        start_time,
        end_time
    )

    # Extract values from query results
    def extract_value(results, field_name, default=0):
        if not results or not results[0]:
            return default
        for item in results[0]:
            if item.get('field') == field_name:
                try:
                    return float(item.get('value', default))
                except (ValueError, TypeError):
                    return default
        return default

    diagrams_count = extract_value(diagrams_created, 'total')
    chats_count = extract_value(chat_interactions, 'total')
    exports_count = extract_value(exports, 'total')
    sessions_count = extract_value(unique_sessions, 'unique_sessions')
    users_count = extract_value(unique_users, 'unique_users')
    avg_nodes = extract_value(avg_diagram_complexity, 'avg_nodes')
    avg_edges = extract_value(avg_diagram_complexity, 'avg_edges')

    # 5. Build Report
    report = {
        'period': {
            'start': start_time.strftime('%Y-%m-%d'),
            'end': end_time.strftime('%Y-%m-%d')
        },
        'infrastructure': {
            'cloudfront_requests': int(cloudfront_requests),
            'lambda_invocations': int(lambda_invocations),
            'lambda_errors': int(lambda_errors),
            'avg_response_time_ms': round(avg_duration, 2),
            'error_rate': round((lambda_errors / lambda_invocations * 100), 2) if lambda_invocations > 0 else 0
        },
        'usage': {
            'unique_users': int(users_count),
            'unique_sessions': int(sessions_count),
            'diagrams_created': int(diagrams_count),
            'chat_interactions': int(chats_count),
            'exports': int(exports_count)
        },
        'quality': {
            'avg_nodes_per_diagram': round(avg_nodes, 1),
            'avg_edges_per_diagram': round(avg_edges, 1)
        },
        'errors': []
    }

    # Add top errors
    for error_result in top_errors:
        error_dict = {}
        for item in error_result:
            field = item.get('field')
            value = item.get('value')
            if field and value:
                error_dict[field] = value
        if error_dict:
            report['errors'].append(error_dict)

    return report


def format_html_email(report):
    """Format report as HTML email."""
    period = f"{report['period']['start']} to {report['period']['end']}"
    infra = report['infrastructure']
    usage = report['usage']
    quality = report['quality']

    # Calculate engagement metrics
    avg_actions_per_user = round(
        (usage['diagrams_created'] + usage['chat_interactions'] + usage['exports']) / usage['unique_users'],
        1
    ) if usage['unique_users'] > 0 else 0

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
            .metric-card {{ background: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; border-radius: 4px; }}
            .metric-value {{ font-size: 32px; font-weight: bold; color: #2c3e50; margin: 5px 0; }}
            .metric-label {{ font-size: 14px; color: #7f8c8d; text-transform: uppercase; }}
            .highlight {{ background: #e8f4f8; padding: 15px; border-radius: 4px; margin: 15px 0; }}
            .error-list {{ background: #fff3cd; padding: 15px; border-radius: 4px; border-left: 4px solid #ffc107; }}
            .success {{ color: #27ae60; }}
            .warning {{ color: #f39c12; }}
            .error {{ color: #e74c3c; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #3498db; color: white; }}
            .footer {{ margin-top: 40px; padding-top: 20px; border-top: 2px solid #ecf0f1; font-size: 12px; color: #95a5a6; }}
        </style>
    </head>
    <body>
        <h1>📊 InfraSketch Weekly Report</h1>
        <p><strong>Period:</strong> {period}</p>

        <h2>👥 User Engagement</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Unique Users</div>
                <div class="metric-value">{usage['unique_users']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Active Sessions</div>
                <div class="metric-value">{usage['unique_sessions']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Diagrams Created</div>
                <div class="metric-value">{usage['diagrams_created']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Actions/User</div>
                <div class="metric-value">{avg_actions_per_user}</div>
            </div>
        </div>

        <h2>💬 Activity Breakdown</h2>
        <table>
            <tr>
                <th>Activity</th>
                <th>Count</th>
            </tr>
            <tr>
                <td>New Diagrams</td>
                <td>{usage['diagrams_created']}</td>
            </tr>
            <tr>
                <td>Chat Interactions</td>
                <td>{usage['chat_interactions']}</td>
            </tr>
            <tr>
                <td>Document Exports</td>
                <td>{usage['exports']}</td>
            </tr>
        </table>

        <h2>📈 Diagram Complexity</h2>
        <div class="highlight">
            <p><strong>Average Nodes per Diagram:</strong> {quality['avg_nodes_per_diagram']}</p>
            <p><strong>Average Edges per Diagram:</strong> {quality['avg_edges_per_diagram']}</p>
        </div>

        <h2>⚡ Performance</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">API Requests</div>
                <div class="metric-value">{infra['lambda_invocations']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Avg Response Time</div>
                <div class="metric-value">{infra['avg_response_time_ms']}<span style="font-size:16px">ms</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Error Rate</div>
                <div class="metric-value {'success' if infra['error_rate'] < 1 else 'warning' if infra['error_rate'] < 5 else 'error'}">{infra['error_rate']}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Frontend Requests</div>
                <div class="metric-value">{infra['cloudfront_requests']}</div>
            </div>
        </div>

        {'<h2>⚠️ Top Errors</h2><div class="error-list">' + '<br>'.join([f"<strong>{err.get('error', 'Unknown')}:</strong> {err.get('error_count', 0)} occurrences" for err in report['errors'][:5]]) + '</div>' if report['errors'] else '<h2>✅ No Errors</h2><div class="highlight"><p>No errors occurred this week! 🎉</p></div>'}

        <div class="footer">
            <p>This report was automatically generated by InfraSketch Analytics</p>
            <p>Dashboard: <a href="https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/InfraSketch-Overview">View CloudWatch Dashboard</a></p>
        </div>
    </body>
    </html>
    """

    return html


def format_text_email(report):
    """Format report as plain text email."""
    period = f"{report['period']['start']} to {report['period']['end']}"
    infra = report['infrastructure']
    usage = report['usage']
    quality = report['quality']

    text = f"""
InfraSketch Weekly Report
Period: {period}

=== USER ENGAGEMENT ===
Unique Users: {usage['unique_users']}
Active Sessions: {usage['unique_sessions']}
Diagrams Created: {usage['diagrams_created']}

=== ACTIVITY BREAKDOWN ===
New Diagrams: {usage['diagrams_created']}
Chat Interactions: {usage['chat_interactions']}
Document Exports: {usage['exports']}

=== DIAGRAM COMPLEXITY ===
Avg Nodes per Diagram: {quality['avg_nodes_per_diagram']}
Avg Edges per Diagram: {quality['avg_edges_per_diagram']}

=== PERFORMANCE ===
API Requests: {infra['lambda_invocations']}
Avg Response Time: {infra['avg_response_time_ms']}ms
Error Rate: {infra['error_rate']}%
Frontend Requests: {infra['cloudfront_requests']}

{"=== TOP ERRORS ===" if report['errors'] else "=== NO ERRORS ==="}
{chr(10).join([f"{err.get('error', 'Unknown')}: {err.get('error_count', 0)} occurrences" for err in report['errors'][:5]]) if report['errors'] else "No errors occurred this week!"}

---
Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/InfraSketch-Overview
    """

    return text.strip()


if __name__ == '__main__':
    report = generate_report()
    print(json.dumps(report, indent=2))
    print("\n" + "="*80 + "\n")
    print(format_text_email(report))
