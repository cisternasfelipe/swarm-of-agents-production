import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

CHROMA_DB_PATH = BASE_DIR / "data" / "chroma_db"
LOGS_DIR = BASE_DIR / "logs"
PROMPTS_DIR = BASE_DIR / "agents" / "prompts"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

MAX_LOOP_ITERATIONS = 3
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
MCP_TIMEOUT_MS = 300000

AGENT_ROLES = {
    "architect": {"can_edit": False, "can_bash": False},
    "backend_dev": {"can_edit": True, "can_bash": True},
    "frontend_dev": {"can_edit": True, "can_bash": True},
    "qa_tester": {"can_edit": True, "can_bash": True},
    "devops": {"can_edit": True, "can_bash": True},
    "code_reviewer": {"can_edit": False, "can_bash": False},
}

FILESYSTEM_MCP_COMMAND = "npx"
FILESYSTEM_MCP_ARGS = ["-y", "@modelcontextprotocol/server-filesystem"]
FILESYSTEM_READ_ONLY_TOOLS = [
    "read_file",
    "read_text_file",
    "read_multiple_files",
    "list_directory",
    "list_directory_with_sizes",
    "directory_tree",
    "search_files",
    "get_file_info",
    "list_allowed_directories",
]

GUARDRAILS_ENABLED = True
GUARDRAILS_STRICT_MODE = False

ROLE_BOUNDARIES = {
    "frontend_dev": {
        "hard_blocked": [
            "**/api/",
            "**/models/",
            "**/services/",
            "**/db/",
            "**/database/",
            "**/*.sql",
            "**/Dockerfile",
            "**/docker-compose*",
            "**/.github/",
            "**/.gitlab-ci*",
            "**/k8s/",
        ],
        "soft_blocked": [
            "**/config.py",
            "**/package.json",
            "**/requirements.txt",
            "**/.env*",
        ],
    },
    "backend_dev": {
        "hard_blocked": [
            "**/components/",
            "**/pages/",
            "**/styles/",
            "**/*.css",
            "**/public/",
            "**/assets/",
        ],
        "soft_blocked": [
            "**/*.html",
            "**/templates/",
            "**/views/",
            "**/config.py",
            "**/package.json",
            "**/requirements.txt",
        ],
    },
    "qa_tester": {
        "hard_blocked": [
            "**/src/",
            "**/lib/",
            "**/app/",
        ],
        "soft_blocked": [
            "**/config.py",
            "**/package.json",
            "**/requirements.txt",
        ],
    },
    "devops": {
        "hard_blocked": [
            "**/src/",
            "**/lib/",
            "**/app/",
            "**/components/",
            "**/api/",
            "**/models/",
        ],
        "soft_blocked": [
            "**/config.py",
            "**/package.json",
            "**/requirements.txt",
        ],
    },
}

SKILLS_DIR = BASE_DIR / "skills"
SKILLS_BY_ROLE = {
    "architect": ["spec-generator", "task-planner", "tech-designer", "modelo-canvas"],
    "frontend_dev": ["frontend-react"],
    "backend_dev": ["backend-node"],
}
SKILLS_GLOBAL = ["Guia tecnica Latex"]
