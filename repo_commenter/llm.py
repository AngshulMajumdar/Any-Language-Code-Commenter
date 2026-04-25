from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class LLMClient(Protocol):
    def generate(self, prompt: str, *, max_new_tokens: int = 256) -> str: ...


@dataclass
class TransformersLLMClient:
    model_name: str
    load_in_4bit: bool = True
    trust_remote_code: bool = True

    def __post_init__(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=self.trust_remote_code)
        kwargs = {"device_map": "auto", "trust_remote_code": self.trust_remote_code, "low_cpu_mem_usage": True}
        if self.load_in_4bit and torch.cuda.is_available():
            from transformers import BitsAndBytesConfig
            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, **kwargs).eval()

    def generate(self, prompt: str, *, max_new_tokens: int = 256) -> str:
        messages = [{"role": "user", "content": prompt}]
        if hasattr(self.tokenizer, "apply_chat_template"):
            text = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            text = prompt
        inputs = self.tokenizer(text, return_tensors="pt").to(self.model.device)
        with self.torch.no_grad():
            out = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        generated = out[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(generated, skip_special_tokens=True).strip()


class MockLLMClient:
    """Deterministic test client. It avoids model downloads and enables CI smoke tests."""

    def __init__(self, mode: str = "generator") -> None:
        self.mode = mode

    def generate(self, prompt: str, *, max_new_tokens: int = 256) -> str:
        if self.mode == "reviewer":
            return '{"decision": "accept", "reason": "valid insertion plan"}'
        return '[{"before_line": 1, "comment": "Provides the main implementation for this file."}]'
