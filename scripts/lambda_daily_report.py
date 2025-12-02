"""
AWS Lambda function for sending daily InfraSketch usage reports.
This function is triggered by EventBridge on a daily schedule.

Reports include:
- Daily unique users
- Feature usage counts (diagrams, chat, design docs, exports)
- Top 5 prompts/questions
- User locations (from CloudFront logs)
"""

import boto3
import json
import gzip
from datetime import datetime, timedelta
from collections import defaultdict
from io import BytesIO

cloudwatch = boto3.client('cloudwatch', region_name='us-east-1')
logs = boto3.client('logs', region_name='us-east-1')
ses = boto3.client('ses', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

# Configuration
SENDER_EMAIL = "reports@infrasketch.net"
RECIPIENT_EMAIL = "mattafrank2439@gmail.com"
CLOUDFRONT_LOGS_BUCKET = "infrasketch-cloudfront-logs-059409992371"
CLOUDFRONT_LOGS_PREFIX = "cloudfront/"


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

        import time
        max_wait = 60
        waited = 0
        while waited < max_wait:
            time.sleep(2)
            waited += 2
            result = logs.get_query_results(queryId=query_id)
            if result['status'] == 'Complete':
                return result.get('results', [])
            elif result['status'] == 'Failed':
                print(f"Query failed: {query_string}")
                return []

        print(f"Query timeout: {query_string}")
        return []
    except Exception as e:
        print(f"Error querying logs: {e}")
        return []


def extract_value(results, field_name, default=0):
    """Extract value from CloudWatch Logs query results."""
    if not results or not results[0]:
        return default
    for item in results[0]:
        if item.get('field') == field_name:
            try:
                return float(item.get('value', default))
            except (ValueError, TypeError):
                return default
    return default


def get_edge_locations_from_cloudfront(start_time, end_time):
    """
    Parse CloudFront logs to get edge location distribution.
    Returns dict of {edge_location: count}
    """
    edge_locations = defaultdict(int)

    try:
        # List log files for the date range
        # CloudFront logs are stored as: prefix/DISTRIBUTION_ID.YYYY-MM-DD-HH.uniqueID.gz
        current_date = start_time.date()
        end_date = end_time.date()

        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            prefix = f"{CLOUDFRONT_LOGS_PREFIX}E2YM028NUBX2QN.{date_str}"

            try:
                paginator = s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=CLOUDFRONT_LOGS_BUCKET, Prefix=prefix):
                    for obj in page.get('Contents', []):
                        try:
                            # Download and decompress log file
                            response = s3.get_object(Bucket=CLOUDFRONT_LOGS_BUCKET, Key=obj['Key'])
                            compressed = BytesIO(response['Body'].read())

                            with gzip.GzipFile(fileobj=compressed) as f:
                                for line in f:
                                    line = line.decode('utf-8').strip()
                                    if line.startswith('#') or not line:
                                        continue

                                    # CloudFront log format:
                                    # 0: date, 1: time, 2: x-edge-location, 3: sc-bytes, 4: c-ip, ...
                                    fields = line.split('\t')
                                    if len(fields) > 2:
                                        edge_loc = fields[2]  # x-edge-location (e.g., "YUL62-C2")
                                        edge_locations[edge_loc] += 1
                        except Exception as e:
                            print(f"Error processing log file {obj['Key']}: {e}")
                            continue
            except Exception as e:
                print(f"Error listing logs for {date_str}: {e}")

            current_date += timedelta(days=1)

    except Exception as e:
        print(f"Error getting CloudFront logs: {e}")

    return dict(edge_locations)


def edge_location_to_region(edge_code):
    """Map CloudFront edge location code to human-readable region."""
    # Edge location codes follow pattern: IATA + number + optional suffix
    # e.g., "YUL62-C2", "IAD89-P1", "SFO20-C3"
    # Extract the 3-letter IATA code from the beginning
    import re
    match = re.match(r'^([A-Z]{3})', edge_code)
    iata = match.group(1) if match else edge_code[:3]

    # Map IATA codes to regions (common ones)
    region_map = {
        # North America
        'IAD': 'Virginia, USA',
        'DFW': 'Texas, USA',
        'SEA': 'Seattle, USA',
        'SFO': 'San Francisco, USA',
        'LAX': 'Los Angeles, USA',
        'ORD': 'Chicago, USA',
        'JFK': 'New York, USA',
        'MIA': 'Miami, USA',
        'ATL': 'Atlanta, USA',
        'YYZ': 'Toronto, Canada',
        'YVR': 'Vancouver, Canada',
        'YUL': 'Montreal, Canada',

        # Europe
        'LHR': 'London, UK',
        'FRA': 'Frankfurt, Germany',
        'CDG': 'Paris, France',
        'AMS': 'Amsterdam, Netherlands',
        'DUB': 'Dublin, Ireland',
        'MXP': 'Milan, Italy',
        'MAD': 'Madrid, Spain',
        'ARN': 'Stockholm, Sweden',

        # Asia Pacific
        'NRT': 'Tokyo, Japan',
        'HND': 'Tokyo, Japan',
        'ICN': 'Seoul, South Korea',
        'SIN': 'Singapore',
        'HKG': 'Hong Kong',
        'SYD': 'Sydney, Australia',
        'MEL': 'Melbourne, Australia',
        'BOM': 'Mumbai, India',
        'DEL': 'Delhi, India',

        # South America
        'GRU': 'São Paulo, Brazil',
        'EZE': 'Buenos Aires, Argentina',
        'BOG': 'Bogotá, Colombia',
        'SCL': 'Santiago, Chile',

        # Middle East / Africa
        'DXB': 'Dubai, UAE',
        'BAH': 'Bahrain',
        'CPT': 'Cape Town, South Africa',
        'JNB': 'Johannesburg, South Africa',
    }

    return region_map.get(iata, f"Other ({iata})")


def generate_report():
    """Generate daily usage report."""
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)

    print(f"Generating daily report for {start_time.date()}")

    # === FEATURE USAGE COUNTS ===
    # Note: Using @message like pattern matching because Lambda logs have a prefix
    # before the JSON that prevents automatic JSON field parsing

    # Diagrams created
    diagrams_result = query_logs(
        'fields @message | filter @message like /"event_type": "diagram_generated"/ | stats count() as total',
        start_time,
        end_time
    )
    diagrams_count = int(extract_value(diagrams_result, 'total'))

    # Chat interactions
    chat_result = query_logs(
        'fields @message | filter @message like /"event_type": "chat_message"/ | stats count() as total',
        start_time,
        end_time
    )
    chat_count = int(extract_value(chat_result, 'total'))

    # Design doc generations
    design_doc_result = query_logs(
        'fields @message | filter @message like /"event_type": "design_doc_generated"/ | stats count() as total',
        start_time,
        end_time
    )
    design_doc_count = int(extract_value(design_doc_result, 'total'))

    # Exports
    export_result = query_logs(
        'fields @message | filter @message like /"event_type": "export_design_doc"/ | stats count() as total',
        start_time,
        end_time
    )
    export_count = int(extract_value(export_result, 'total'))

    # Node operations (manual adds/deletes/updates)
    node_ops_result = query_logs(
        'fields @message | filter @message like /node_added/ or @message like /node_deleted/ or @message like /node_updated/ | stats count() as total',
        start_time,
        end_time
    )
    node_ops_count = int(extract_value(node_ops_result, 'total'))

    # Unique users (by IP) - parse the user_ip from JSON
    users_result = query_logs(
        '''
        fields @message
        | filter @message like /"event_type": "diagram_generated"/ or @message like /"event_type": "chat_message"/
        | parse @message /"user_ip": "(?<user_ip>[^"]+)"/
        | stats count_distinct(user_ip) as unique_users
        ''',
        start_time,
        end_time
    )
    unique_users = int(extract_value(users_result, 'unique_users'))

    # === TOP 5 PROMPTS ===
    # Parse prompt from JSON in log message
    top_prompts_result = query_logs(
        '''
        fields @message
        | filter @message like /"event_type": "diagram_generated"/
        | parse @message /"prompt": "(?<prompt>[^"]+)"/
        | filter ispresent(prompt)
        | stats count() as count by prompt
        | sort count desc
        | limit 5
        ''',
        start_time,
        end_time
    )

    top_prompts = []
    for result in top_prompts_result:
        prompt_data = {}
        for item in result:
            field = item.get('field')
            value = item.get('value')
            if field == 'prompt':
                prompt_data['prompt'] = value[:100] + "..." if len(value) > 100 else value
            elif field == 'count':
                prompt_data['count'] = int(float(value))
        if prompt_data:
            top_prompts.append(prompt_data)

    # === TOP 5 CHAT QUESTIONS ===
    # Parse message from JSON in log message
    top_questions_result = query_logs(
        '''
        fields @message
        | filter @message like /"event_type": "chat_message"/
        | parse @message /"message": "(?<message>[^"]+)"/
        | filter ispresent(message)
        | stats count() as count by message
        | sort count desc
        | limit 5
        ''',
        start_time,
        end_time
    )

    top_questions = []
    for result in top_questions_result:
        question_data = {}
        for item in result:
            field = item.get('field')
            value = item.get('value')
            if field == 'message':
                question_data['question'] = value[:100] + "..." if len(value) > 100 else value
            elif field == 'count':
                question_data['count'] = int(float(value))
        if question_data:
            top_questions.append(question_data)

    # === USER LOCATIONS ===
    edge_locations = get_edge_locations_from_cloudfront(start_time, end_time)

    # Convert edge locations to regions and aggregate
    region_counts = defaultdict(int)
    for edge_code, count in edge_locations.items():
        region = edge_location_to_region(edge_code)
        region_counts[region] += count

    # Sort by count and get top 10
    top_locations = sorted(region_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    report = {
        'date': start_time.strftime('%Y-%m-%d'),
        'unique_users': unique_users,
        'feature_usage': {
            'diagrams_created': diagrams_count,
            'chat_interactions': chat_count,
            'design_docs_generated': design_doc_count,
            'exports': export_count,
            'node_operations': node_ops_count,
        },
        'top_prompts': top_prompts,
        'top_questions': top_questions,
        'user_locations': top_locations,
    }

    return report


def format_html_email(report):
    """Format report as HTML email."""
    date = report['date']
    usage = report['feature_usage']

    # Total interactions
    total_interactions = sum(usage.values())

    # Format top prompts
    prompts_html = ""
    if report['top_prompts']:
        prompts_html = "<ol>"
        for p in report['top_prompts']:
            prompts_html += f"<li><strong>{p.get('prompt', 'N/A')}</strong> ({p.get('count', 0)} times)</li>"
        prompts_html += "</ol>"
    else:
        prompts_html = "<p>No diagram prompts recorded today.</p>"

    # Format top questions
    questions_html = ""
    if report['top_questions']:
        questions_html = "<ol>"
        for q in report['top_questions']:
            questions_html += f"<li><strong>{q.get('question', 'N/A')}</strong> ({q.get('count', 0)} times)</li>"
        questions_html += "</ol>"
    else:
        questions_html = "<p>No chat questions recorded today.</p>"

    # Format locations
    locations_html = ""
    if report['user_locations']:
        locations_html = "<table><tr><th>Location</th><th>Requests</th></tr>"
        for location, count in report['user_locations']:
            locations_html += f"<tr><td>{location}</td><td>{count:,}</td></tr>"
        locations_html += "</table>"
    else:
        locations_html = "<p>No location data available.</p>"

    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
            h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #34495e; margin-top: 30px; border-left: 4px solid #3498db; padding-left: 10px; }}
            .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 20px 0; }}
            .metric-card {{ background: #f8f9fa; border-left: 4px solid #3498db; padding: 15px; border-radius: 4px; }}
            .metric-value {{ font-size: 32px; font-weight: bold; color: #2c3e50; margin: 5px 0; }}
            .metric-label {{ font-size: 14px; color: #7f8c8d; text-transform: uppercase; }}
            .highlight {{ background: #e8f4f8; padding: 15px; border-radius: 4px; margin: 15px 0; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
            th {{ background: #3498db; color: white; }}
            ol {{ margin: 10px 0; padding-left: 20px; }}
            li {{ margin: 8px 0; }}
            .footer {{ margin-top: 40px; padding-top: 20px; border-top: 2px solid #ecf0f1; font-size: 12px; color: #95a5a6; }}
        </style>
    </head>
    <body>
        <h1>📊 InfraSketch Daily Report</h1>
        <p><strong>Date:</strong> {date}</p>

        <h2>👥 Users</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Unique Users</div>
                <div class="metric-value">{report['unique_users']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total Interactions</div>
                <div class="metric-value">{total_interactions}</div>
            </div>
        </div>

        <h2>⚡ Feature Usage</h2>
        <div class="metric-grid">
            <div class="metric-card">
                <div class="metric-label">Diagrams Created</div>
                <div class="metric-value">{usage['diagrams_created']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Chat Messages</div>
                <div class="metric-value">{usage['chat_interactions']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Design Docs</div>
                <div class="metric-value">{usage['design_docs_generated']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Exports</div>
                <div class="metric-value">{usage['exports']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Node Edits</div>
                <div class="metric-value">{usage['node_operations']}</div>
            </div>
        </div>

        <h2>💡 Top 5 Diagram Prompts</h2>
        {prompts_html}

        <h2>💬 Top 5 Chat Questions</h2>
        {questions_html}

        <h2>🌍 User Locations (by CloudFront edge)</h2>
        {locations_html}

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
    date = report['date']
    usage = report['feature_usage']
    total = sum(usage.values())

    # Format prompts
    prompts_text = ""
    for i, p in enumerate(report['top_prompts'], 1):
        prompts_text += f"  {i}. {p.get('prompt', 'N/A')} ({p.get('count', 0)} times)\n"
    if not prompts_text:
        prompts_text = "  No prompts recorded\n"

    # Format questions
    questions_text = ""
    for i, q in enumerate(report['top_questions'], 1):
        questions_text += f"  {i}. {q.get('question', 'N/A')} ({q.get('count', 0)} times)\n"
    if not questions_text:
        questions_text = "  No questions recorded\n"

    # Format locations
    locations_text = ""
    for location, count in report['user_locations']:
        locations_text += f"  {location}: {count:,} requests\n"
    if not locations_text:
        locations_text = "  No location data\n"

    text = f"""
InfraSketch Daily Report
Date: {date}

=== USERS ===
Unique Users: {report['unique_users']}
Total Interactions: {total}

=== FEATURE USAGE ===
Diagrams Created: {usage['diagrams_created']}
Chat Messages: {usage['chat_interactions']}
Design Docs Generated: {usage['design_docs_generated']}
Exports: {usage['exports']}
Node Operations: {usage['node_operations']}

=== TOP 5 DIAGRAM PROMPTS ===
{prompts_text}
=== TOP 5 CHAT QUESTIONS ===
{questions_text}
=== USER LOCATIONS ===
{locations_text}
---
Dashboard: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards/dashboard/InfraSketch-Overview
    """

    return text.strip()


def send_email(report):
    """Send email via SES."""
    html_body = format_html_email(report)
    text_body = format_text_email(report)

    subject = f"📊 InfraSketch Daily Report - {report['date']}"

    try:
        response = ses.send_email(
            Source=SENDER_EMAIL,
            Destination={
                'ToAddresses': [RECIPIENT_EMAIL]
            },
            Message={
                'Subject': {
                    'Data': subject,
                    'Charset': 'UTF-8'
                },
                'Body': {
                    'Text': {
                        'Data': text_body,
                        'Charset': 'UTF-8'
                    },
                    'Html': {
                        'Data': html_body,
                        'Charset': 'UTF-8'
                    }
                }
            }
        )

        print(f"Email sent! Message ID: {response['MessageId']}")
        return response
    except Exception as e:
        print(f"Error sending email: {e}")
        raise


def lambda_handler(event, context):
    """Lambda handler function."""
    print("Starting daily report generation...")

    try:
        # Generate report
        report = generate_report()
        print(f"Report generated: {json.dumps(report, indent=2)}")

        # Send email
        send_email(report)

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Daily report sent successfully',
                'report': report
            })
        }
    except Exception as e:
        print(f"Error in lambda_handler: {e}")
        import traceback
        traceback.print_exc()

        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error generating daily report',
                'error': str(e)
            })
        }
