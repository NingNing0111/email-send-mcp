"""
在读取 os.environ 之前加载项目根目录的 .env。

MCP/uv 启动时工作目录可能不是项目根，仅 load_dotenv() 会从 cwd 找 .env 而失败。
此处从当前文件向上查找包含 .env 或 pyproject.toml 的目录并加载。
"""
from __future__ import annotations

from pathlib import Path


def load_dotenv_from_project() -> bool:
    """
    加载第一个找到的 .env。返回是否加载了某个文件（若无文件仍可能 load_dotenv() 读环境）。
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return False

    here = Path(__file__).resolve()
    # email_service/load_env.py -> src -> 项目根；Docker  COPY src/ . 时 .env 常在 /app
    candidates = [
        here.parent,           # email_service/
        here.parent.parent,    # src/ 或 项目根（若未用 src 包名）
        here.parent.parent.parent,  # 项目根（src 的上一级）
    ]
    for d in candidates:
        env_path = d / ".env"
        if env_path.is_file():
            load_dotenv(env_path, override=False)
            return True

    # 再向上多找几级（例如从包安装路径运行时）
    d = here.parent.parent
    for _ in range(5):
        d = d.parent
        env_path = d / ".env"
        if env_path.is_file():
            load_dotenv(env_path, override=False)
            return True
        if (d / "pyproject.toml").is_file():
            load_dotenv(d / ".env", override=False)
            return (d / ".env").is_file()

    # 最后尝试当前工作目录
    load_dotenv(override=False)
    return False
