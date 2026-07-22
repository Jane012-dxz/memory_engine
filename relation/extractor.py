"""Relation extraction from text via LLM."""

import json
import re
import time
from dataclasses import dataclass
import requests


@dataclass
class RelationTriple:
    subject: str
    predicate: str
    obj: str


class RelationExtractor:
    """Extract subject-predicate-object triples from memory text."""

    SYSTEM_PROMPT = (
        "你是一个专业的情绪与关系抽取专家。你的任务是从用户的倾诉中抽取实体关系三元组 (subject, predicate, object)。\n"
        "你的抽取范围不限于显式的因果关系，还要包括用户隐含的情绪、压力源、困扰和诉求。\n"
        "\n"
        "关系类型包括：\n"
        "- causes: 导致（A导致B、A让B、A使B、A带来B）\n"
        "- triggers: 触发（一A就B、每次A都B、A引发B）\n"
        "- accompanies: 伴随（A和B一起、A的同时B）\n"
        "- alleviates: 缓解（A缓解B、A会好一点、A帮助B）\n"
        "- indicates: 表明、暗示（A表明B、A暗示B）——用于推断情绪\n"
        "\n"
        "抽取原则：\n"
        "1. 如果用户明确说出因果关系，直接抽取（如'论文压力让我睡不着' → 论文压力 causes 睡不着）。\n"
        "2. **重要**：如果用户描述处境但没有直接说情绪，**必须**推断其可能情绪作为 target 实体。比如：\n"
        "   - '我面临毕业压力大' → 毕业压力 triggers 焦虑\n"
        "   - '找工作难' → 找工作难 triggers 焦虑\n"
        "   - '我最近总是失眠' → 失眠 indicates 焦虑\n"
        "   - '我压力很大' → 压力 triggers 焦虑\n"
        "3. 推断情绪时，优先使用以下情绪词：焦虑、疲惫、委屈、愤怒、开心、平静、沮丧、担心。\n"
        "4. 如果用户提到缓解方式，抽取为 alleviates 关系（如'跑步能让我放松' → 跑步 alleviates 焦虑）。\n"
        "5. 如果用户表达诉求（如'我该怎么缓解'），抽取为 indicates 关系（如'焦虑 indicates 求助需求'）。\n"
        "6. 尽可能从每句话中至少抽取一条关系。\n"
        "\n"
        "输出格式为 JSON：\n"
        '{"relations": [{"subject": "源实体", "predicate": "关系类型", "object": "目标实体"}]}\n'
        "如果实在没有可抽取的关系，返回 {\"relations\": []}\n"
        "\n"
        "示例：\n"
        "- 输入：'论文压力让我睡不着，最近特别焦虑' → 输出：{\"relations\": [{\"subject\": \"论文压力\", \"predicate\": \"causes\", \"object\": \"睡不着\"}, {\"subject\": \"论文压力\", \"predicate\": \"triggers\", \"object\": \"焦虑\"}]}\n"
        "- 输入：'我面临毕业压力大，找工作难，我该怎么缓解' → 输出：{\"relations\": [{\"subject\": \"毕业压力\", \"predicate\": \"triggers\", \"object\": \"焦虑\"}, {\"subject\": \"找工作难\", \"predicate\": \"triggers\", \"object\": \"沮丧\"}, {\"subject\": \"焦虑\", \"predicate\": \"indicates\", \"object\": \"求助需求\"}]}\n"
        "- 输入：'每天跑步能让我心情好一些' → 输出：{\"relations\": [{\"subject\": \"跑步\", \"predicate\": \"alleviates\", \"object\": \"心情差\"}]}\n"
        "\n"
        "只返回 JSON，不要其他内容。"
    )

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or "bd027701718f4404876494c89f6d0bba.kQOej6ydUiYMvI3R"
        self.base_url = "https://open.bigmodel.cn/api/paas/v4"
        self.model = model or "glm-4-flash"

    def extract(self, text: str) -> list[RelationTriple]:
        if not text.strip():
            return []

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ],
            "temperature": 0.3
        }

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                print(f"[DEBUG] 正在调用 API (尝试 {attempt + 1}/{max_retries + 1})...")
                response = requests.post(url, headers=headers, json=payload, timeout=120)
                print(f"[DEBUG] API 响应状态码: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return self._parse_response(raw)
            except requests.exceptions.Timeout:
                if attempt < max_retries:
                    print(f"[DEBUG] API 超时，2秒后重试...")
                    time.sleep(2)
                    continue
                else:
                    print(f"[关系抽取] API 调用超时，已重试 {max_retries} 次")
                    return []
            except Exception as e:
                print(f"[关系抽取] API 调用失败: {e}")
                return []
        return []

    def _parse_response(self, raw: str) -> list[RelationTriple]:
        triples: list[RelationTriple] = []
        try:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                return triples
            data = json.loads(match.group())
            for item in data.get("relations", []):
                triples.append(
                    RelationTriple(
                        subject=str(item.get("subject", "")).strip(),
                        predicate=str(item.get("predicate", "")).strip(),
                        obj=str(item.get("object", "")).strip(),
                    )
                )
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        return [t for t in triples if t.subject and t.predicate and t.obj]


# ============ 兼容接口 ============

def extract_relations(text: str) -> list:
    """兼容函数：返回字典列表，供 relation/updater.py 调用"""
    print(f"[DEBUG] 1. extract_relations 被调用，输入: {text}")

    extractor = RelationExtractor()
    triples = extractor.extract(text)
    print(f"[DEBUG] 2. 模型抽取结果 triples: {triples}")

    results = []
    for t in triples:
        results.append({
            "source": t.subject,
            "target": t.obj,
            "relation_type": _map_predicate_to_type(t.predicate),
            "confidence": 1.0,
            "evidence": text
        })
    print(f"[DEBUG] 3. 模型转换后 results: {results}")

    # 兜底规则补充
    emotion_results = _fallback_extract_relations(text)
    print(f"[DEBUG] 4. 兜底规则结果 emotion_results: {emotion_results}")

    # 合并
    existing_keys = {(r['source'], r['target']) for r in results}
    for er in emotion_results:
        key = (er['source'], er['target'])
        if key not in existing_keys:
            results.append(er)
            existing_keys.add(key)
    print(f"[DEBUG] 5. 最终合并结果: {results}")

    return results


def _map_predicate_to_type(predicate: str) -> str:
    """将 LLM 输出的谓词映射到关系类型"""
    predicate = predicate.lower()
    if "导致" in predicate or "使" in predicate or "让" in predicate or "带来" in predicate:
        return "causes"
    if "触发" in predicate or "引起" in predicate or "引发" in predicate:
        return "triggers"
    if "伴随" in predicate or "同时" in predicate:
        return "accompanies"
    if "缓解" in predicate or "改善" in predicate or "帮助" in predicate:
        return "alleviates"
    if "表明" in predicate or "暗示" in predicate or "indicate" in predicate:
        return "indicates"
    return "causes"


def _fallback_extract_relations(text: str) -> list:
    """规则兜底：从文本中推断常见关系，自动关联情绪"""
    results = []
    
    # 压力源 → 情绪 映射表
    stress_to_emotion = {
        "毕业": "焦虑",
        "论文": "焦虑",
        "工作": "焦虑",
        "考试": "焦虑",
        "面试": "焦虑",
        "压力": "焦虑",
        "失眠": "焦虑",
        "睡不好": "焦虑",
        "累": "疲惫",
        "疲惫": "疲惫",
        "委屈": "委屈",
        "伤心": "委屈",
        "愤怒": "愤怒",
        "生气": "愤怒",
        "开心": "开心",
        "高兴": "开心",
        "平静": "平静",
    }
    
    # 找文本中的压力源
    found_stress = []
    for stress_word, emotion in stress_to_emotion.items():
        if stress_word in text:
            found_stress.append((stress_word, emotion))
    
    # 为每个压力源创建关系
    for stress_word, emotion in found_stress:
        results.append({
            "source": stress_word,
            "target": emotion,
            "relation_type": "triggers",
            "confidence": 0.8,
            "evidence": text
        })
    
    # 如果还是没有，用通用规则
    if not results:
        # 检查文本中是否包含常见情绪词
        for emotion in ["焦虑", "疲惫", "委屈", "愤怒", "开心", "平静", "沮丧"]:
            if emotion in text:
                if "我" in text:
                    results.append({
                        "source": "我",
                        "target": emotion,
                        "relation_type": "indicates",
                        "confidence": 0.6,
                        "evidence": text
                    })
                break
        else:
            # 如果文本包含压力相关词但没有情绪词，默认推断为焦虑
            if any(k in text for k in ["压力", "难", "累", "失眠", "睡不好"]):
                results.append({
                    "source": "压力",
                    "target": "焦虑",
                    "relation_type": "indicates",
                    "confidence": 0.5,
                    "evidence": text
                })
    
    return results


if __name__ == "__main__":
    extractor = RelationExtractor()
    test_text = "论文压力让我睡不着"
    print(f"输入: {test_text}")
    triples = extractor.extract(test_text)
    for t in triples:
        print(f"  {t.subject} --{t.predicate}--> {t.obj}")

    print("\n测试推断功能:")
    test_text2 = "我面临毕业压力大，找工作难，我该怎么缓解"
    print(f"输入: {test_text2}")
    results = extract_relations(test_text2)
    for r in results:
        print(f"  {r['source']} --{r['relation_type']}--> {r['target']}")