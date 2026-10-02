import json
from typing import Dict, Any, Union, List


def clean_json_output(content: Union[str, List[Any], Any]) -> Dict[str, Any]:
    """
    LLM çıktısından Markdown kod bloklarını (```json ... ``` veya ``` ... ```)
    temizleyip geçerli bir Python sözlüğü (dict) olarak parse eder.
    LangChain'in yeni modellerinde content string veya blok listesi olabilir.
    """
    if isinstance(content, list):
        text_parts = []
        for part in content:
            if isinstance(part, dict):
                text_parts.append(str(part.get("text", "")))
            elif hasattr(part, "text"):
                text_parts.append(str(part.text))
            else:
                text_parts.append(str(part))
        text = "".join(text_parts).strip()
    else:
        text = str(content).strip()

    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    return json.loads(text)
