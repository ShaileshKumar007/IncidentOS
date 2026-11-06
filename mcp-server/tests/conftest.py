import sys
from pathlib import Path

# Ensure both backend/ and mcp-server/ are in sys.path
TESTS_DIR = Path(__file__).resolve().parent
MCP_SERVER_ROOT = TESTS_DIR.parent
PROJECT_ROOT = MCP_SERVER_ROOT.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

if str(MCP_SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_SERVER_ROOT))
