"""Qwen3-Reranker-0.6B as a local cross-encoder (agent/retrieval_spec.en.md §4.2 item 6), following the model card's
transformers recipe. Only the order is used: the probability never leaves this module (no scores in returns)."""
import os

MODEL = "Qwen/Qwen3-Reranker-0.6B"
MAX_LEN = 2048
INSTRUCT = {
    "law": "Given a question about cross-border dividend taxation, retrieve the statutory provision, treaty article or official guidance that answers it",
    "products": "Given a question about the tax computation of holding structures, retrieve the computed record that answers it",
    "case": "Given a question about a client's facts, retrieve the passage of the client's documents or statements that answers it",
    "all": "Given a question about a cross-border dividend tax case, retrieve whatever answers it best: a statutory provision or treaty article, "
           "a computed record of the case's tax structures, or a passage of the client's documents and statements",
}
_m = None


def _load():
    global _m
    if _m is None:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        dev = "cuda" if torch.cuda.is_available() else "cpu"
        tok = AutoTokenizer.from_pretrained(MODEL, padding_side="left")
        model = AutoModelForCausalLM.from_pretrained(MODEL, torch_dtype=torch.float16 if dev == "cuda" else torch.float32).to(dev).eval()
        prefix = ("<|im_start|>system\nJudge whether the Document meets the requirements based on the Query and the Instruct provided. "
                  "Note that the answer can only be \"yes\" or \"no\".<|im_end|>\n<|im_start|>user\n")
        suffix = "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
        _m = {"tok": tok, "model": model, "dev": dev, "pre": tok.encode(prefix, add_special_tokens=False),
              "suf": tok.encode(suffix, add_special_tokens=False), "yes": tok.convert_tokens_to_ids("yes"), "no": tok.convert_tokens_to_ids("no")}
    return _m


def order(query, docs, material="law", batch=8):
    """Indices of docs, most relevant first."""
    if len(docs) <= 1:
        return list(range(len(docs)))
    import torch
    m = _load()
    tok, model = m["tok"], m["model"]
    texts = ["<Instruct>: %s\n<Query>: %s\n<Document>: %s" % (INSTRUCT.get(material, INSTRUCT["law"]), query, d) for d in docs]
    probs = []
    for i in range(0, len(texts), batch):
        enc = tok(texts[i:i + batch], padding=False, truncation="longest_first", return_attention_mask=False,
                  max_length=MAX_LEN - len(m["pre"]) - len(m["suf"]))
        enc["input_ids"] = [m["pre"] + ids + m["suf"] for ids in enc["input_ids"]]
        enc = tok.pad(enc, padding=True, return_tensors="pt", max_length=MAX_LEN)
        enc = {k: v.to(m["dev"]) for k, v in enc.items()}
        with torch.no_grad():
            logits = model(**enc).logits[:, -1, :]
        pair = torch.stack([logits[:, m["no"]], logits[:, m["yes"]]], dim=1).float()
        probs += torch.nn.functional.log_softmax(pair, dim=1)[:, 1].exp().tolist()
    return sorted(range(len(docs)), key=lambda i: (-probs[i], i))
