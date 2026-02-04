"""
GitHub repository analyzer for architecture extraction.

Fetches repository data via GitHub API and performs deep code analysis
to extract architectural patterns, dependencies, and infrastructure.
"""

import base64
import re
import json
from dataclasses import dataclass, field
from typing import Optional
import httpx


@dataclass
class RepoAnalysis:
    """Structured analysis of a GitHub repository."""

    repo_url: str
    owner: str
    name: str
    description: Optional[str] = None
    default_branch: str = "main"
    primary_language: Optional[str] = None
    languages: dict = field(default_factory=dict)

    # Dependency analysis
    dependencies: dict = field(default_factory=dict)

    # Infrastructure hints
    has_docker: bool = False
    docker_services: list = field(default_factory=list)
    has_kubernetes: bool = False
    kubernetes_resources: list = field(default_factory=list)
    has_terraform: bool = False
    terraform_resources: list = field(default_factory=list)
    has_ci_cd: bool = False
    ci_cd_platform: Optional[str] = None

    # Code structure
    entry_points: list = field(default_factory=list)
    api_routes: list = field(default_factory=list)
    database_connections: list = field(default_factory=list)
    external_services: list = field(default_factory=list)

    # README content
    readme_summary: Optional[str] = None

    # File tree (simplified)
    file_structure: dict = field(default_factory=dict)

    # Raw file contents for context
    key_files: dict = field(default_factory=dict)


# Language-specific patterns for code analysis
LANGUAGE_PATTERNS = {
    "python": {
        "imports": r"^(?:from|import)\s+([\w.]+)",
        "routes": [
            r"@(?:app|router|api|bp|blueprint)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)",
            r"@(?:app|router|api)\.(route)\s*\(\s*['\"]([^'\"]+)",
            r"path\s*\(\s*['\"]([^'\"]+)['\"]",
        ],
        "db_patterns": [
            (r"(?:postgresql|postgres)://", "PostgreSQL"),
            (r"mysql://", "MySQL"),
            (r"mongodb://|pymongo", "MongoDB"),
            (r"redis://|import redis|from redis", "Redis"),
            (r"sqlite://|sqlite3", "SQLite"),
            (r"sqlalchemy", "SQLAlchemy ORM"),
            (r"from prisma|import prisma", "Prisma"),
            (r"from tortoise|import tortoise", "Tortoise ORM"),
        ],
        "services": [
            (r"boto3|import boto3|from boto3", "AWS SDK"),
            (r"stripe\.|import stripe", "Stripe"),
            (r"sendgrid|from sendgrid", "SendGrid"),
            (r"twilio|from twilio", "Twilio"),
            (r"openai\.|import openai", "OpenAI"),
            (r"anthropic\.|import anthropic", "Anthropic"),
            (r"resend\.|import resend", "Resend"),
            (r"firebase_admin|import firebase", "Firebase"),
            (r"google\.cloud", "Google Cloud"),
            (r"azure\.", "Azure SDK"),
        ],
    },
    "javascript": {
        "imports": r"(?:import\s+.*?\s+from\s+['\"]|require\s*\(\s*['\"])([^'\"]+)",
        "routes": [
            r"(?:app|router|server)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)",
            r"\.route\s*\(\s*['\"]([^'\"]+)",
        ],
        "db_patterns": [
            (r"mongoose|mongodb", "MongoDB"),
            (r"sequelize", "Sequelize ORM"),
            (r"prisma|@prisma/client", "Prisma"),
            (r"knex", "Knex.js"),
            (r"pg|postgres", "PostgreSQL"),
            (r"mysql2?", "MySQL"),
            (r"redis|ioredis", "Redis"),
            (r"typeorm", "TypeORM"),
            (r"drizzle", "Drizzle ORM"),
        ],
        "services": [
            (r"aws-sdk|@aws-sdk", "AWS SDK"),
            (r"stripe", "Stripe"),
            (r"@sendgrid", "SendGrid"),
            (r"twilio", "Twilio"),
            (r"openai", "OpenAI"),
            (r"@anthropic-ai", "Anthropic"),
            (r"resend", "Resend"),
            (r"firebase|firebase-admin", "Firebase"),
            (r"@google-cloud", "Google Cloud"),
            (r"@azure", "Azure SDK"),
        ],
    },
    "go": {
        "imports": r"import\s+(?:\(\s*)?\"([^\"]+)\"",
        "routes": [
            r"(?:Get|Post|Put|Delete|Patch|Handle|HandleFunc)\s*\(\s*\"([^\"]+)\"",
            r"\.(?:GET|POST|PUT|DELETE|PATCH)\s*\(\s*\"([^\"]+)\"",
        ],
        "db_patterns": [
            (r"database/sql|lib/pq", "PostgreSQL"),
            (r"go-sql-driver/mysql", "MySQL"),
            (r"mongo-driver", "MongoDB"),
            (r"go-redis|redis", "Redis"),
            (r"gorm", "GORM"),
            (r"sqlx", "sqlx"),
        ],
        "services": [
            (r"aws-sdk-go", "AWS SDK"),
            (r"stripe-go", "Stripe"),
            (r"twilio-go", "Twilio"),
        ],
    },
    "rust": {
        "imports": r"use\s+([\w:]+)",
        "routes": [
            r"\.route\s*\(\s*\"([^\"]+)\"",
            r"#\[(?:get|post|put|delete|patch)\s*\(\s*\"([^\"]+)\"",
        ],
        "db_patterns": [
            (r"diesel|sqlx", "PostgreSQL/MySQL"),
            (r"mongodb", "MongoDB"),
            (r"redis", "Redis"),
            (r"sea-orm|sea_orm", "SeaORM"),
        ],
        "services": [
            (r"aws-sdk", "AWS SDK"),
            (r"stripe", "Stripe"),
        ],
    },
    "java": {
        "imports": r"import\s+([\w.]+);",
        "routes": [
            r"@(?:Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*)?\"([^\"]+)\"",
            r"@RequestMapping\s*\(\s*(?:value\s*=\s*)?\"([^\"]+)\"",
        ],
        "db_patterns": [
            (r"jdbc:postgresql", "PostgreSQL"),
            (r"jdbc:mysql", "MySQL"),
            (r"mongodb", "MongoDB"),
            (r"redis", "Redis"),
            (r"hibernate|jpa", "Hibernate/JPA"),
        ],
        "services": [
            (r"software\.amazon\.awssdk", "AWS SDK"),
            (r"com\.stripe", "Stripe"),
        ],
    },
}

# File priorities for analysis
PRIORITY_FILES = {
    1: [
        "package.json",
        "requirements.txt",
        "pyproject.toml",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "Gemfile",
        "composer.json",
    ],
    2: [
        "docker-compose.yml",
        "docker-compose.yaml",
        "Dockerfile",
        ".dockerignore",
    ],
    3: [
        "README.md",
        "README.rst",
        "readme.md",
        "ARCHITECTURE.md",
    ],
    4: [
        "main.py",
        "app.py",
        "index.js",
        "index.ts",
        "main.go",
        "main.rs",
        "server.py",
        "server.js",
        "server.ts",
    ],
}

# Directories to analyze for source code
SOURCE_DIRS = [
    "src",
    "lib",
    "app",
    "api",
    "routes",
    "services",
    "controllers",
    "handlers",
    "internal",
    "pkg",
    "cmd",
    "backend",
    "server",
]


class GitHubAnalyzerError(Exception):
    """Base exception for GitHub analyzer errors."""
    pass


class RepoNotFoundError(GitHubAnalyzerError):
    """Repository not found."""
    pass


class RepoAccessDeniedError(GitHubAnalyzerError):
    """Access to repository denied (private repo without token)."""
    pass


class GitHubRateLimitError(GitHubAnalyzerError):
    """GitHub API rate limit exceeded."""

    def __init__(self, reset_time: int, message: str = "Rate limit exceeded"):
        self.reset_time = reset_time
        super().__init__(message)


class GitHubAnalyzer:
    """Fetches and analyzes GitHub repositories."""

    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize the analyzer.

        Args:
            access_token: Optional GitHub personal access token for private repos
                         and higher rate limits.
        """
        self.access_token = access_token
        self.base_url = "https://api.github.com"
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        """Lazy-initialize HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=30.0)
        return self._client

    def _get_headers(self) -> dict:
        """Get headers for GitHub API requests."""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "InfraSketch-Analyzer",
        }
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def _check_rate_limit(self, response: httpx.Response) -> None:
        """Check and raise if rate limited."""
        if response.status_code == 403:
            remaining = response.headers.get("X-RateLimit-Remaining", "0")
            if remaining == "0":
                reset_time = int(response.headers.get("X-RateLimit-Reset", "0"))
                raise GitHubRateLimitError(reset_time)

    def parse_github_url(self, url: str) -> tuple[str, str]:
        """
        Extract owner and repo name from GitHub URL.

        Handles formats:
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - github.com/owner/repo
        - git@github.com:owner/repo.git

        Returns:
            Tuple of (owner, repo_name)

        Raises:
            ValueError: If URL is not a valid GitHub repository URL
        """
        patterns = [
            r"github\.com[:/]([^/]+)/([^/\s.]+?)(?:\.git)?(?:\s|$|/)",
            r"github\.com[:/]([^/]+)/([^/\s]+)",
        ]

        url = url.strip()

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                owner = match.group(1)
                repo = match.group(2)
                # Remove .git suffix if present (use removesuffix, not rstrip)
                if repo.endswith(".git"):
                    repo = repo[:-4]
                return owner, repo

        raise ValueError(
            f"Invalid GitHub URL: {url}. "
            "Expected format: https://github.com/owner/repo"
        )

    def analyze_repo(self, repo_url: str) -> RepoAnalysis:
        """
        Perform full repository analysis.

        Args:
            repo_url: GitHub repository URL

        Returns:
            RepoAnalysis with all extracted information
        """
        owner, repo = self.parse_github_url(repo_url)

        # Get repo metadata
        metadata = self._get_repo_metadata(owner, repo)

        analysis = RepoAnalysis(
            repo_url=repo_url,
            owner=owner,
            name=repo,
            description=metadata.get("description"),
            default_branch=metadata.get("default_branch", "main"),
            primary_language=metadata.get("language"),
        )

        # Get language breakdown
        analysis.languages = self._get_languages(owner, repo)

        # Get file tree
        analysis.file_structure = self._get_file_tree(owner, repo, analysis.default_branch)

        # Fetch and analyze priority files
        self._fetch_priority_files(owner, repo, analysis)

        # Analyze dependencies from package files
        self._analyze_dependencies(analysis)

        # Analyze infrastructure
        self._analyze_infrastructure(analysis)

        # Analyze code patterns
        self._analyze_code_patterns(owner, repo, analysis)

        # Get README summary
        analysis.readme_summary = self._get_readme_summary(analysis)

        return analysis

    def _get_repo_metadata(self, owner: str, repo: str) -> dict:
        """Fetch repository metadata."""
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = self.client.get(url, headers=self._get_headers())

        self._check_rate_limit(response)

        if response.status_code == 404:
            raise RepoNotFoundError(f"Repository {owner}/{repo} not found")

        if response.status_code == 403:
            raise RepoAccessDeniedError(
                f"Access denied to {owner}/{repo}. "
                "This may be a private repository."
            )

        response.raise_for_status()
        return response.json()

    def _get_languages(self, owner: str, repo: str) -> dict:
        """Get language breakdown for the repository."""
        url = f"{self.base_url}/repos/{owner}/{repo}/languages"
        response = self.client.get(url, headers=self._get_headers())

        self._check_rate_limit(response)

        if response.status_code == 200:
            return response.json()
        return {}

    def _get_file_tree(self, owner: str, repo: str, branch: str) -> dict:
        """Get simplified file tree structure."""
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        response = self.client.get(url, headers=self._get_headers())

        self._check_rate_limit(response)

        if response.status_code != 200:
            return {}

        data = response.json()
        tree = data.get("tree", [])

        # Build simplified tree structure
        structure = {"dirs": [], "files": []}

        for item in tree:
            path = item["path"]
            if item["type"] == "tree":
                # Only include top-level and important directories
                parts = path.split("/")
                if len(parts) <= 2:
                    structure["dirs"].append(path)
            elif item["type"] == "blob":
                # Only include important files at root or in key directories
                parts = path.split("/")
                if len(parts) == 1:
                    structure["files"].append(path)
                elif len(parts) == 2 and parts[0] in SOURCE_DIRS:
                    structure["files"].append(path)

        return structure

    def _get_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """Fetch file content from GitHub API."""
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        response = self.client.get(url, headers=self._get_headers())

        self._check_rate_limit(response)

        if response.status_code == 200:
            data = response.json()
            if data.get("encoding") == "base64" and data.get("content"):
                try:
                    content = base64.b64decode(data["content"]).decode("utf-8")
                    # Limit file size to avoid context issues
                    if len(content) > 100000:
                        return content[:100000] + "\n... (truncated)"
                    return content
                except (UnicodeDecodeError, ValueError):
                    return None
        return None

    def _fetch_priority_files(self, owner: str, repo: str, analysis: RepoAnalysis) -> None:
        """Fetch priority files for analysis."""
        all_files = analysis.file_structure.get("files", [])

        files_fetched = 0
        max_files = 50

        # Fetch by priority
        for priority in sorted(PRIORITY_FILES.keys()):
            for filename in PRIORITY_FILES[priority]:
                if files_fetched >= max_files:
                    return

                # Check if file exists
                matching = [f for f in all_files if f.endswith(filename) or f == filename]
                for match in matching:
                    content = self._get_file_content(owner, repo, match)
                    if content:
                        analysis.key_files[match] = content
                        files_fetched += 1

    def _analyze_dependencies(self, analysis: RepoAnalysis) -> None:
        """Analyze dependencies from package files."""
        # Python
        if "requirements.txt" in analysis.key_files:
            deps = []
            for line in analysis.key_files["requirements.txt"].split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract package name
                    pkg = re.split(r"[=<>!~\[]", line)[0].strip()
                    if pkg:
                        deps.append(pkg)
            analysis.dependencies["python"] = deps

        if "pyproject.toml" in analysis.key_files:
            content = analysis.key_files["pyproject.toml"]
            # Simple extraction of dependencies
            deps = []
            in_deps = False
            for line in content.split("\n"):
                if "[project.dependencies]" in line or "[tool.poetry.dependencies]" in line:
                    in_deps = True
                    continue
                if in_deps:
                    if line.startswith("["):
                        break
                    match = re.match(r'^[\s"]*([a-zA-Z0-9_-]+)', line)
                    if match:
                        deps.append(match.group(1))
            if deps:
                analysis.dependencies["python"] = list(set(
                    analysis.dependencies.get("python", []) + deps
                ))

        # JavaScript/Node
        if "package.json" in analysis.key_files:
            try:
                pkg = json.loads(analysis.key_files["package.json"])
                deps = list(pkg.get("dependencies", {}).keys())
                dev_deps = list(pkg.get("devDependencies", {}).keys())
                analysis.dependencies["npm"] = deps
                analysis.dependencies["npm_dev"] = dev_deps
            except json.JSONDecodeError:
                pass

        # Go
        if "go.mod" in analysis.key_files:
            deps = []
            for line in analysis.key_files["go.mod"].split("\n"):
                if line.strip().startswith("require"):
                    continue
                match = re.match(r"\s*([^\s]+)\s+v", line)
                if match:
                    deps.append(match.group(1))
            analysis.dependencies["go"] = deps

        # Rust
        if "Cargo.toml" in analysis.key_files:
            deps = []
            in_deps = False
            for line in analysis.key_files["Cargo.toml"].split("\n"):
                if "[dependencies]" in line:
                    in_deps = True
                    continue
                if in_deps:
                    if line.startswith("["):
                        break
                    match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                    if match:
                        deps.append(match.group(1))
            analysis.dependencies["rust"] = deps

    def _analyze_infrastructure(self, analysis: RepoAnalysis) -> None:
        """Analyze infrastructure files."""
        # Docker
        for filename in analysis.key_files:
            if "docker-compose" in filename.lower():
                analysis.has_docker = True
                content = analysis.key_files[filename]
                # Extract service names
                services = []
                for line in content.split("\n"):
                    match = re.match(r"^\s{2}([a-zA-Z0-9_-]+):\s*$", line)
                    if match:
                        services.append(match.group(1))
                analysis.docker_services = services
            elif filename.lower() == "dockerfile":
                analysis.has_docker = True

        # Kubernetes
        k8s_files = [f for f in analysis.file_structure.get("files", [])
                     if "kubernetes" in f.lower() or f.endswith(".yaml") or f.endswith(".yml")]
        for filename in k8s_files:
            if filename in analysis.key_files:
                content = analysis.key_files[filename]
                if "kind:" in content and "apiVersion:" in content:
                    analysis.has_kubernetes = True
                    # Extract resource kinds
                    kinds = re.findall(r"kind:\s*(\w+)", content)
                    analysis.kubernetes_resources.extend(kinds)

        # Terraform
        tf_files = [f for f in analysis.file_structure.get("files", []) if f.endswith(".tf")]
        if tf_files:
            analysis.has_terraform = True

        # CI/CD
        ci_files = {
            ".github/workflows": "GitHub Actions",
            ".gitlab-ci.yml": "GitLab CI",
            ".circleci": "CircleCI",
            "Jenkinsfile": "Jenkins",
            ".travis.yml": "Travis CI",
            "azure-pipelines.yml": "Azure Pipelines",
        }

        all_paths = (
            analysis.file_structure.get("files", []) +
            analysis.file_structure.get("dirs", [])
        )

        for path_prefix, platform in ci_files.items():
            if any(p.startswith(path_prefix) or p == path_prefix for p in all_paths):
                analysis.has_ci_cd = True
                analysis.ci_cd_platform = platform
                break

    def _analyze_code_patterns(self, owner: str, repo: str, analysis: RepoAnalysis) -> None:
        """Analyze code for routes, databases, and services."""
        # Determine primary language patterns to use
        lang = (analysis.primary_language or "").lower()

        lang_map = {
            "python": "python",
            "javascript": "javascript",
            "typescript": "javascript",
            "go": "go",
            "rust": "rust",
            "java": "java",
            "kotlin": "java",
        }

        pattern_key = lang_map.get(lang, "python")
        patterns = LANGUAGE_PATTERNS.get(pattern_key, LANGUAGE_PATTERNS["python"])

        # Analyze all key files
        all_content = "\n".join(analysis.key_files.values())

        # Find API routes
        routes = []
        for route_pattern in patterns.get("routes", []):
            matches = re.findall(route_pattern, all_content, re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    routes.append({"method": match[0].upper(), "path": match[1]})
                else:
                    routes.append({"path": match})
        analysis.api_routes = routes[:20]  # Limit to 20 routes

        # Find database connections
        databases = set()
        for pattern, db_name in patterns.get("db_patterns", []):
            if re.search(pattern, all_content, re.IGNORECASE):
                databases.add(db_name)
        analysis.database_connections = list(databases)

        # Find external services
        services = set()
        for pattern, service_name in patterns.get("services", []):
            if re.search(pattern, all_content, re.IGNORECASE):
                services.add(service_name)
        analysis.external_services = list(services)

        # Identify entry points
        entry_points = []
        for filename in analysis.key_files:
            basename = filename.split("/")[-1]
            if basename in PRIORITY_FILES.get(4, []):
                entry_points.append(filename)
        analysis.entry_points = entry_points

    def _get_readme_summary(self, analysis: RepoAnalysis) -> Optional[str]:
        """Extract relevant summary from README."""
        readme_content = None

        for key in analysis.key_files:
            if "readme" in key.lower():
                readme_content = analysis.key_files[key]
                break

        if not readme_content:
            return None

        # Truncate to first ~2000 chars for context efficiency
        if len(readme_content) > 2000:
            # Try to cut at a paragraph break
            truncated = readme_content[:2000]
            last_para = truncated.rfind("\n\n")
            if last_para > 1000:
                truncated = truncated[:last_para]
            return truncated + "\n\n... (truncated)"

        return readme_content

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
