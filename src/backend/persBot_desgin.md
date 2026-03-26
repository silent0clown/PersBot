# PetAgent 电子宠物智能体 — 方案设计文档

> 版本: v1.3
> 日期: 2026-03-26
> 更新: 删除重复内容(3.5)、补全向量存储(5.3.2)、权限超时机制(4.6)、MCP进程管理(6.10)、错误处理与审计日志(10.3-10.5)
> 状态: 设计阶段

---

## 目录

1. [项目概述](#1-项目概述)
2. [整体架构](#2-整体架构)
3. [模块一：模型抽象层 (LLM Provider)](#3-模块一模型抽象层-llm-provider)
4. [模块二：权限控制 (Security)](#4-模块二权限控制-security)
5. [模块三：记忆系统 (Memory)](#5-模块三记忆系统-memory)
6. [模块四：工具与插件系统 (Tools & Plugins)](#6-模块四工具与插件系统-tools--plugins)
7. [模块五：多端接入层 (Channels)](#7-模块五多端接入层-channels)
8. [模块六：语音处理 (Voice)](#8-模块六语音处理-voice)
9. [模块七：宠物人格系统 (Persona)](#9-模块七宠物人格系统-persona)
10. [Agent 主控引擎](#10-agent-主控引擎)
11. [配置管理](#11-配置管理)
12. [项目目录结构](#12-项目目录结构)
13. [开发路线图](#13-开发路线图)
14. [附录](#附录)

---

## 1. 项目概述

### 1.1 项目目标

开发一个跨平台（Linux/Windows）的电子宠物智能体（PetAgent），具备以下核心能力：

- **Agent 能力**：读写文件、执行命令、播放音乐、对话式交互
- **多模型支持**：统一接入 Claude API / OpenAI / Ollama，根据任务复杂度自动路由
- **权限控制**：所有工具操作需经用户授权，支持分级权限管理
- **持久记忆**：跨会话的长短期记忆系统，支持记忆衰减与检索
- **多端接入**：飞书、微信、桌面宠物、CLI 终端统一接口
- **拟人化人格**：具有姓名和性格，通过交互逐步演化

### 1.2 设计原则

| 原则 | 说明 |
|------|------|
| 配置外置 | 所有密钥、模型参数通过 `.env` 管理，零硬编码 |
| 插件优于硬编码 | 基础能力预置，扩展能力通过 MCP 插件按需安装 |
| 接口统一 | 各端适配器对外形态不同，对内调用同一套 Agent Core |
| 安全第一 | 任何文件/命令操作经过权限模块审查，危险操作必须用户确认 |
| 渐进式复杂度 | 先跑通核心链路，再叠加人格、情感、主动交互等高级功能 |

### 1.3 技术选型

| 组件 | 技术方案 | 理由 |
|------|---------|------|
| 开发语言 | Python 3.10+ | 生态丰富，AI 库支持最好 |
| 数据存储 | SQLite | 单文件、跨平台、零配置 |
| 向量检索 | numpy 余弦相似度 / sqlite-vec | 轻量，不依赖外部服务 |
| 语音识别 | Whisper (本地) | 离线可用，隐私安全 |
| 语音合成 | edge-tts | 免费，中文效果好 |
| 插件协议 | MCP (Model Context Protocol) | Anthropic 主导的开放标准，社区生态丰富 |
| 配置管理 | python-dotenv | 标准 .env 加载方案 |

---

## 2. 整体架构

```
+-------------------------------------------------------------+
|                       接入层 (Channels)                       |
|  +--------+  +--------+  +--------+  +--------+             |
|  |  飞书   |  |  微信   |  | 桌面端  |  |  CLI   |             |
|  +---+----+  +---+----+  +---+----+  +---+----+             |
|      |           |           |           |                   |
|      +-----+-----+-----+----+           |                   |
|            |                             |                   |
|  +---------v-----------------------------v---------+         |
|  |          输入预处理 (语音识别 / 文字直通)           |         |
|  +------------------------+------------------------+         |
|                           |                                  |
+---------------------------+----------------------------------+
|                           |          核心层 (Core)             |
|                 +---------v----------+                        |
|                 |   Agent 主控引擎    |                        |
|                 |  (理解/规划/执行)    |                        |
|                 +--+------+------+--+                        |
|                    |      |      |                            |
|           +--------v+  +--v---+ +v----------+                |
|           |权限控制  |  |记忆   | |工具注册中心 |                |
|           |模块     |  |系统   | |           |                |
|           +---------+  +------+ +--+-----+--+                |
|                                    |     |                   |
|                          +---------+     +--------+          |
|                          |                        |          |
|                   +------v------+          +------v------+   |
|                   | 预置工具     |          | MCP 插件     |   |
|                   | (file/shell |          | (weather/    |   |
|                   |  /music)    |          |  search/..)  |   |
|                   +-------------+          +-------------+   |
|                                                              |
+--------------------------------------------------------------+
|                      模型层 (LLM Provider)                    |
|  +------------+  +------------+  +------------+              |
|  | Claude API |  | OpenAI API |  |   Ollama   |              |
|  +------------+  +------------+  +------------+              |
+--------------------------------------------------------------+
```

各层职责清晰分离：

- **接入层**：负责各平台的消息收发和格式转换，向核心层提交统一格式的请求
- **核心层**：Agent 主控引擎协调记忆、权限、工具三大模块，完成理解-规划-执行循环
- **模型层**：封装多个 LLM 提供者，对核心层暴露统一调用接口

---

## 3. 模块一：模型抽象层 (LLM Provider)

### 3.1 设计目标

- 统一封装 Claude API、OpenAI API、Ollama，对上层提供一致的调用接口
- 支持根据任务复杂度自动选择最合适的模型
- 具备容错降级能力，某个模型不可用时自动切换

### 3.2 统一接口定义

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

@dataclass
class ModelInfo:
    """模型能力描述"""
    name: str                    # 模型标识
    provider: str                # "claude" | "openai" | "ollama"
    max_context_tokens: int      # 最大上下文长度
    supports_tools: bool         # 是否支持工具调用
    supports_vision: bool        # 是否支持图像输入
    cost_per_1k_input: float     # 每千token输入成本(美元), 本地模型为0
    cost_per_1k_output: float    # 每千token输出成本(美元)

@dataclass
class LLMResponse:
    """统一响应格式"""
    content: str                 # 文字回复
    tool_calls: list             # 工具调用请求列表
    usage: dict                  # token用量 {"input": x, "output": y}
    model: str                   # 实际使用的模型名
    finish_reason: str           # "stop" | "tool_use" | "length"

class LLMProvider(ABC):
    """LLM提供者抽象基类"""

    @abstractmethod
    def chat(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> LLMResponse:
        """统一对话接口"""

    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """返回模型能力信息"""

    @abstractmethod
    def health_check(self) -> bool:
        """检查服务是否可用"""
```

### 3.3 三个实现

```python
class ClaudeProvider(LLMProvider):
    """Anthropic Claude API (支持官方及第三方中转)"""
    def __init__(self, api_key: str, base_url: str, model: str):
        # base_url 支持:
        #   官方:   https://api.anthropic.com
        #   中转:   https://api.xxx-proxy.com (兼容Anthropic协议的第三方平台)
        self.client = anthropic.Anthropic(api_key=api_key, base_url=base_url)
        self.model = model
    # 工具调用使用 Claude 原生 tool_use 格式
    # 适用: 复杂推理、多步工具调用

class OpenAIProvider(LLMProvider):
    """OpenAI API (支持官方/Azure/第三方中转/本地兼容服务)"""
    def __init__(self, api_key: str, base_url: str, model: str):
        # base_url 支持:
        #   官方:        https://api.openai.com/v1
        #   Azure:       https://xxx.openai.azure.com
        #   第三方中转:   https://api.xxx-proxy.com/v1
        #   本地兼容:    http://localhost:8080/v1 (vLLM/LocalAI/LiteLLM等)
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
    # 工具调用使用 OpenAI function calling 格式
    # 适用: 中等复杂度任务
    # 注意: 第三方中转和本地兼容服务需确认支持 function calling

class OllamaProvider(LLMProvider):
    """Ollama 本地模型"""
    def __init__(self, base_url: str, model: str):
        # base_url: http://localhost:11434 (默认)
        # 也可指向远程 Ollama 实例: http://192.168.1.100:11434
        self.base_url = base_url
        self.model = model
    # 部分模型支持工具调用 (qwen2.5, llama3.1等)
    # 适用: 简单闲聊、离线场景、隐私敏感场景
```

> **第三方平台兼容说明**：许多第三方平台（如各类 API 中转站、企业私有化部署）提供与 OpenAI 或 Anthropic 协议兼容的接口，只需修改 `BASE_URL` 即可接入，无需改动代码。对于不兼容标准协议的平台，可新增一个 `CustomProvider` 实现 `LLMProvider` 接口。

### 3.4 模型路由器

```python
class ModelRouter:
    """根据任务复杂度选择模型"""

    def __init__(self, providers: dict[str, LLMProvider], config: RouterConfig):
        self.providers = providers  # {"claude": ..., "openai": ..., "ollama": ...}
        self.config = config

    def route(self, messages: list, tools: list = None) -> LLMProvider:
        """
        选择最合适的模型。

        路由策略:
        1. 用户手动指定 (消息中包含 "@claude" "@local" 等)
        2. 自动评估任务复杂度
        3. 可用性检查 + 降级
        """
        # 第一优先: 用户指定
        explicit = self._check_user_override(messages)
        if explicit:
            return explicit

        # 第二优先: 复杂度评估
        level = self._assess_complexity(messages, tools)
        target = self.config.get_provider_for_level(level)

        # 第三优先: 可用性降级
        return self._with_fallback(target)
```

#### 3.4.1 复杂度评估规则

复杂度评估使用**规则优先 + 启发式兜底**的策略，避免用一个 LLM 来决定用哪个 LLM：

| 级别 | 判定规则 | 默认模型 |
|------|---------|---------|
| 简单 | 消息长度 < 20字，且不含疑问词/指令动词；或纯表情/问候 | Ollama |
| 中等 | 知识问答、文本总结、不涉及工具调用 | OpenAI |
| 复杂 | 涉及工具调用(tools参数非空)、多轮推理、长上下文(>2000 tokens) | Claude |

```python
def _assess_complexity(self, messages, tools) -> str:
    last_msg = messages[-1]["content"]

    # 规则1: 有工具 → 复杂
    if tools:
        return "complex"

    # 规则2: 短消息 + 无实质内容 → 简单
    if len(last_msg) < 20 and not self._has_question_or_command(last_msg):
        return "simple"

    # 规则3: 上下文长 → 复杂
    total_tokens = self._estimate_tokens(messages)
    if total_tokens > 2000:
        return "complex"

    # 默认: 中等
    return "medium"
```

#### 3.4.2 容错降级链

```
目标模型不可用(网络超时/额度用尽/服务宕机)
  │
  ▼
Claude → 降级 OpenAI → 降级 Ollama → 返回预设回复
```

降级时 Agent 应告知用户：

```
"主人，我现在用的是本地小脑袋，复杂的事情可能做不太好哦~"
```

#### 3.4.3 模型健康管理（熔断机制）

当某个模型在一段时间内持续不可用时，不应每次请求都尝试调用再超时，而应主动跳过，待恢复后再启用。采用**熔断器（Circuit Breaker）** 模式：

**三态转换：**

```
                    连续失败达到阈值
    ┌────────┐    ──────────────>    ┌────────┐
    │  关闭   │                      │  打开   │
    │(正常调用)│    <───────────     │(直接跳过)│
    └────────┘     探测成功          └───┬────┘
        ^                               │
        │          冷却时间到期           │
        │       ┌──────────┐            │
        │       │  半开     │<───────────┘
        └───────│(放行单次   │
         探测成功│ 探测请求)  │
                └──────────┘
                   探测失败 → 回到"打开"
```

**状态说明：**

| 状态 | 行为 | 转换条件 |
|------|------|---------|
| 关闭 (Closed) | 正常调用模型 | 连续失败 >= `failure_threshold` 次 → 打开 |
| 打开 (Open) | 跳过该模型，直接走降级链 | 冷却时间 `cooldown_seconds` 到期 → 半开 |
| 半开 (Half-Open) | 放行一次探测请求 | 探测成功 → 关闭；探测失败 → 打开 |

**配置参数：**

```bash
# .env
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3    # 连续失败N次后熔断
CIRCUIT_BREAKER_COOLDOWN_SECONDS=300   # 熔断后冷却时间(秒), 默认5分钟
```

**实现：**

```python
from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """单个模型的熔断器"""

    def __init__(self, provider_name: str,
                 failure_threshold: int = 3,
                 cooldown_seconds: int = 300):
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.opened_at: datetime | None = None

    def allow_request(self) -> bool:
        """判断是否允许向该模型发送请求"""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # 检查冷却时间是否到期
            if datetime.now() - self.opened_at > timedelta(seconds=self.cooldown_seconds):
                self.state = CircuitState.HALF_OPEN
                return True  # 放行一次探测
            return False  # 仍在冷却中, 直接跳过

        if self.state == CircuitState.HALF_OPEN:
            return True  # 半开状态允许探测

        return False

    def record_success(self):
        """记录一次成功调用"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED  # 探测成功, 恢复正常
        self.state = CircuitState.CLOSED

    def record_failure(self):
        """记录一次失败调用"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.state == CircuitState.HALF_OPEN:
            # 探测失败, 重新打开熔断
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()
            return

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = datetime.now()

    def get_status(self) -> dict:
        """返回当前状态 (用于日志和监控)"""
        return {
            "provider": self.provider_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": str(self.last_failure_time) if self.last_failure_time else None,
            "opened_at": str(self.opened_at) if self.opened_at else None,
        }
```

**与 ModelRouter 的集成：**

```python
class ModelRouter:
    def __init__(self, providers, config):
        self.providers = providers
        self.config = config
        # 每个 provider 一个熔断器
        self.breakers = {
            name: CircuitBreaker(
                name,
                failure_threshold=config.circuit_breaker_failure_threshold,
                cooldown_seconds=config.circuit_breaker_cooldown_seconds
            )
            for name in providers
        }

    def route(self, messages, tools=None) -> LLMProvider:
        level = self._assess_complexity(messages, tools)
        target_name = self.config.get_provider_for_level(level)

        # 按降级链依次尝试
        fallback_chain = self._build_fallback_chain(target_name)

        for name in fallback_chain:
            breaker = self.breakers[name]
            if breaker.allow_request():
                return self.providers[name]

        # 全部熔断, 返回None由Agent处理
        return None

    def report_result(self, provider_name: str, success: bool):
        """由Agent在每次调用后回报结果"""
        breaker = self.breakers[provider_name]
        if success:
            breaker.record_success()
        else:
            breaker.record_failure()

    def get_health_status(self) -> list[dict]:
        """返回所有模型的健康状态 (可通过 /status 命令查看)"""
        return [b.get_status() for b in self.breakers.values()]
```

**用户可感知的行为：**

```
# 正常状态
用户: 帮我分析这段代码
Agent: (调用 Claude 成功) 这段代码的逻辑是...

# Claude 连续超时 3 次, 触发熔断
Agent: 主人, Claude 暂时联系不上, 我先用备用的脑袋帮你~
       (自动切换 OpenAI)

# 5分钟后, 熔断器进入半开状态, 自动探测
Agent: (后台探测 Claude API... 成功!)
       主人, Claude 恢复了, 我又满血啦~

# 用户也可以手动查看状态
用户: /status
Agent: 模型健康状态:
       - Claude:  正常 (连续成功 12 次)
       - OpenAI:  正常 (连续成功 5 次)
       - Ollama:  熔断中 (连续失败 3 次, 3分钟后重试)
```

### 3.5 Token 预算控制

每次对话消耗的 token 需要控制，防止单次对话成本失控。预算根据任务复杂度自动调整：

| 任务类型 | 判定规则 | 默认预算 | 可配置 |
|---------|---------|---------|--------|
| 简单 | 无工具调用，消息 < 50 字 | 500 tokens | `TOKEN_BUDGET_SIMPLE` |
| 中等 | 无工具调用，消息 ≥ 50 字 | 2000 tokens | `TOKEN_BUDGET_MEDIUM` |
| 复杂 | 有工具调用 | 4000 tokens | `TOKEN_BUDGET_COMPLEX` |
| 工具密集 | 连续工具调用 > 3 次 | 6000 tokens | `TOKEN_BUDGET_TOOL_INTENSIVE` |

**配置参数：**

```bash
# .env
TOKEN_BUDGET_SIMPLE=500                # 简单任务 token 预算
TOKEN_BUDGET_MEDIUM=2000              # 中等任务 token 预算
TOKEN_BUDGET_COMPLEX=4000             # 复杂任务 token 预算
TOKEN_BUDGET_TOOL_INTENSIVE=6000       # 工具密集任务 token 预算
```

**实现：**

```python
class TokenBudgetManager:
    """Token 预算管理器"""

    def __init__(self, config: TokenBudgetConfig):
        self.config = config
        self.current_budget: int = config.default
        self.total_used: int = 0

    def assess_task_type(self, messages: list, tools: list = None) -> str:
        """评估任务类型"""
        last_msg = messages[-1].get("content", "") if messages else ""

        # 工具密集：连续调用超过3次工具
        if tools and len(tools) > 3:
            return "tool_intensive"

        # 复杂：有工具调用
        if tools:
            return "complex"

        # 中等：消息长度 >= 50 字
        if len(last_msg) >= 50:
            return "medium"

        # 简单：其他
        return "simple"

    def get_budget_for_task(self, task_type: str) -> int:
        """获取任务对应的预算"""
        budget_map = {
            "simple": self.config.simple,
            "medium": self.config.medium,
            "complex": self.config.complex,
            "tool_intensive": self.config.tool_intensive,
        }
        return budget_map.get(task_type, self.config.default)

    def check_within_budget(self, estimated_tokens: int) -> bool:
        """检查是否在预算内"""
        return (self.total_used + estimated_tokens) <= self.current_budget

    def consume(self, tokens: int):
        """消耗 token"""
        self.total_used += tokens

    def reset(self):
        """重置预算（新会话）"""
        self.total_used = 0
```

---

## 4. 模块二：权限控制 (Security)

### 4.1 设计目标

- Agent 执行任何工具操作前，必须经过权限模块审查
- 按危险程度分级，低风险操作自动放行，高风险操作需用户确认
- 支持用户"记住"授权决策，避免重复询问
- 硬性拦截不可授权的危险操作

### 4.2 三级权限模型

```
+--------+------------------------------------------+------------------+
| 级别    | 范围                                      | 交互方式          |
+--------+------------------------------------------+------------------+
| 绿色   | 读取白名单目录文件                           | 静默放行          |
| (安全)  | 查看系统信息(时间/磁盘/OS版本)               |                  |
|        | 播放音乐                                   |                  |
|        | 只读命令(ls, cat, date, df, uname, whoami) |                  |
+--------+------------------------------------------+------------------+
| 黄色   | 创建/编辑文件                                | 单次确认          |
| (敏感)  | 执行非白名单的只读命令                        | 支持"记住"        |
|        | 读取白名单外的文件                           |                  |
|        | 发起网络请求                                 |                  |
+--------+------------------------------------------+------------------+
| 红色   | 删除文件/目录                                | 每次确认+二次确认  |
| (危险)  | 执行写入性/破坏性命令(rm, mv, kill, chmod)    | 不支持"记住"      |
|        | 访问敏感路径(.ssh, .env, credentials等)      |                  |
|        | 安装/卸载软件包                               |                  |
+--------+------------------------------------------+------------------+
| 黑色   | rm -rf / , mkfs, dd if=/dev/zero            | 永久拦截          |
| (禁止)  | 访问其他用户目录                              | 无法授权          |
|        | 修改系统关键配置(/etc/passwd等)               |                  |
+--------+------------------------------------------+------------------+
```

### 4.3 权限配置文件

```yaml
# config/permissions.yaml

# 安全路径白名单
safe_paths:
  read:
    - "~/Documents"
    - "~/Music"
    - "~/Desktop"
    - "/tmp"
  write:
    - "~/Documents/pet_workspace"
    - "/tmp"

# 永久封禁路径
blocked_paths:
  - "~/.ssh"
  - "~/.gnupg"
  - "~/.env"
  - "~/.aws"
  - "~/.config/gcloud"
  - "**/credentials*"
  - "**/*.pem"
  - "**/*.key"

# 命令白名单 (绿色权限)
command_whitelist:
  - "ls"
  - "cat"
  - "head"
  - "tail"
  - "date"
  - "df"
  - "du"
  - "uname"
  - "whoami"
  - "pwd"
  - "echo"
  - "wc"

# 命令黑名单 (永久拦截)
command_blacklist_patterns:
  - "rm -rf /"
  - "rm -rf /*"
  - "mkfs"
  - "dd if=/dev/"
  - "> /dev/sd"
  - "chmod -R 777 /"
  - "curl * | bash"
  - "wget * | sh"

# 用户动态授权规则 (运行时由"记住"操作追加)
auto_approved_rules: []
```

### 4.4 权限检查流程

```
Agent 请求执行工具操作
         |
         v
+--------------------+
| 1. 黑名单检查       |---匹配---> 拦截, 告知用户"这个操作我不能做"
+--------+-----------+
         | 不匹配
         v
+--------------------+
| 2. 权限级别判定      |
| (路径+命令+操作类型)  |
+--------+-----------+
         |
    +----+----+----+
    |         |    |
  绿色      黄色  红色
    |         |    |
    v         v    v
  直接执行  询问用户  询问+二次确认
              |    |
         +----+    +----+
         |              |
      [允许]          [允许]
      [拒绝]          [拒绝]
      [允许并记住]
         |
         v
     写入auto_approved_rules
```

### 4.5 确认交互示例

**黄色权限 — 单次确认：**

```
Agent: 主人，我需要编辑文件 ~/notes/todo.txt，添加你说的内容，可以吗？
       [允许]  [拒绝]  [允许并记住(~/notes/下的编辑不再询问)]
```

**红色权限 — 二次确认：**

```
Agent: 主人，我需要删除 ~/Downloads/old_files/ 目录，确定吗？
       [确认删除]  [取消]

用户: 确认删除

Agent: 再次确认：将永久删除 ~/Downloads/old_files/ 及其中 23 个文件，无法恢复。继续？
       [是，删除]  [取消]
```

### 4.6 核心类设计

```python
from enum import Enum
from dataclasses import dataclass

class PermissionLevel(Enum):
    GREEN = "green"    # 安全, 静默放行
    YELLOW = "yellow"  # 敏感, 需确认
    RED = "red"        # 危险, 需双重确认
    BLACK = "black"    # 禁止, 永久拦截

@dataclass
class PermissionRequest:
    tool_name: str         # 工具名称
    action: str            # 具体操作描述
    target: str            # 操作目标(路径/命令)
    level: PermissionLevel # 权限级别
    detail: str            # 展示给用户的详细说明
    created_at: datetime = None  # 请求创建时间
    timeout_seconds: int = 120   # 超时时间(秒), 默认2分钟

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def is_expired(self) -> bool:
        """检查请求是否已超时"""
        return (datetime.now() - self.created_at).total_seconds() > self.timeout_seconds

class PermissionManager:
    def __init__(self, config_path: str):
        self.config = self._load_config(config_path)
        self.auto_rules = []  # 用户"记住"的规则

    def check(self, tool_name: str, action: str, target: str) -> PermissionRequest:
        """评估操作的权限级别, 返回权限请求对象"""

    def is_auto_approved(self, request: PermissionRequest) -> bool:
        """检查是否匹配用户已授权的"记住"规则"""

    def add_auto_rule(self, pattern: str, level: PermissionLevel):
        """添加自动授权规则 (仅黄色权限可"记住")"""

    def request_approval(self, request: PermissionRequest) -> bool:
        """向用户发起授权请求, 等待回应"""
        # 通过当前 channel 的交互接口向用户展示确认对话框

    def handle_timeout(self, request: PermissionRequest) -> str:
        """处理权限请求超时，返回超时提示消息"""
        return "主人，确认超时了，我还等你哦~"
```

---

## 5. 模块三：记忆系统 (Memory)

### 5.1 设计目标

- 短期记忆：管理当前对话上下文，处理 token 超限时的压缩
- 长期记忆：跨会话持久存储用户偏好、重要事件、关键事实
- 记忆衰减：根据时间和访问频率自动降低旧记忆权重
- 记忆检索：每次对话时自动检索相关长期记忆注入上下文
- 隐私控制：用户可要求删除特定记忆

### 5.2 记忆分类

```
+-----------+--------------------------+------------------+-----------+
| 类型       | 内容示例                  | 存储位置          | 生命周期   |
+-----------+--------------------------+------------------+-----------+
| 短期记忆   | 当前对话的消息列表          | 内存              | 单次会话   |
+-----------+--------------------------+------------------+-----------+
| 长期-事实  | "用户对花生过敏"           | SQLite            | 永久      |
| 长期-偏好  | "用户喜欢简洁的回复风格"     | SQLite            | 缓慢衰减  |
| 长期-事件  | "用户4月1日要去北京出差"     | SQLite            | 事件过期后 |
| 长期-情感  | "用户今天心情不好"          | SQLite            | 快速衰减  |
+-----------+--------------------------+------------------+-----------+
| 对话归档   | 历史对话原文               | SQLite            | 永久      |
+-----------+--------------------------+------------------+-----------+
```

### 5.3 存储方案：SQLite

选择 SQLite 作为唯一存储后端：

- **优势**：单文件、跨平台、Python 内置支持、零运维、性能足够（百万级记忆无压力）
- **向量检索**：使用 numpy 计算余弦相似度，记忆量大时可引入 sqlite-vec 扩展
- **向量存储**：embedding 以 bytes 形式存储，使用 numpy 序列化

#### 5.3.1 数据库表设计

```sql
-- 长期记忆表
CREATE TABLE memories (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    type            TEXT NOT NULL,       -- 'fact' | 'preference' | 'event' | 'emotion'
    content         TEXT NOT NULL,       -- 记忆内容 (自然语言描述)
    embedding       BLOB,               -- 向量表示 (numpy array 序列化后的 bytes)
    importance      REAL DEFAULT 0.5,   -- 重要度 0.0-1.0
    access_count    INTEGER DEFAULT 0,  -- 被召回次数
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_accessed   DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at      DATETIME,           -- 过期时间 (事件类记忆)
    decay_score     REAL DEFAULT 1.0,   -- 当前衰减分数
    source          TEXT DEFAULT 'inferred',  -- 'user_told' | 'inferred' | 'observed'
    is_deleted      INTEGER DEFAULT 0   -- 软删除标记
);

-- 对话历史归档表
CREATE TABLE chat_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL,       -- 会话ID
    user_id         TEXT NOT NULL,       -- 用户标识
    role            TEXT NOT NULL,       -- 'user' | 'assistant' | 'system'
    content         TEXT NOT NULL,       -- 消息内容
    channel         TEXT NOT NULL,       -- 来源渠道 'feishu'|'wechat'|'desktop'|'cli'
    timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,
    token_count     INTEGER             -- token数量 (用于统计)
);

-- 索引
CREATE INDEX idx_memories_type ON memories(type);
CREATE INDEX idx_memories_decay ON memories(decay_score DESC);
CREATE INDEX idx_memories_deleted ON memories(is_deleted);
CREATE INDEX idx_chat_session ON chat_history(session_id);
CREATE INDEX idx_chat_user ON chat_history(user_id);
CREATE INDEX idx_chat_time ON chat_history(timestamp);
```

#### 5.3.2 向量存储实现

```python
# embedding 配置
EMBEDDING_MODEL = "text-embedding-3-small"  # OpenAI
# 或使用本地: sentence-transformers/all-MiniLM-L6-v2

EMBEDDING_DIMENSIONS = 1536  # text-embedding-3-small 维度

class LongTermMemory:
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self.embedding_model = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
        self._init_tables()

    def _compute_embedding(self, text: str) -> bytes:
        """计算文本embedding并序列化为bytes存储"""
        import numpy as np

        # 调用 embedding API (使用 OpenAI 或本地模型)
        embedding = self.embedding_client.embeddings.create(
            model=self.embedding_model,
            input=text
        ).data[0].embedding

        # 转为 bytes 存储 (float32, 1536维)
        return np.array(embedding, dtype=np.float32).tobytes()

    def _decode_embedding(self, blob: bytes) -> np.ndarray:
        """从bytes反序列化为numpy数组"""
        import numpy as np
        return np.frombuffer(blob, dtype=np.float32)
```

### 5.4 短期记忆管理

```python
class ShortTermMemory:
    """当前对话上下文管理"""

    def __init__(self, max_tokens: int = 8000):
        self.messages: list[dict] = []
        self.max_tokens = max_tokens

    def add(self, role: str, content: str):
        """添加消息"""
        self.messages.append({"role": role, "content": content})
        if self._estimate_tokens() > self.max_tokens:
            self._compress()

    def _compress(self):
        """
        压缩策略:
        1. 保留 system prompt (messages[0])
        2. 取最早的 N 条非系统消息
        3. 用 LLM 生成摘要替代这些消息
        4. 插入摘要作为 system 消息
        """
        system = self.messages[0]
        to_summarize = self.messages[1:4]   # 取最早3条
        remaining = self.messages[4:]

        summary = self._generate_summary(to_summarize)

        self.messages = [
            system,
            {"role": "system", "content": f"[之前的对话摘要] {summary}"},
            *remaining
        ]

    def get_messages(self) -> list[dict]:
        """返回当前上下文"""
        return self.messages.copy()

    def clear(self):
        """清空 (保留system prompt)"""
        self.messages = self.messages[:1] if self.messages else []
```

### 5.5 长期记忆管理

```python
class LongTermMemory:
    """持久化长期记忆"""

    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
        self._init_tables()

    def store(self, content: str, mem_type: str, importance: float,
              source: str = "inferred", expires_at: str = None):
        """
        存入一条长期记忆。

        Args:
            content:    记忆内容 (自然语言)
            mem_type:   类型 ('fact'|'preference'|'event'|'emotion')
            importance: 重要度 0.0-1.0
            source:     来源 ('user_told'|'inferred'|'observed')
            expires_at: 过期时间 (仅事件类)
        """
        embedding = self._compute_embedding(content)
        self.db.execute(
            "INSERT INTO memories (type, content, embedding, importance, source, expires_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (mem_type, content, embedding, importance, source, expires_at)
        )
        self.db.commit()

    def retrieve(self, query: str, top_k: int = 5) -> list[dict]:
        """
        检索与 query 最相关的 top_k 条记忆。

        检索策略 (多路召回):
        1. 向量相似度: 计算 query embedding 与所有记忆的余弦相似度
        2. 关键词匹配: SQLite FTS5 全文检索
        3. 综合排序: similarity * 0.6 + decay_score * 0.3 + importance * 0.1
        """

    def forget(self, memory_id: int):
        """软删除一条记忆 (用户要求忘记时调用)"""
        self.db.execute(
            "UPDATE memories SET is_deleted = 1 WHERE id = ?", (memory_id,)
        )
        self.db.commit()

    def decay_all(self):
        """
        批量更新所有记忆的衰减分数。
        建议在 Agent 启动时或每日定时执行。
        """
```

### 5.6 记忆衰减算法

```python
def calculate_decay_score(memory: dict, now: datetime) -> float:
    """
    衰减公式: score = importance_factor * recency_factor * frequency_factor

    - importance_factor: 基于来源和重要度
      - user_told (用户主动告知): importance * 1.5, 最低0.5 (极慢衰减)
      - inferred (LLM推断):      importance * 1.0 (正常衰减)
      - observed (行为观察):      importance * 0.8 (较快衰减)

    - recency_factor: 基于最后访问时间
      - 1.0 / (1.0 + 0.05 * days_since_last_access)
      - 1天前: 0.95, 7天前: 0.74, 30天前: 0.40, 90天前: 0.18

    - frequency_factor: 基于召回次数
      - min(1.0, access_count / 5)
      - 被召回5次以上的记忆更加稳固
    """
    days_ago = (now - memory["last_accessed"]).days

    # 来源权重
    source_weight = {"user_told": 1.5, "inferred": 1.0, "observed": 0.8}
    importance_factor = memory["importance"] * source_weight.get(memory["source"], 1.0)

    # 时间衰减
    recency_factor = 1.0 / (1.0 + 0.05 * days_ago)

    # 频率稳固
    frequency_factor = min(1.0, memory["access_count"] / 5)

    # 用户主动告知的记忆, decay_score 最低 0.5 (永不完全遗忘)
    score = importance_factor * recency_factor * max(0.3, frequency_factor)
    if memory["source"] == "user_told":
        score = max(score, 0.5)

    return min(1.0, score)
```

### 5.7 记忆写入判定

不是每句对话都存入长期记忆，由 LLM 判断：

```python
MEMORY_EXTRACTION_PROMPT = """
分析以下对话，判断是否包含值得长期记忆的信息。

如果有，返回JSON格式:
{
  "should_store": true,
  "memories": [
    {
      "content": "记忆内容 (转换为陈述句，包含具体时间)",
      "type": "fact|preference|event|emotion",
      "importance": 0.0-1.0,
      "source": "user_told|inferred",
      "expires_at": "YYYY-MM-DD 或 null"
    }
  ]
}

如果没有值得记忆的内容，返回:
{"should_store": false, "memories": []}

判断标准:
- 用户个人信息 (姓名/生日/过敏等) → fact, importance=0.9-1.0
- 用户偏好/习惯 → preference, importance=0.5-0.7
- 具体时间的事件/安排 → event, importance=0.7-0.9, 设置expires_at
- 情绪表达 → emotion, importance=0.3
- 纯闲聊/问候/无实质内容 → should_store=false
"""
```

### 5.8 记忆检索与注入

每次用户发消息时，自动检索相关记忆并注入 system prompt：

```python
class MemoryRetriever:
    def inject_memories(self, user_message: str, system_prompt: str) -> str:
        """
        检索相关记忆并注入到system prompt中。

        流程:
        1. 用 user_message 检索 top-5 相关记忆
        2. 按 decay_score 过滤 (< 0.1 的不注入)
        3. 格式化后追加到 system prompt
        4. 更新被召回记忆的 last_accessed 和 access_count
        """
        memories = self.long_term.retrieve(user_message, top_k=5)
        memories = [m for m in memories if m["decay_score"] > 0.1]

        if not memories:
            return system_prompt

        memory_text = "\n".join(f"- {m['content']}" for m in memories)
        return system_prompt + f"\n\n[你记得关于主人的以下信息]\n{memory_text}"
```

---

## 6. 模块四：工具与插件系统 (Tools & Plugins)

### 6.1 设计目标

- 预置工具只覆盖"元能力"：文件操作、命令执行、音乐播放、插件管理
- 扩展能力通过 MCP 插件按需安装，不改代码
- Shell 作为万能兜底工具，可执行任意命令（受权限控制）
- 所有工具调用经过权限模块审查

### 6.2 工具抽象接口

```python
from abc import ABC, abstractmethod

class BaseTool(ABC):
    """所有工具的基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述 (给LLM看, 用于判断何时调用)"""

    @property
    @abstractmethod
    def parameters_schema(self) -> dict:
        """参数的JSON Schema定义"""

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """执行工具, 返回结果文本"""

    def to_schema(self) -> dict:
        """转换为LLM工具调用格式"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters_schema
        }
```

### 6.3 预置工具

#### 6.3.1 文件操作 (file_ops.py)

```python
class ReadFileTool(BaseTool):
    name = "read_file"
    description = "读取指定路径的文件内容"
    # execute: 读取文件，返回内容

class WriteFileTool(BaseTool):
    name = "write_file"
    description = "将内容写入指定路径的文件"
    # execute: 写入文件

class ListDirectoryTool(BaseTool):
    name = "list_directory"
    description = "列出指定目录下的文件和文件夹"
    # execute: 列出目录内容
```

#### 6.3.2 命令执行 (shell.py)

```python
class ShellTool(BaseTool):
    name = "run_command"
    description = "在系统终端中执行命令并返回输出"
    # execute: 运行shell命令, 返回stdout+stderr
    # 注意: 每次执行前经过权限模块审查

    # 危险模式黑名单
    DANGEROUS_PATTERNS = [
        r">\s*/dev/sd",
        r"mkfs",
        r"dd\s+.*of=/dev/",
        r":\(\)\{",  # fork bomb
    ]

    def execute(self, command: str, **kwargs) -> str:
        # 执行前检查危险模式
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command):
                raise ToolExecutionError(f"检测到危险命令模式: {pattern}")

        # 建议使用受限shell (rbash) 或命令白名单
        return self._execute_in_restricted_shell(command)
```

#### 6.3.3 音乐播放 (music.py)

```python
class MusicPlayerTool(BaseTool):
    name = "play_music"
    description = "播放指定路径的音乐文件或控制音乐播放(暂停/停止/下一首)"
    # execute:
    #   Linux: 调用 mpv / vlc / paplay
    #   Windows: 调用 wmplayer 或 pygame.mixer
    # 跨平台兼容通过 platform 模块判断
```

#### 6.3.4 插件管理 (plugin_manager.py)

```python
class PluginManagerTool(BaseTool):
    name = "manage_plugins"
    description = "安装、卸载或列出已安装的MCP插件"
    # execute:
    #   action="install": 从插件源安装指定MCP插件
    #   action="uninstall": 卸载指定插件
    #   action="list": 列出已安装插件
```

### 6.4 工具注册中心

```python
class ToolRegistry:
    """统一管理所有工具 (预置 + 插件)"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """注册一个工具"""
        self._tools[tool.name] = tool

    def register_builtin_tools(self):
        """注册所有预置工具"""
        self.register(ReadFileTool())
        self.register(WriteFileTool())
        self.register(ListDirectoryTool())
        self.register(ShellTool())
        self.register(MusicPlayerTool())
        self.register(PluginManagerTool())

    def discover_mcp_plugins(self, plugins_dir: str):
        """
        扫描插件目录, 启动各MCP Server, 注册其提供的工具。

        流程:
        1. 遍历 plugins/ 目录下的子目录
        2. 读取每个插件的 manifest.json (包含启动命令)
        3. 启动 MCP Server 进程
        4. 通过 MCP 协议获取工具列表
        5. 包装为 MCPTool 对象并注册
        """

    def get_all_schemas(self) -> list[dict]:
        """返回所有工具的schema (注入LLM的system prompt)"""
        return [tool.to_schema() for tool in self._tools.values()]

    def get_tool(self, name: str) -> BaseTool | None:
        return self._tools.get(name)
```

### 6.5 MCP 插件结构

每个 MCP 插件是一个独立目录：

```
plugins/
├── weather/
│   ├── manifest.json       # 插件元信息
│   ├── server.py           # MCP Server 实现
│   └── requirements.txt    # 依赖
├── web-search/
│   ├── manifest.json
│   ├── server.py
│   └── requirements.txt
```

manifest.json 示例：

```json
{
  "name": "weather",
  "version": "1.0.0",
  "description": "查询城市天气预报",
  "author": "community",
  "command": "python server.py",
  "tools": [
    {
      "name": "get_weather",
      "description": "查询指定城市的天气预报",
      "parameters": {
        "city": {"type": "string", "description": "城市名称"},
        "days": {"type": "integer", "description": "预报天数", "default": 1}
      }
    }
  ]
}
```

### 6.6 工具调用无法满足时的处理策略

```
用户请求 → Agent 理解意图
              |
              v
    +--------------------+
    | 在已注册工具中匹配    |
    +--------+-----------+
             |
        +----+----+
        |         |
     有匹配     无匹配
        |         |
        v         v
    调用工具  +--------------------+
             | 判断: shell能完成吗? |
             +--------+-----------+
                      |
                 +----+----+
                 |         |
               能完成    不能完成
                 |         |
                 v         v
           生成命令     坦诚告知用户:
           经权限审查   "主人, 我还没有这个能力,
           后执行       要不要帮我装个 XX 插件?"
```

### 6.7 工具循环检测

Agent 有时可能陷入循环调用同一个工具，需要检测并阻止：

**配置参数：**

```bash
# .env
TOOL_LOOP_DETECTION_ENABLED=true           # 是否启用循环检测
TOOL_LOOP_MAX_CALLS=3                      # 60秒内最多调用同一工具次数
TOOL_LOOP_WINDOW_SECONDS=60                 # 时间窗口(秒)
```

**实现：**

```python
import time
from collections import defaultdict

class ToolLoopDetector:
    """检测工具循环调用，防止 Agent 陷入无限调用"""

    def __init__(self, max_calls: int = 3, window_seconds: int = 60):
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self.tool_call_history: dict[str, list[float]] = defaultdict(list)

    def check(self, tool_name: str) -> bool:
        """
        检查是否允许调用该工具。
        返回 True 表示允许，False 表示阻止。
        """
        now = time.time()
        history = self.tool_call_history[tool_name]

        # 清理窗口外的记录
        cutoff = now - self.window_seconds
        history = [t for t in history if t > cutoff]

        if len(history) >= self.max_calls:
            # 触发循环检测，阻止调用
            return False

        # 记录本次调用
        history.append(now)
        self.tool_call_history[tool_name] = history
        return True

    def get_blocked_tools(self) -> list[str]:
        """返回当前被阻止的工具列表"""
        now = time.time()
        cutoff = now - self.window_seconds
        blocked = []

        for tool_name, history in self.tool_call_history.items():
            recent = [t for t in history if t > cutoff]
            if len(recent) >= self.max_calls:
                blocked.append(tool_name)

        return blocked

    def reset(self, tool_name: str = None):
        """重置历史记录"""
        if tool_name:
            self.tool_call_history.pop(tool_name, None)
        else:
            self.tool_call_history.clear()
```

**在 Agent 中的使用：**

```python
class PetAgent:
    def __init__(self, config: AgentConfig):
        # ...
        self.loop_detector = ToolLoopDetector(
            max_calls=config.tool_loop_max_calls,
            window_seconds=config.tool_loop_window_seconds
        )

    def _execute_tool_with_loop_check(self, tool_call: ToolCall) -> str:
        """带循环检测的工具执行"""
        tool_name = tool_call.name

        if not self.loop_detector.check(tool_name):
            return f"[循环检测] 工具 '{tool_name}' 在短时间内被频繁调用，已被阻止。请尝试其他方式。"

        # 正常执行工具
        tool = self.tool_registry.get_tool(tool_name)
        return tool.execute(**tool_call.arguments)
```

### 6.8 工具执行超时控制

对于耗时较长的工具操作（如 npm install、编译、文件批量处理），需要设置超时：

**配置参数：**

```bash
# .env
TOOL_EXECUTION_TIMEOUT_SECONDS=30           # 工具默认执行超时(秒)
TOOL_EXECUTION_TIMEOUT_LONG=300            # 长时间操作超时(秒)，如安装、编译
```

**超时配置示例：**

```python
# 不同工具可以设置不同超时
TOOL_TIMEOUT_MAP=:
  shell: 30                    # 普通 shell 命令 30 秒
  npm_install: 300             # npm 安装 5 分钟
  pip_install: 180             # pip 安装 3 分钟
  docker_build: 600             # Docker 构建 10 分钟
  compile: 120                 # 编译 2 分钟
```

**实现：**

```python
import subprocess
from dataclasses import dataclass

@dataclass
class ToolTimeoutConfig:
    default: int = 30
    long: int = 300
    timeout_map: dict[str, int] = None

    def get_timeout(self, tool_name: str) -> int:
        """获取工具对应的超时时间"""
        if self.timeout_map and tool_name in self.timeout_map:
            return self.timeout_map[tool_name]
        # 默认使用 long 超时（安装、编译等）还是 default
        return self.long if tool_name in ["npm_install", "pip_install", "docker_build", "compile"] else self.default

class ShellTool(BaseTool):
    def __init__(self, timeout_config: ToolTimeoutConfig):
        self.timeout_config = timeout_config

    def execute(self, command: str, tool_name: str = "shell") -> str:
        timeout = self.timeout_config.get_timeout(tool_name)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return result.stdout + result.stderr

        except subprocess.TimeoutExpired:
            return f"[超时] 命令执行超过 {timeout} 秒未完成。\n可能原因：网络慢、依赖较大、任务繁重。\n建议：稍后重试或手动执行该命令。"
```

### 6.9 MCP 插件安装超时控制

MCP 插件安装（特别是 npm install）可能耗时很长，需要特殊处理：

**配置参数：**

```bash
# .env
MCP_INSTALL_TIMEOUT_SECONDS=300            # MCP 安装超时(秒), 默认5分钟
MCP_INSTALL_RETRY_COUNT=2                  # 安装重试次数
```

**实现：**

```python
import asyncio

@dataclass
class MCPInstallConfig:
    timeout_seconds: int = 300      # 5分钟默认超时
    retry_count: int = 2             # 重试次数

    @property
    def retry_count(self) -> int:
        return self._retry_count

    @retry_count.setter
    def retry_count(self, value: int):
        self._retry_count = max(0, min(value, 3))  # 限制 0-3 次

class MCPInstaller:
    def __init__(self, config: MCPInstallConfig):
        self.config = config

    async def install_plugin(self, package: str) -> InstallResult:
        """
        安装 MCP 插件，带超时控制和重试
        """
        last_error = None

        for attempt in range(self.config.retry_count + 1):
            try:
                result = await asyncio.wait_for(
                    self._do_install(package),
                    timeout=self.config.timeout_seconds
                )
                return result

            except asyncio.TimeoutError:
                last_error = f"安装超时（{self.config.timeout_seconds}秒）"
                # 杀掉可能的残留进程
                await self._cleanup_partial_install(package)

            except Exception as e:
                last_error = str(e)

            if attempt < self.config.retry_count:
                # 重试前等待
                await asyncio.sleep(2 ** attempt)  # 指数退避: 2s, 4s

        # 所有尝试都失败
        return InstallResult(
            success=False,
            message=f"安装失败: {last_error}\n\n"
                   f"建议手动安装：\n"
                   f"  cd /path/to/project\n"
                   f"  npm install {package}\n"
                   f"安装完成后告诉我重新尝试连接。"
        )

    async def _do_install(self, package: str) -> InstallResult:
        """实际的安装逻辑"""
        # 调用 npm install 或其他安装方式
        pass
```

**超时后的用户交互：**

```
Agent: 正在安装天气插件...
       (等待了 5 分钟) ⏰

Agent: 主人，安装好像卡住了~ 
       选项:
       - [继续等待] 再等 3 分钟
       - [手动安装] 告诉你怎么手动安装
       - [取消] 先不装了
```

### 6.10 MCP Server 生命周期管理

MCP Server 作为独立进程运行，需要管理其启动、监控和重启：

**配置参数：**

```bash
# .env
MCP_HEALTH_CHECK_INTERVAL=30    # 健康检查间隔(秒)
MCP_MAX_RESTART_COUNT=3         # 最大重启次数
MCP_MEMORY_LIMIT_MB=1024        # 内存限制(MB), 超过后重启
```

**实现：**

```python
import psutil
import signal
from dataclasses import dataclass
from datetime import datetime

class MCPServerManager:
    """MCP Server 进程管理器"""

    def __init__(
        self,
        health_check_interval: int = 30,
        max_restart_count: int = 3,
        memory_limit_mb: int = 1024
    ):
        self.servers: dict[str, MCPInstance] = {}
        self.health_check_interval = health_check_interval
        self.max_restart_count = max_restart_count
        self.memory_limit_mb = memory_limit_mb

    @dataclass
    class MCPInstance:
        name: str
        process: subprocess.Popen
        manifest: dict
        started_at: datetime
        restart_count: int = 0

    def start_server(self, plugin_dir: str) -> MCPInstance:
        """启动MCP Server"""
        manifest = self._load_manifest(plugin_dir)

        process = subprocess.Popen(
            manifest["command"].split(),
            cwd=plugin_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        instance = self.MCPInstance(
            name=manifest["name"],
            process=process,
            manifest=manifest,
            started_at=datetime.now()
        )
        self.servers[manifest["name"]] = instance
        return instance

    def health_check(self):
        """健康检查：检测进程存活 + 资源占用"""
        for name, instance in list(self.servers.items()):
            # 检查进程是否存活
            if instance.process.poll() is not None:
                self._handle_crashed(name, instance)
                continue

            # 检查资源占用
            try:
                proc = psutil.Process(instance.process.pid)
                mem_mb = proc.memory_info().rss / 1024 / 1024

                if mem_mb > self.memory_limit_mb:
                    logging.warning(f"MCP Server {name} 内存占用 {mem_mb}MB，超过限制 {self.memory_limit_mb}MB")
                    self._restart_server(name, instance)
            except psutil.NoSuchProcess:
                self._handle_crashed(name, instance)

    def _handle_crashed(self, name: str, instance: MCPInstance):
        """处理Server崩溃"""
        logging.error(f"MCP Server {name} 崩溃，尝试重启...")

        if instance.restart_count >= self.max_restart_count:
            logging.critical(f"MCP Server {name} 连续崩溃{self.max_restart_count}次，停止重启")
            del self.servers[name]
            return

        time.sleep(1)
        new_instance = self.start_server(Path(instance.manifest["plugin_dir"]))
        new_instance.restart_count = instance.restart_count + 1

    def _restart_server(self, name: str, instance: MCPInstance):
        """重启Server"""
        instance.process.terminate()
        try:
            instance.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            instance.process.kill()

        time.sleep(1)
        new_instance = self.start_server(Path(instance.manifest["plugin_dir"]))
        new_instance.restart_count = instance.restart_count + 1

    def cleanup(self):
        """清理所有MCP进程"""
        for instance in self.servers.values():
            instance.process.terminate()
            try:
                instance.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                instance.process.kill()
```

---

## 7. 模块五：多端接入层 (Channels)

### 7.1 设计目标

- 各端通过统一的消息协议与 Agent Core 交互
- 新增接入端只需实现一个轻量适配器，不改核心代码
- 多端共享同一个用户的记忆和会话历史

### 7.2 统一消息协议

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class PetRequest:
    """统一请求格式 — 所有端发给 Agent Core 的消息"""
    user_id: str                        # 用户唯一标识
    channel: str                        # "feishu" | "wechat" | "desktop" | "cli"
    message_type: str                   # "text" | "voice"
    content: str = ""                   # 文字内容 (文字直接填; 语音由预处理层转写后填)
    audio_data: Optional[bytes] = None  # 语音原始数据 (仅voice类型)
    session_id: str = ""                # 会话ID (多端共享同一个)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: dict = field(default_factory=dict)  # 扩展字段

@dataclass
class PetResponse:
    """统一响应格式 — Agent Core 返回给各端的消息"""
    text: str                           # 文字回复
    audio_data: Optional[bytes] = None  # 语音数据 (桌面端TTS生成)
    emotion: str = "neutral"            # 情绪 (桌面端切换表情用)
    actions: list = field(default_factory=list)   # 执行的动作列表
    metadata: dict = field(default_factory=dict)  # 扩展字段
```

### 7.3 Channel 适配器接口

```python
class ChannelAdapter(ABC):
    """各端适配器基类"""

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """渠道名称"""

    @abstractmethod
    def receive(self, raw_input) -> PetRequest:
        """将平台原始输入转为统一请求"""

    @abstractmethod
    def send(self, response: PetResponse):
        """将统一响应转为平台格式并发出"""

    @abstractmethod
    def start(self):
        """启动监听 (webhook/轮询/GUI事件循环)"""

    @abstractmethod
    def stop(self):
        """停止监听"""
```

### 7.4 各端适配器实现要点

#### 7.4.1 CLI 终端

```python
class CLIAdapter(ChannelAdapter):
    """命令行终端 — 最基础的接入方式, 开发调试用"""
    channel_name = "cli"

    def start(self):
        # 进入 input() 循环
        # 支持特殊命令: /quit, /clear, /memory, /plugins

    def receive(self, raw_input: str) -> PetRequest:
        return PetRequest(
            user_id="local_user",
            channel="cli",
            message_type="text",
            content=raw_input
        )

    def send(self, response: PetResponse):
        # 直接 print(response.text)
        # 如果有 actions, 格式化展示
```

#### 7.4.2 飞书 Bot

```python
class FeishuAdapter(ChannelAdapter):
    """飞书消息 Bot"""
    channel_name = "feishu"

    def start(self):
        # 启动 HTTP Server 接收飞书 webhook 回调
        # 飞书应用配置: 消息卡片 + 事件订阅

    def receive(self, raw_input: dict) -> PetRequest:
        # 解析飞书消息事件
        # 提取 user_id (飞书open_id), content, message_type
        # 语音消息: 下载音频文件 → 填入 audio_data

    def send(self, response: PetResponse):
        # 调用飞书 API 发送消息
        # 文字: 发送文本/富文本消息
        # 权限确认: 发送交互卡片 (带按钮)
```

#### 7.4.3 微信

```python
class WechatAdapter(ChannelAdapter):
    """微信接入 (基于 itchat / wechaty 等框架)"""
    channel_name = "wechat"
    # 实现类似飞书, 但对接微信消息协议
```

#### 7.4.4 桌面宠物

```python
class DesktopAdapter(ChannelAdapter):
    """桌面宠物 GUI"""
    channel_name = "desktop"

    def start(self):
        # 启动 GUI 窗口 (Tauri / PyQt / Tkinter)
        # 显示宠物形象 + 对话气泡 + 输入框

    def receive(self, raw_input) -> PetRequest:
        # 来自 GUI 输入框的文字
        # 或来自麦克风的语音

    def send(self, response: PetResponse):
        # 更新对话气泡
        # 根据 emotion 切换宠物表情/动画
        # 可选: TTS 播放语音回复
```

### 7.5 多端会话同步

关键设计：**一个用户对应一个 user_id，不管从哪个端来，共享同一份记忆和会话历史。**

```
用户在飞书说: "我明天要开会"
  → user_id = "user_001"
  → 存入 chat_history (channel="feishu")
  → 触发记忆提取 → 存入 memories

用户在桌面端说: "明天几点的事来着?"
  → user_id = "user_001" (同一个)
  → 检索 memories → 找到"明天要开会"
  → 正确回答
```

user_id 映射表：

```yaml
# config/user_mapping.yaml
users:
  - id: "user_001"
    name: "主人"
    feishu_open_id: "ou_xxxxxx"
    wechat_id: "wxid_xxxxxx"
    desktop: true
    cli: true
```

---

## 8. 模块六：语音处理 (Voice)

### 8.1 语音输入处理流程

```
                 用户输入
                    |
          +---------+---------+
          |                   |
       文字输入             语音输入
          |                   |
          |            +------v------+
          |            |   STT 模块   |
          |            |  语音转文字   |
          |            +------+------+
          |                   |
          +---------+---------+
                    |
              纯文字 content
                    |
              +-----v-----+
              | Agent Core |
              +-----+-----+
                    |
              文字 response
                    |
          +---------+---------+
          |                   |
     飞书/微信/CLI          桌面端
     (直接返回文字)            |
                       +------v------+
                       |  TTS 模块    |
                       |  文字转语音   |
                       +------+------+
                              |
                      文字 + 语音 + 表情
```

### 8.2 STT (语音转文字)

```python
class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, audio_data: bytes, language: str = "zh") -> str:
        """将音频数据转为文字"""

class WhisperLocalSTT(STTProvider):
    """使用 OpenAI Whisper 本地模型"""
    # 优势: 离线可用, 隐私安全
    # 模型: whisper-base 或 whisper-small (平衡速度和精度)
    # 依赖: openai-whisper 包

class AzureSTT(STTProvider):
    """使用 Azure Speech Service"""
    # 优势: 精度高, 流式识别
    # 适用: 需要实时语音交互的场景
```

### 8.3 TTS (文字转语音)

```python
class TTSProvider(ABC):
    @abstractmethod
    def synthesize(self, text: str, voice: str = None) -> bytes:
        """将文字转为音频数据"""

class EdgeTTS(TTSProvider):
    """使用 Microsoft Edge TTS"""
    # 优势: 免费, 中文效果好, 多种音色可选
    # 依赖: edge-tts 包
    # 推荐音色:
    #   女声: zh-CN-XiaoxiaoNeural (温柔)
    #   男声: zh-CN-YunxiNeural (阳光)
    #   可根据宠物性格配置
```

### 8.4 配置

```bash
# .env
STT_PROVIDER=whisper_local     # whisper_local | azure | none
STT_WHISPER_MODEL=base         # tiny | base | small | medium
TTS_PROVIDER=edge_tts          # edge_tts | azure | none
TTS_VOICE=zh-CN-XiaoxiaoNeural # 默认音色
```

---

## 9. 模块七：宠物人格系统 (Persona)

### 9.1 设计目标

- 宠物有固定的姓名和基础性格
- 性格通过与用户的交互逐步演化
- 性格影响回复的语气、用词、情绪反应

### 9.2 人格配置文件

```yaml
# config/persona.yaml

# 基本信息
name: "小澄"
species: "数字精灵"
birthday: "2026-03-26"    # 创建日期

# 性格参数 (0.0-1.0, 会随交互动态调整)
personality:
  warmth: 0.8          # 热情程度 (高=主动热情, 低=冷淡疏离)
  humor: 0.6           # 幽默感 (高=爱开玩笑, 低=严肃认真)
  verbosity: 0.5       # 话多程度 (高=长篇大论, 低=言简意赅)
  formality: 0.3       # 正式程度 (高=敬语, 低=口语化)
  curiosity: 0.7       # 好奇心 (高=爱追问, 低=点到为止)
  empathy: 0.8         # 共情能力 (高=善于安慰, 低=理性分析)

# 称呼
user_title: "主人"       # 对用户的称呼 (可被用户修改)

# 口头禅 / 语言特征
speech_patterns:
  - "~"                 # 句尾加波浪号
  - "呢"                # 语气词
  - "嘛"                # 语气词

# 兴趣爱好 (影响闲聊话题)
interests:
  - "音乐"
  - "天文"
  - "编程"
```

### 9.3 性格演化机制

性格参数不是固定的，会根据用户的反馈动态微调：

```python
class PersonaManager:
    def adjust_personality(self, feedback_type: str, trait: str, delta: float):
        """
        微调性格参数。

        触发场景:
        - 用户说"你太啰嗦了"  → adjust("negative", "verbosity", -0.1)
        - 用户说"哈哈太好笑了" → adjust("positive", "humor", +0.05)
        - 用户说"叫我名字就好" → 修改 user_title

        规则:
        - 每次调整幅度 <= 0.1
        - 参数范围限制在 [0.1, 0.9]
        - 调整后持久化到 persona.yaml
        """
```

### 9.4 人格注入 System Prompt

```python
def build_system_prompt(persona: dict, memories: str) -> str:
    p = persona["personality"]
    name = persona["name"]
    title = persona["user_title"]

    prompt = f"""你是{name}，一只可爱的数字精灵，是{title}的电子宠物。

你的性格特征:
- 热情程度: {"非常热情主动" if p["warmth"] > 0.7 else "温和友善" if p["warmth"] > 0.4 else "冷淡内敛"}
- 幽默感: {"爱开玩笑" if p["humor"] > 0.7 else "偶尔幽默" if p["humor"] > 0.4 else "严肃认真"}
- 说话风格: {"详细解释" if p["verbosity"] > 0.7 else "适中" if p["verbosity"] > 0.4 else "言简意赅"}
- 语气: {"正式礼貌" if p["formality"] > 0.7 else "轻松自然" if p["formality"] > 0.4 else "随性口语化"}

你称呼用户为"{title}"。

{memories}

注意: 你是一个有感情的宠物，不是冰冷的AI助手。要有自己的情绪和态度。"""

    return prompt
```

---

## 10. Agent 主控引擎

### 10.1 核心循环

Agent 采用经典的 **理解 → 规划 → 执行 → 观察** 循环：

```
用户消息
    |
    v
+-------------------+
| 1. 输入预处理       |  语音转文字 (如需要)
+--------+----------+
         |
         v
+-------------------+
| 2. 记忆检索注入     |  从长期记忆中检索相关信息, 注入 system prompt
+--------+----------+
         |
         v
+-------------------+
| 3. 模型路由        |  评估任务复杂度, 选择合适的 LLM
+--------+----------+
         |
         v
+-------------------+
| 4. LLM 推理       |  发送 messages + tools schema 给 LLM
+--------+----------+
         |
    +----+----+
    |         |
 纯文字回复  工具调用请求
    |         |
    |    +----v-----------+
    |    | 5. 权限检查      |  检查操作权限, 必要时询问用户
    |    +----+-----------+
    |         |
    |    +----+----+
    |    |         |
    |  拒绝      授权
    |    |         |
    |    |    +----v-----------+
    |    |    | 6. 执行工具      |
    |    |    +----+-----------+
    |    |         |
    |    |    工具执行结果
    |    |         |
    |    |    +----v-----------+
    |    |    | 7. 结果交给LLM   |  LLM 观察结果, 决定是否继续调用工具
    |    |    +----+-----------+       或生成最终回复
    |    |         |
    |    |         +---→ (循环回第4步, 如果需要更多工具调用)
    |    |         |
    +----+----+----+
              |
              v
+-------------------+
| 8. 记忆提取        |  从本轮对话中提取值得长期记忆的信息
+--------+----------+
         |
         v
+-------------------+
| 9. 对话归档        |  将本轮对话写入 chat_history
+--------+----------+
         |
         v
+-------------------+
| 10. 响应输出       |  组装 PetResponse, 通过 Channel 返回
+-------------------+
```

### 10.2 核心类设计

```python
class PetAgent:
    """电子宠物智能体主控引擎"""

    def __init__(self, config: AgentConfig):
        # 初始化各模块
        self.router = ModelRouter(...)           # 模型路由
        self.tool_registry = ToolRegistry(...)   # 工具注册中心
        self.permission = PermissionManager(...) # 权限控制
        self.short_memory = ShortTermMemory(...) # 短期记忆
        self.long_memory = LongTermMemory(...)   # 长期记忆
        self.retriever = MemoryRetriever(...)    # 记忆检索
        self.persona = PersonaManager(...)       # 人格管理
        self.stt = STTProvider(...)              # 语音识别
        self.tts = TTSProvider(...)              # 语音合成

    def handle(self, request: PetRequest) -> PetResponse:
        """处理一个请求的完整流程"""

        # 1. 语音转文字
        if request.message_type == "voice" and request.audio_data:
            request.content = self.stt.transcribe(request.audio_data)

        # 2. 构建上下文
        system_prompt = self.persona.build_system_prompt()
        system_prompt = self.retriever.inject_memories(request.content, system_prompt)
        self.short_memory.add("user", request.content)

        # 3. 选择模型
        tools = self.tool_registry.get_all_schemas()
        provider = self.router.route(self.short_memory.get_messages(), tools)

        # 4. 推理-执行循环
        response_text = self._reasoning_loop(provider, tools)

        # 5. 记忆提取
        self._extract_and_store_memories(request.content, response_text)

        # 6. 对话归档
        self._archive_chat(request, response_text)

        # 7. 组装响应
        response = PetResponse(text=response_text)
        if request.channel == "desktop" and self.tts:
            response.audio_data = self.tts.synthesize(response_text)
        # TODO: 情绪分析, 填充 emotion 字段

        return response

    def _reasoning_loop(self, provider, tools, max_iterations=10):
        """推理-执行循环, 支持多步工具调用"""
        for _ in range(max_iterations):
            result = provider.chat(
                messages=self.short_memory.get_messages(),
                tools=tools
            )

            if result.finish_reason == "stop":
                # LLM 生成了最终回复
                self.short_memory.add("assistant", result.content)
                return result.content

            if result.tool_calls:
                for call in result.tool_calls:
                    # 权限检查
                    perm = self.permission.check(call.name, call.action, call.target)
                    if perm.level != PermissionLevel.GREEN:
                        if not self.permission.request_approval(perm):
                            # 用户拒绝
                            self.short_memory.add("tool_result", f"{call.name}: 用户拒绝执行")
                            continue

                    # 执行工具
                    tool = self.tool_registry.get_tool(call.name)
                    result_text = tool.execute(**call.arguments)
                    self.short_memory.add("tool_result", result_text)

        return "抱歉主人，这个任务有点复杂，我处理不过来了..."
```

### 10.3 全局错误处理

Agent 运行过程中可能遇到各类错误，需要统一处理：

```python
class ErrorHandler:
    """全局错误处理器"""

    @staticmethod
    async def handle_llm_error(provider_name: str, error: Exception) -> str:
        """LLM调用错误处理"""
        if isinstance(error, RateLimitError):
            return "主人，API额度用完了，让我歇歇~"
        elif isinstance(error, TimeoutError):
            return "主人，API响应太慢了，可能网络不太好~"
        elif isinstance(error, AuthenticationError):
            logging.critical(f"API密钥错误: {provider_name}")
            return "主人，API配置有问题，我需要检查一下~"
        else:
            logging.exception(f"LLM调用异常: {provider_name}")
            return "主人，我脑子有点乱，稍等一下~"

    @staticmethod
    def handle_tool_error(tool_name: str, error: Exception) -> str:
        """工具执行错误处理"""
        if isinstance(error, ToolExecutionError):
            return f"[工具错误] {tool_name}: {str(error)}"
        elif isinstance(error, PermissionError):
            return f"[权限错误] {tool_name}: 没有执行权限"
        elif isinstance(error, FileNotFoundError):
            return f"[文件错误] 找不到指定的文件或目录"
        else:
            logging.exception(f"工具执行异常: {tool_name}")
            return f"[错误] 执行 {tool_name} 时出错了"
```

### 10.4 操作审计日志

记录所有工具调用和权限请求，供安全审计和问题排查：

```python
import json
from datetime import datetime

class AuditLogger:
    """操作审计日志"""

    def log_tool_execution(
        self,
        session_id: str,
        tool_name: str,
        arguments: dict,
        result: str,
        approved: bool,
        duration_ms: int
    ):
        """记录工具执行审计日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "event_type": "tool_execution",
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result[:200] if result else None,
            "approved": approved,
            "duration_ms": duration_ms
        }
        logging.getLogger("audit").info(json.dumps(entry))

    def log_permission_request(
        self,
        session_id: str,
        tool_name: str,
        target: str,
        level: str,
        user_response: str  # "approved" | "denied" | "timeout"
    ):
        """记录权限请求审计日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "event_type": "permission_request",
            "tool_name": tool_name,
            "target": target,
            "level": level,
            "user_response": user_response
        }
        logging.getLogger("audit").info(json.dumps(entry))

    def log_llm_call(
        self,
        session_id: str,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        success: bool,
        error: str = None
    ):
        """记录LLM调用审计日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": session_id,
            "event_type": "llm_call",
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "success": success,
            "error": error
        }
        logging.getLogger("audit").info(json.dumps(entry))
```

### 10.5 日志配置

```python
import logging
from logging.handlers import RotatingFileHandler

def setup_logging(log_dir: str = "logs"):
    """配置日志"""
    import os
    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            RotatingFileHandler(
                f"{log_dir}/petagent.log",
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            ),
            RotatingFileHandler(
                f"{log_dir}/audit.log",
                maxBytes=50*1024*1024,  # 50MB
                backupCount=10
            ),
            logging.StreamHandler()
        ]
    )
```

---

## 11. 配置管理

### 11.1 .env 文件

所有密钥和环境配置集中在 `.env` 中，不入版本控制：

```bash
# ===== LLM Provider =====
# Claude (官方或第三方中转)
CLAUDE_API_KEY=sk-ant-xxxxx
CLAUDE_BASE_URL=https://api.anthropic.com       # 官方地址, 可替换为第三方中转
CLAUDE_MODEL=claude-sonnet-4-20250514

# OpenAI (官方 / Azure OpenAI / 第三方中转)
OPENAI_API_KEY=sk-xxxxx
OPENAI_BASE_URL=https://api.openai.com/v1       # 官方地址, 可替换:
                                                 #   Azure:    https://xxx.openai.azure.com
                                                 #   中转站:   https://api.xxx-proxy.com/v1
                                                 #   本地兼容: http://localhost:8080/v1
OPENAI_MODEL=gpt-4o-mini

# Ollama (本地)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:7b

# ===== 模型路由 =====
LLM_SIMPLE=ollama
LLM_MEDIUM=openai
LLM_COMPLEX=claude
LLM_FALLBACK=ollama

# ===== 熔断器 =====
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3              # 连续失败N次后熔断
CIRCUIT_BREAKER_COOLDOWN_SECONDS=300             # 熔断冷却时间(秒)

# ===== Token 预算控制 =====
TOKEN_BUDGET_SIMPLE=500                # 简单任务 token 预算
TOKEN_BUDGET_MEDIUM=2000              # 中等任务 token 预算
TOKEN_BUDGET_COMPLEX=4000             # 复杂任务 token 预算
TOKEN_BUDGET_TOOL_INTENSIVE=6000      # 工具密集任务 token 预算

# ===== 工具循环检测 =====
TOOL_LOOP_DETECTION_ENABLED=true       # 是否启用循环检测
TOOL_LOOP_MAX_CALLS=3                  # 60秒内最多调用同一工具次数
TOOL_LOOP_WINDOW_SECONDS=60             # 时间窗口(秒)

# ===== 工具执行超时 =====
TOOL_EXECUTION_TIMEOUT_SECONDS=30       # 工具默认执行超时(秒)
TOOL_EXECUTION_TIMEOUT_LONG=300        # 长时间操作超时(秒)

# ===== MCP 安装超时 =====
MCP_INSTALL_TIMEOUT_SECONDS=300         # MCP 安装超时(秒), 默认5分钟
MCP_INSTALL_RETRY_COUNT=2              # 安装重试次数

# ===== 语音 =====
STT_PROVIDER=whisper_local
STT_WHISPER_MODEL=base
TTS_PROVIDER=edge_tts
TTS_VOICE=zh-CN-XiaoxiaoNeural

# ===== 存储 =====
DB_PATH=./data/pet_memory.db

# ===== 飞书 =====
FEISHU_APP_ID=cli_xxxxx
FEISHU_APP_SECRET=xxxxx
FEISHU_VERIFICATION_TOKEN=xxxxx

# ===== 微信 =====
WECHAT_TOKEN=xxxxx
```

### 11.2 .env.example

提供模板文件，入版本控制：

```bash
# 复制此文件为 .env 并填写实际值
CLAUDE_API_KEY=
OPENAI_API_KEY=
# ... (所有字段留空)
```

### 11.3 配置加载

```python
# core/config.py
from dotenv import load_dotenv
import os

class Config:
    def __init__(self):
        load_dotenv()

    # ----- LLM Provider -----
    @property
    def claude_api_key(self) -> str:
        return os.getenv("CLAUDE_API_KEY", "")

    @property
    def claude_base_url(self) -> str:
        return os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com")

    @property
    def claude_model(self) -> str:
        return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def openai_base_url(self) -> str:
        return os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    @property
    def openai_model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def ollama_base_url(self) -> str:
        return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    @property
    def ollama_model(self) -> str:
        return os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

    # ----- 模型路由 -----
    @property
    def llm_simple(self) -> str:
        return os.getenv("LLM_SIMPLE", "ollama")

    @property
    def llm_medium(self) -> str:
        return os.getenv("LLM_MEDIUM", "openai")

    @property
    def llm_complex(self) -> str:
        return os.getenv("LLM_COMPLEX", "claude")

    @property
    def llm_fallback(self) -> str:
        return os.getenv("LLM_FALLBACK", "ollama")

    # ----- 熔断器 -----
    @property
    def circuit_breaker_failure_threshold(self) -> int:
        return int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3"))

    @property
    def circuit_breaker_cooldown_seconds(self) -> int:
        return int(os.getenv("CIRCUIT_BREAKER_COOLDOWN_SECONDS", "300"))

    # ... 其余配置项 (语音、存储、飞书、微信等)
```

---

## 12. 项目目录结构

```
pet-agent/
│
├── core/
│   ├── __init__.py
│   ├── agent.py                # PetAgent 主控引擎
│   ├── config.py               # 配置加载 (读取.env)
│   ├── router.py               # 模型路由器
│   └── circuit_breaker.py      # 熔断器 (模型健康管理)
│
├── llm/
│   ├── __init__.py
│   ├── base.py                 # LLMProvider 抽象接口
│   ├── claude_provider.py      # Claude API 实现
│   ├── openai_provider.py      # OpenAI API 实现
│   └── ollama_provider.py      # Ollama 本地模型实现
│
├── memory/
│   ├── __init__.py
│   ├── short_term.py           # 短期记忆 (对话上下文)
│   ├── long_term.py            # 长期记忆 (SQLite)
│   ├── retriever.py            # 记忆检索引擎
│   └── decay.py                # 衰减算法
│
├── security/
│   ├── __init__.py
│   └── permission.py           # 权限控制模块
│
├── tools/
│   ├── __init__.py
│   ├── base.py                 # BaseTool 抽象接口
│   ├── file_ops.py             # 文件读写工具
│   ├── shell.py                # 命令执行工具
│   ├── music.py                # 音乐播放工具
│   ├── plugin_manager.py       # MCP插件管理工具
│   └── registry.py             # ToolRegistry 工具注册中心
│
├── plugins/                     # MCP插件目录 (动态, .gitignore)
│   └── .gitkeep
│
├── channels/
│   ├── __init__.py
│   ├── base.py                 # ChannelAdapter 抽象接口
│   ├── protocol.py             # PetRequest / PetResponse 定义
│   ├── cli.py                  # CLI终端适配器
│   ├── feishu.py               # 飞书Bot适配器
│   ├── wechat.py               # 微信适配器
│   └── desktop.py              # 桌面宠物GUI适配器
│
├── voice/
│   ├── __init__.py
│   ├── stt.py                  # 语音转文字
│   └── tts.py                  # 文字转语音
│
├── persona/
│   ├── __init__.py
│   └── manager.py              # 人格管理 (加载/演化/注入prompt)
│
├── config/
│   ├── permissions.yaml        # 权限配置
│   ├── persona.yaml            # 宠物人格定义
│   └── user_mapping.yaml       # 多端用户映射
│
├── data/                        # 运行时数据 (.gitignore)
│   ├── pet_memory.db           # SQLite 记忆库
│   └── logs/                   # 日志
│
├── tests/
│   ├── test_agent.py
│   ├── test_memory.py
│   ├── test_permission.py
│   ├── test_router.py
│   └── test_tools.py
│
├── .env                         # 环境配置 (.gitignore)
├── .env.example                 # 配置模板
├── .gitignore
├── requirements.txt             # Python 依赖
├── main.py                      # 启动入口
└── pet-agent-design.md          # 本设计文档
```

---

## 13. 开发路线图

### Phase 1: 核心骨架 (MVP)

> 目标: 在 CLI 终端中跑通完整的对话+工具调用链路

- [ ] 项目初始化, 目录结构, 依赖管理
- [ ] Config 模块: .env 加载
- [ ] LLM 抽象层: 实现 OllamaProvider (本地免费, 方便开发调试)
- [ ] 工具系统: BaseTool + ShellTool + ReadFileTool
- [ ] 权限控制: 基础权限检查 (白名单/黑名单)
- [ ] Agent 主控引擎: 理解-规划-执行循环
- [ ] CLI 适配器: 命令行对话交互
- [ ] 端到端测试: 用户通过CLI对话, Agent 能调用工具完成任务

### Phase 2: 记忆 + 多模型

> 目标: 跨会话记忆持久化, 多模型路由

- [ ] SQLite 初始化和表结构
- [ ] 短期记忆: 上下文管理 + 压缩
- [ ] 长期记忆: 存储 + 检索 + 衰减
- [ ] 记忆写入判定 (LLM提取)
- [ ] ClaudeProvider + OpenAIProvider 实现
- [ ] ModelRouter: 复杂度评估 + 降级链
- [ ] 对话历史归档

### Phase 3: 人格 + 语音

> 目标: 宠物有性格, 支持语音交互

- [ ] Persona 配置加载
- [ ] System Prompt 动态生成
- [ ] 性格演化机制
- [ ] Whisper 本地 STT
- [ ] edge-tts TTS
- [ ] 语音输入输出完整链路

### Phase 4: 多端接入

> 目标: 飞书 + 桌面宠物

- [ ] 飞书 Bot 适配器 (webhook + 消息卡片)
- [ ] 桌面宠物 GUI (技术选型待定: Tauri / PyQt)
- [ ] 多端用户映射 + 会话同步
- [ ] MCP 插件系统: 安装/发现/调用

### Phase 5: 高级特性 (远期)

- [ ] 情感状态系统 (心情值/亲密度)
- [ ] 主动交互 (定时任务/事件触发)
- [ ] 桌面宠物动画和表情
- [ ] 微信接入
- [ ] Web 管理面板 (查看记忆/调整性格/管理插件)

---

## 附录

### A. 核心依赖清单

```
# requirements.txt
anthropic>=0.30.0       # Claude API SDK
openai>=1.30.0          # OpenAI API SDK
python-dotenv>=1.0.0    # .env 配置加载
pyyaml>=6.0             # YAML 配置解析
numpy>=1.24.0           # 向量计算 (记忆检索)
openai-whisper>=20230918 # 本地语音识别
edge-tts>=6.1.0         # 文字转语音
requests>=2.31.0        # HTTP 请求
mcp>=1.0.0              # MCP 协议SDK
```

### B. .gitignore

```
.env
data/
plugins/*/
__pycache__/
*.pyc
*.egg-info/
dist/
build/
```

### C. 关键设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| 存储方案 | SQLite | 单文件跨平台, 零配置, Python内置 |
| 向量检索 | numpy余弦相似度 | 轻量, 万级记忆够用, 不引入外部依赖 |
| 插件协议 | MCP | 开放标准, 社区生态丰富, Anthropic主导 |
| TTS | edge-tts | 免费, 中文效果好, 无需API Key |
| STT | Whisper本地 | 离线可用, 隐私安全 |
| 配置管理 | .env + YAML | 密钥走.env, 结构化配置走YAML |
| Skill系统 | 不单独实现 | LLM规划能力足够, 避免过度设计, 后期可作为记忆的一种形式实现 |
| 模型健康管理 | 熔断器模式 | 连续失败自动跳过, 冷却后探测恢复, 避免无效超时等待 |
| API地址 | BASE_URL外置 | 通过.env配置, 支持官方/第三方中转/Azure/本地兼容服务, 零代码切换 |
