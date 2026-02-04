"""
Prompts for generating architecture diagrams from GitHub repository analysis.
"""

REPO_ANALYSIS_PROMPT = """You are an expert system architect. Based on the following repository analysis, generate a system architecture diagram that accurately represents the application's structure.

## Repository Information
- **Name**: {repo_name}
- **Owner**: {owner}
- **Description**: {description}
- **Primary Language**: {primary_language}
- **Languages Used**: {languages}

## Dependencies
{dependencies}

## Infrastructure
- **Docker**: {has_docker}
{docker_details}
- **Kubernetes**: {has_kubernetes}
{kubernetes_details}
- **Terraform**: {has_terraform}
- **CI/CD**: {ci_cd}

## Code Analysis
### Entry Points
{entry_points}

### API Routes Detected
{api_routes}

### Database Connections
{databases}

### External Services
{external_services}

## File Structure
{file_structure}

## README Summary
{readme_summary}

---

## Instructions

Based on this analysis, generate a system architecture diagram that:

1. **Shows the main application layers**:
   - If it's a web app: frontend, backend/API, database layers
   - If it's a service: entry points, processing, storage
   - If it's a CLI: command handlers, core logic, output

2. **Uses specific technologies** from the analysis:
   - Use actual database names (e.g., "PostgreSQL" not "database")
   - Use actual service names (e.g., "Redis Cache" not "cache")
   - Use actual frameworks (e.g., "FastAPI" not "API")

3. **Includes detected integrations**:
   - External services (AWS, Stripe, etc.)
   - Message queues if detected
   - Caching layers if detected

4. **Keeps it focused**:
   - 4-8 nodes maximum
   - Every node must be connected
   - Include a client/entry point node
   - Omit generic infrastructure (load balancers, monitoring) unless explicitly present

## Output Format

Output ONLY valid JSON in this exact format (no markdown, no explanations):

{{
  "nodes": [
    {{
      "id": "unique-id",
      "type": "cache|database|api|server|loadbalancer|queue|cdn|gateway|storage|service",
      "label": "Component Name",
      "description": "Brief description of what this component does",
      "inputs": ["What flows into this component"],
      "outputs": ["What this component produces"],
      "metadata": {{
        "technology": "Specific technology (e.g., PostgreSQL, Redis, FastAPI)",
        "notes": "Additional implementation details"
      }}
    }}
  ],
  "edges": [
    {{
      "id": "edge-id",
      "source": "source-node-id",
      "target": "target-node-id",
      "label": "Description of data/action flow",
      "type": "default"
    }}
  ]
}}

Remember:
- Every node MUST be connected via edges
- Use technology-specific labels (not generic ones)
- Keep descriptions concise but informative
- IDs should be lowercase with hyphens (e.g., "postgres-db", "api-server")
"""


def format_repo_analysis_prompt(analysis) -> str:
    """
    Format the REPO_ANALYSIS_PROMPT with data from a RepoAnalysis object.

    Args:
        analysis: RepoAnalysis dataclass instance

    Returns:
        Formatted prompt string ready for Claude
    """
    # Format dependencies
    deps_lines = []
    for lang, pkgs in analysis.dependencies.items():
        if pkgs:
            deps_lines.append(f"**{lang}**: {', '.join(pkgs[:15])}")
            if len(pkgs) > 15:
                deps_lines.append(f"  ... and {len(pkgs) - 15} more")
    dependencies = "\n".join(deps_lines) if deps_lines else "No dependencies detected"

    # Format Docker details
    docker_details = ""
    if analysis.has_docker and analysis.docker_services:
        docker_details = f"  - Services: {', '.join(analysis.docker_services)}"

    # Format Kubernetes details
    kubernetes_details = ""
    if analysis.has_kubernetes and analysis.kubernetes_resources:
        kubernetes_details = f"  - Resources: {', '.join(set(analysis.kubernetes_resources))}"

    # Format CI/CD
    ci_cd = analysis.ci_cd_platform if analysis.has_ci_cd else "Not detected"

    # Format entry points
    entry_points = "\n".join(f"- {ep}" for ep in analysis.entry_points) if analysis.entry_points else "Not detected"

    # Format API routes
    if analysis.api_routes:
        routes = []
        for route in analysis.api_routes[:10]:
            if "method" in route:
                routes.append(f"- {route.get('method', 'GET')} {route.get('path', '/')}")
            else:
                routes.append(f"- {route.get('path', '/')}")
        api_routes = "\n".join(routes)
        if len(analysis.api_routes) > 10:
            api_routes += f"\n... and {len(analysis.api_routes) - 10} more routes"
    else:
        api_routes = "No routes detected"

    # Format databases
    databases = ", ".join(analysis.database_connections) if analysis.database_connections else "Not detected"

    # Format external services
    external_services = ", ".join(analysis.external_services) if analysis.external_services else "Not detected"

    # Format file structure
    dirs = analysis.file_structure.get("dirs", [])
    files = analysis.file_structure.get("files", [])
    structure_lines = []
    if dirs:
        structure_lines.append("**Directories**: " + ", ".join(dirs[:10]))
    if files:
        structure_lines.append("**Key files**: " + ", ".join(files[:10]))
    file_structure = "\n".join(structure_lines) if structure_lines else "Unable to fetch"

    # Format languages
    if analysis.languages:
        total_bytes = sum(analysis.languages.values())
        lang_strs = []
        for lang, bytes_count in sorted(analysis.languages.items(), key=lambda x: -x[1])[:5]:
            pct = (bytes_count / total_bytes) * 100
            lang_strs.append(f"{lang} ({pct:.0f}%)")
        languages = ", ".join(lang_strs)
    else:
        languages = analysis.primary_language or "Unknown"

    return REPO_ANALYSIS_PROMPT.format(
        repo_name=analysis.name,
        owner=analysis.owner,
        description=analysis.description or "No description provided",
        primary_language=analysis.primary_language or "Unknown",
        languages=languages,
        dependencies=dependencies,
        has_docker="Yes" if analysis.has_docker else "No",
        docker_details=docker_details,
        has_kubernetes="Yes" if analysis.has_kubernetes else "No",
        kubernetes_details=kubernetes_details,
        has_terraform="Yes" if analysis.has_terraform else "No",
        ci_cd=ci_cd,
        entry_points=entry_points,
        api_routes=api_routes,
        databases=databases,
        external_services=external_services,
        file_structure=file_structure,
        readme_summary=analysis.readme_summary or "No README found",
    )
