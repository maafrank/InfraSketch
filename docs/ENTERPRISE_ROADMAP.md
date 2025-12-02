# InfraSketch Enterprise Readiness Roadmap

A checklist for making InfraSketch ready for use at global publicly traded companies.

---

## Enterprise Requirements Summary

Based on feedback from an enterprise architect, these are the requirements before InfraSketch can be considered:

| Requirement | Priority | Status |
|-------------|----------|--------|
| SOC2 Certification | High | ⬜ Not Started |
| Cyber Insurance | High | ⬜ Not Started |
| Penetration Test | High | ⬜ Not Started |
| Published SLAs | High | ⬜ Not Started |
| Published RPO/RTO | High | ⬜ Not Started |
| Hosting Platform Docs | Medium | ⬜ Not Started |
| Data Retention Policies | High | ⬜ Not Started |
| AI Usage Policies | Critical | ⬜ Not Started |

---

## Phase 1: Technical Security Hardening

### 1.1 Data Encryption at Rest
- [ ] Enable AWS KMS encryption on DynamoDB `infrasketch-sessions` table
  - [ ] Run: `aws dynamodb update-table --table-name infrasketch-sessions --sse-specification Enabled=true,SSEType=KMS`
  - [ ] Verify encryption is enabled in AWS Console
  - [ ] Document encryption key management policy

### 1.2 Security Headers
- [ ] Add security headers middleware to `backend/app/main.py`
  - [ ] `Strict-Transport-Security` (HSTS)
  - [ ] `X-Content-Type-Options: nosniff`
  - [ ] `X-Frame-Options: DENY`
  - [ ] `X-XSS-Protection: 1; mode=block`
  - [ ] `Content-Security-Policy`
- [ ] Test headers with securityheaders.com
- [ ] Deploy to production

### 1.3 Data Retention Controls
- [ ] Reduce DynamoDB TTL from 1 year to 30 days
  - [ ] Update `backend/app/session/dynamodb_storage.py`
  - [ ] Make TTL configurable via environment variable
  - [ ] Document retention period in policies
- [ ] Add data retention notice to UI

### 1.4 GDPR Compliance Endpoints
- [ ] Add `GET /api/user/data-export` endpoint
  - [ ] Export all user sessions as JSON
  - [ ] Include diagrams, conversations, design docs
- [ ] Add `DELETE /api/user/data` endpoint
  - [ ] Delete all user sessions
  - [ ] Add confirmation requirement
  - [ ] Log deletion for audit trail
- [ ] Add `GET /api/user/data-summary` endpoint
  - [ ] Show count of sessions, nodes, messages
  - [ ] Show data storage locations
- [ ] Add frontend UI for data management
  - [ ] "Export My Data" button
  - [ ] "Delete My Account" button with confirmation

### 1.5 Secrets Management
- [ ] Migrate all production secrets to AWS Secrets Manager
  - [ ] `ANTHROPIC_API_KEY`
  - [ ] `CLERK_SECRET_KEY`
- [ ] Update `backend/app/utils/secrets.py` to require Secrets Manager in production
- [ ] Remove secrets from Lambda environment variables
- [ ] Update `deploy-backend.sh` with Secrets Manager permissions
- [ ] Document secret rotation procedures

### 1.6 PII Screening for LLM
- [ ] Create `backend/app/utils/pii_screening.py`
  - [ ] Detect email addresses
  - [ ] Detect IP addresses
  - [ ] Detect API keys/passwords
  - [ ] Detect credit card numbers
  - [ ] Detect SSN patterns
- [ ] Integrate PII screening into `backend/app/agent/graph.py`
- [ ] Integrate PII screening into `backend/app/agent/doc_generator.py`
- [ ] Add warning to users when PII detected (not blocking, just warning)
- [ ] Log PII detection events (without logging the PII itself)

### 1.7 Enhanced Logging & Monitoring
- [ ] Set CloudWatch log retention to 90 days
  - [ ] Run: `aws logs put-retention-policy --log-group-name /aws/lambda/infrasketch-backend --retention-in-days 90`
- [ ] Enable CloudTrail for AWS API audit logging
- [ ] Add log scrubbing to remove any leaked PII
- [ ] Create security-focused CloudWatch dashboard
  - [ ] Failed authentication attempts
  - [ ] Rate limit violations
  - [ ] Error rate spikes
  - [ ] Unusual access patterns

---

## Phase 2: Policy Documentation

### 2.1 Privacy Policy
- [ ] Draft Privacy Policy covering:
  - [ ] What data is collected (diagrams, conversations, usage metadata)
  - [ ] How data is stored (AWS DynamoDB, encrypted at rest)
  - [ ] Data retention periods (30 days default)
  - [ ] Third-party data sharing (Anthropic, Clerk, AWS)
  - [ ] User rights (access, deletion, export, portability)
  - [ ] Cookie policy
  - [ ] Children's privacy (COPPA)
  - [ ] International data transfers
  - [ ] Contact information for privacy requests
- [ ] Have legal counsel review
- [ ] Publish at `infrasketch.net/legal/privacy`
- [ ] Add link to footer of all pages

### 2.2 Terms of Service
- [ ] Draft Terms of Service covering:
  - [ ] Service description
  - [ ] Account registration requirements
  - [ ] Acceptable use policy
  - [ ] Prohibited activities
  - [ ] Intellectual property (users own their diagrams)
  - [ ] Limitation of liability
  - [ ] Disclaimer of warranties
  - [ ] Service availability disclaimers
  - [ ] Termination rights
  - [ ] Dispute resolution
  - [ ] Governing law and jurisdiction
  - [ ] Changes to terms
- [ ] Have legal counsel review
- [ ] Publish at `infrasketch.net/legal/terms`
- [ ] Require acceptance on signup

### 2.3 AI/LLM Usage Policy (Critical)
- [ ] Draft AI Usage Policy covering:
  - [ ] What data is sent to Claude (prompts, diagrams, conversations)
  - [ ] Statement: "Anthropic does not use commercial API data for model training"
  - [ ] Link to Anthropic's data usage policy
  - [ ] How long Claude retains data (zero retention after request)
  - [ ] What Claude can and cannot do with data
  - [ ] Opt-out options (if any)
  - [ ] Enterprise options for enhanced privacy
- [ ] Get Anthropic's explicit confirmation of commercial API data policy
- [ ] Have legal counsel review
- [ ] Publish at `infrasketch.net/legal/ai-policy`
- [ ] Add AI usage notice to diagram generation UI

### 2.4 Security Policy
- [ ] Draft Security Policy covering:
  - [ ] Security architecture overview
  - [ ] Encryption standards (at rest, in transit)
  - [ ] Authentication methods (Clerk, JWT)
  - [ ] Access controls
  - [ ] Network security
  - [ ] Vulnerability management
  - [ ] Incident response overview
  - [ ] Security contact (security@infrasketch.net)
- [ ] Publish at `infrasketch.net/legal/security`
- [ ] Set up security@infrasketch.net email

### 2.5 Data Processing Agreement (DPA)
- [ ] Draft DPA template for enterprise customers
  - [ ] Data processor vs controller definitions
  - [ ] Processing instructions
  - [ ] Sub-processors list (Anthropic, AWS, Clerk)
  - [ ] Data transfer mechanisms (EU-US)
  - [ ] Security measures
  - [ ] Breach notification procedures (72 hours)
  - [ ] Audit rights
  - [ ] Data deletion upon termination
- [ ] Have legal counsel review
- [ ] Make available for enterprise customers upon request

### 2.6 Vulnerability Disclosure Policy
- [ ] Draft responsible disclosure policy
  - [ ] How to report vulnerabilities
  - [ ] What's in scope
  - [ ] Safe harbor statement
  - [ ] Response timeline commitments
  - [ ] Recognition/rewards (if any)
- [ ] Publish at `infrasketch.net/security` or `/.well-known/security.txt`
- [ ] Set up security@infrasketch.net monitoring

---

## Phase 3: Infrastructure Hardening

### 3.1 Infrastructure as Code
- [ ] Create `infrastructure/` directory
- [ ] Set up Terraform (or CloudFormation)
- [ ] Define all AWS resources:
  - [ ] Lambda function
  - [ ] API Gateway
  - [ ] DynamoDB table (with encryption, PITR)
  - [ ] S3 buckets
  - [ ] CloudFront distribution
  - [ ] IAM roles and policies
  - [ ] Secrets Manager secrets
  - [ ] CloudWatch log groups
  - [ ] WAF rules
- [ ] Migrate from shell scripts to IaC deployment
- [ ] Set up state management (S3 backend for Terraform)
- [ ] Document infrastructure in README

### 3.2 Backup & Disaster Recovery
- [ ] Enable DynamoDB Point-in-Time Recovery (PITR)
  - [ ] Run: `aws dynamodb update-continuous-backups --table-name infrasketch-sessions --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true`
- [ ] Document backup procedures
- [ ] Test restore procedures
- [ ] Define and document RPO (Recovery Point Objective)
  - [ ] Target: 1 hour (achievable with PITR)
- [ ] Define and document RTO (Recovery Time Objective)
  - [ ] Target: 4 hours (Lambda redeploy + data restore)
- [ ] Create disaster recovery runbook

### 3.3 Web Application Firewall (WAF)
- [ ] Add AWS WAF to CloudFront
- [ ] Configure managed rule sets:
  - [ ] AWS Managed Rules - Common Rule Set
  - [ ] AWS Managed Rules - Known Bad Inputs
  - [ ] SQL Injection protection
  - [ ] XSS protection
- [ ] Configure rate limiting at edge
- [ ] Set up WAF logging
- [ ] Create WAF dashboard

### 3.4 DDoS Protection
- [ ] Verify AWS Shield Standard is enabled (automatic with CloudFront)
- [ ] Consider AWS Shield Advanced for enterprise tier
- [ ] Document DDoS mitigation capabilities

### 3.5 Network Security
- [ ] Consider VPC for Lambda (if needed for compliance)
- [ ] Review and document all security group rules
- [ ] Enable VPC Flow Logs (if using VPC)

---

## Phase 4: Service Level Agreement (SLA)

### 4.1 Define SLA Metrics
- [ ] Define uptime target
  - [ ] Recommended: 99.5% (allows ~43 hours downtime/year)
  - [ ] Or: 99.9% for enterprise tier (~8.7 hours/year)
- [ ] Define API response time targets
  - [ ] Diagram generation: < 60 seconds
  - [ ] Chat responses: < 30 seconds
  - [ ] Other API calls: < 2 seconds
- [ ] Define support response times
  - [ ] Critical issues: 4 hours
  - [ ] High priority: 24 hours
  - [ ] Normal priority: 72 hours

### 4.2 SLA Documentation
- [ ] Draft SLA document covering:
  - [ ] Service description
  - [ ] Uptime commitment
  - [ ] Planned maintenance windows
  - [ ] Exclusions (force majeure, user errors)
  - [ ] Monitoring and reporting
  - [ ] Service credits for outages
  - [ ] Claim procedures
- [ ] Have legal counsel review
- [ ] Publish at `infrasketch.net/legal/sla`

### 4.3 Monitoring for SLA
- [ ] Set up uptime monitoring (Pingdom, UptimeRobot, or AWS)
- [ ] Create status page (statuspage.io or similar)
- [ ] Set up alerting for SLA breaches
- [ ] Automate monthly uptime reporting

---

## Phase 5: Compliance Certifications

### 5.1 SOC2 Type 1 Preparation
- [ ] Document all security controls
- [ ] Implement change management process
  - [ ] Require PR reviews for all code changes
  - [ ] Require approval for production deployments
  - [ ] Maintain change log
- [ ] Create incident response playbook
  - [ ] Detection procedures
  - [ ] Escalation procedures
  - [ ] Communication templates
  - [ ] Post-incident review process
- [ ] Document vendor management
  - [ ] Anthropic security review
  - [ ] AWS compliance documentation
  - [ ] Clerk security review
- [ ] Gather evidence of controls (logs, screenshots, policies)
- [ ] Select SOC2 auditor
  - [ ] Options: Vanta, Drata, Secureframe (automated) or traditional firms
- [ ] Complete SOC2 Type 1 audit
- [ ] Address any findings
- [ ] Receive SOC2 Type 1 report

### 5.2 SOC2 Type 2 Preparation
- [ ] Maintain controls for 6+ months
- [ ] Collect continuous evidence
- [ ] Complete SOC2 Type 2 audit
- [ ] Receive SOC2 Type 2 report

### 5.3 Penetration Testing
- [ ] Define scope of penetration test
  - [ ] External network
  - [ ] API endpoints
  - [ ] Authentication/authorization
  - [ ] Data access controls
- [ ] Select penetration testing firm
  - [ ] Options: Cobalt, Synack, NCC Group, Bishop Fox
- [ ] Schedule and complete penetration test
- [ ] Receive penetration test report
- [ ] Remediate all critical/high findings
- [ ] Remediate medium findings
- [ ] Document accepted risks for low findings
- [ ] Obtain clean or remediated report for customers

### 5.4 Cyber Insurance
- [ ] Determine coverage needs
  - [ ] Data breach response
  - [ ] Business interruption
  - [ ] Regulatory fines
  - [ ] Third-party liability
  - [ ] Recommended coverage: $1-5M
- [ ] Get quotes from cyber insurance providers
- [ ] Complete security questionnaire for insurer
- [ ] Purchase cyber insurance policy
- [ ] Document certificate of insurance for customers

---

## Phase 6: Frontend & Trust Experience

### 6.1 Legal Pages
- [ ] Create React components for legal pages
  - [ ] `frontend/src/pages/Privacy.jsx`
  - [ ] `frontend/src/pages/Terms.jsx`
  - [ ] `frontend/src/pages/AIPolicy.jsx`
  - [ ] `frontend/src/pages/Security.jsx`
  - [ ] `frontend/src/pages/SLA.jsx`
- [ ] Add routes in React Router
- [ ] Add footer links to all legal pages
- [ ] Style legal pages consistently

### 6.2 Trust/Security Page
- [ ] Create Trust Center page at `infrasketch.net/trust`
  - [ ] Security overview
  - [ ] Compliance certifications (SOC2 badge when obtained)
  - [ ] Encryption standards
  - [ ] Data handling practices
  - [ ] Infrastructure overview
  - [ ] Penetration test summary (without sensitive details)
  - [ ] Links to all policies
  - [ ] Security contact

### 6.3 Consent & Transparency
- [ ] Add cookie/data consent banner
  - [ ] Explain data collection
  - [ ] Link to privacy policy
  - [ ] Allow acceptance/rejection
- [ ] Add AI usage notice before first diagram generation
  - [ ] Explain data sent to Claude
  - [ ] Link to AI policy
  - [ ] Require acknowledgment

### 6.4 User Data Management
- [ ] Create user settings/account page
  - [ ] View account information
  - [ ] View data summary
  - [ ] Export data button
  - [ ] Delete account button
- [ ] Add confirmation dialogs for destructive actions
- [ ] Send email confirmation for account deletion

---

## Phase 7: Enterprise Features (Future)

### 7.1 Enterprise Tier
- [ ] Define enterprise pricing
- [ ] Create enterprise feature set:
  - [ ] Enhanced SLA (99.9%)
  - [ ] Priority support
  - [ ] Custom data retention
  - [ ] Dedicated account manager
  - [ ] Custom DPA
  - [ ] Invoice billing

### 7.2 SSO/SAML Support
- [ ] Research Clerk enterprise SSO options
- [ ] Implement SAML authentication
- [ ] Implement OIDC authentication
- [ ] Test with common IdPs (Okta, Azure AD, Google Workspace)

### 7.3 Audit Logging
- [ ] Create detailed audit log for enterprise customers
  - [ ] User logins
  - [ ] Diagram creations/modifications
  - [ ] Data exports
  - [ ] Admin actions
- [ ] Provide audit log export capability
- [ ] Retain audit logs for 1 year

### 7.4 On-Premises / Self-Hosted Option
- [ ] Create Docker container for backend
- [ ] Create deployment documentation
- [ ] Support customer-provided Anthropic API keys
- [ ] Remove dependency on Clerk (or make optional)
- [ ] Create installation guide

### 7.5 Data Residency Options
- [ ] Deploy to EU region (eu-west-1)
- [ ] Allow customers to choose data region
- [ ] Ensure Anthropic API supports region requirements

---

## Estimated Costs

| Item | One-Time | Annual | Notes |
|------|----------|--------|-------|
| Legal review (policies) | $3,000-10,000 | - | Varies by firm |
| SOC2 Type 1 (automated platform) | $15,000-30,000 | - | Vanta, Drata, etc. |
| SOC2 Type 2 | - | $20,000-40,000 | After 6 months |
| Penetration test | $10,000-30,000 | $10,000-30,000 | Annual refresh |
| Cyber insurance | - | $3,000-10,000 | Based on coverage |
| AWS WAF | - | $500-2,000 | Usage-based |
| Status page (Statuspage.io) | - | $500-1,500 | Or free alternatives |
| Uptime monitoring | - | $100-500 | Pingdom, etc. |
| **Total Year 1** | **~$30,000-70,000** | **~$35,000-85,000** | |

---

## Quick Reference: Key Files to Modify

### Backend
- `backend/app/main.py` - Security headers
- `backend/app/api/routes.py` - GDPR endpoints
- `backend/app/session/dynamodb_storage.py` - TTL, encryption docs
- `backend/app/utils/secrets.py` - Secrets Manager
- `backend/app/utils/pii_screening.py` - New file
- `backend/app/agent/graph.py` - PII integration

### Frontend
- `frontend/src/App.jsx` - Routes
- `frontend/src/pages/` - New legal pages
- `frontend/src/components/ConsentBanner.jsx` - New
- `frontend/src/components/UserSettings.jsx` - New

### Infrastructure
- `infrastructure/` - New Terraform directory
- `deploy-backend.sh` - IaC integration

### Documentation
- `docs/SECURITY.md` - New
- `docs/INCIDENT_RESPONSE.md` - New
- `docs/DISASTER_RECOVERY.md` - New

---

## Progress Tracking

Last updated: ____________

| Phase | Status | Completion |
|-------|--------|------------|
| Phase 1: Technical Security | ⬜ Not Started | 0% |
| Phase 2: Policy Documentation | ⬜ Not Started | 0% |
| Phase 3: Infrastructure | ⬜ Not Started | 0% |
| Phase 4: SLA | ⬜ Not Started | 0% |
| Phase 5: Compliance | ⬜ Not Started | 0% |
| Phase 6: Frontend/Trust | ⬜ Not Started | 0% |
| Phase 7: Enterprise Features | ⬜ Not Started | 0% |

**Overall Progress: 0%**
