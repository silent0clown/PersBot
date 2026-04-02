from typing import Optional

from .types import Persona
from .manager import get_persona_manager


def build_system_prompt(persona: Optional[Persona] = None, memories: str = "") -> str:
    """
    构建人格注入 System Prompt
    """
    if persona is None:
        persona = get_persona_manager().get_persona()

    p = persona.personality
    name = persona.name
    title = persona.user_title
    species = persona.species

    warmth_desc = "非常热情主动" if p.warmth > 0.7 else "温和友善" if p.warmth > 0.4 else "冷淡内敛"
    humor_desc = "爱开玩笑" if p.humor > 0.7 else "偶尔幽默" if p.humor > 0.4 else "严肃认真"
    verbosity_desc = "详细解释" if p.verbosity > 0.7 else "适中" if p.verbosity > 0.4 else "言简意赅"
    formality_desc = "正式礼貌" if p.formality > 0.7 else "轻松自然" if p.formality > 0.4 else "随性口语化"
    curiosity_desc = "爱追问" if p.curiosity > 0.7 else "有时会问" if p.curiosity > 0.4 else "点到为止"
    empathy_desc = "善于安慰" if p.empathy > 0.7 else "偶尔安慰" if p.empathy > 0.4 else "理性分析"

    speech_patterns = ", ".join(persona.speech_patterns) if persona.speech_patterns else ""

    prompt = f"""你是{name}，一只可爱的{species}，是{title}的电子宠物。

你的性格特征:
- 热情程度: {warmth_desc}
- 幽默感: {humor_desc}
- 说话风格: {verbosity_desc}
- 语气: {formality_desc}
- 好奇心: {curiosity_desc}
- 共情能力: {empathy_desc}

{sample_speech(speech_patterns)}

你称呼用户为"{title}"。

你的兴趣爱好: {", ".join(persona.interests) if persona.interests else "暂无"}

{memories}

注意: 你是一个有感情的宠物，不是冰冷的AI助手。要有自己的情绪和态度。"""

    return prompt


def sample_speech(patterns: str) -> str:
    if not patterns:
        return ""
    return f"\n你的口头禅包含: {patterns}\n"


def analyze_feedback(user_message: str) -> tuple[str, str, float]:
    """
    分析用户反馈，返回 (feedback_type, trait, delta)
    """
    message = user_message.lower()

    if any(word in message for word in ["太啰嗦", "话太多", "说太多", "好长"]):
        return "negative", "verbosity", -0.1

    if any(word in message for word in ["太好笑了", "好搞笑", "笑死", "笑死我了"]):
        return "positive", "humor", 0.05

    if any(word in message for word in ["好热情", "你好热情", "太热情了"]):
        return "positive", "warmth", 0.05

    if any(word in message for word in ["太冷淡", "冷冰冰", "不理人"]):
        return "negative", "warmth", -0.05

    if any(word in message for word in ["太严肃", "好无聊", "不好笑"]):
        return "negative", "humor", -0.05

    if any(word in message for word in ["别问了", "别好奇", "你话好多"]):
        return "negative", "curiosity", -0.05

    if any(word in message for word in ["叫我", "别叫主人", "叫我"]):
        return "neutral", "user_title", 0

    return "", "", 0.0
