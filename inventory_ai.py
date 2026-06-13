# inventory_ai.py
import os
import io
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

OLLAMA_HOST  = os.getenv("OLLAMA_HOST",  "http://10.22.39.192:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5vl:latest")


def call_llm(prompt: str, max_tokens: int = 1024) -> str:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model":   OLLAMA_MODEL,
            "prompt":  prompt,
            "stream":  False,
            "options": {"temperature": 0.1, "num_predict": max_tokens}
        },
        timeout=120
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


def run_pandas(code: str, df_dict: dict) -> str:
    """Execute pandas code against inventory dataframes."""
    import sys
    import io
    import contextlib

    output = io.StringIO()
    local_vars = {k: v.copy() for k, v in df_dict.items()}
    local_vars["pd"] = pd

    try:
        with contextlib.redirect_stdout(output):
            exec(code, {"__builtins__": {"print": print, "len": len,
                                          "round": round, "sum": sum}},
                 local_vars)
        return output.getvalue() or "Code ran successfully, no output."
    except Exception as e:
        return f"Error: {str(e)}"


def answer_inventory_question(
    question:  str,
    inventory: pd.DataFrame,
    sales:     pd.DataFrame = None,
    suppliers: pd.DataFrame = None
) -> dict:
    """Answer natural language questions about inventory."""

    # Describe the data
    inv_desc = f"inventory dataframe 'df' with columns: {list(inventory.columns)}, {len(inventory)} rows"
    sales_desc = f"sales_history dataframe 'sales' with columns: {list(sales.columns)}" if sales is not None else ""
    sup_desc   = f"suppliers dataframe 'suppliers' with columns: {list(suppliers.columns)}" if suppliers is not None else ""

    sample = inventory.head(3).to_string()

    prompt = (
        "You are a supply chain data analyst.\n"
        "Answer this inventory question by writing pandas code.\n\n"
        f"AVAILABLE DATA:\n{inv_desc}\n{sales_desc}\n{sup_desc}\n\n"
        f"SAMPLE DATA (inventory):\n{sample}\n\n"
        f"QUESTION: {question}\n\n"
        "Write Python pandas code using 'df' for inventory, 'sales' for sales history, "
        "'suppliers' for supplier data.\n"
        "Use print() to output the answer.\n"
        "Code only, no explanation:"
    )

    code = call_llm(prompt, max_tokens=512)

    # Clean code
    if "```" in code:
        parts = code.split("```")
        for p in parts:
            if p.startswith("python"):
                code = p[6:].strip()
                break
            elif "\n" in p and "print" in p:
                code = p.strip()
                break

    # Execute
    df_dict = {"df": inventory}
    if sales     is not None: df_dict["sales"]     = sales
    if suppliers is not None: df_dict["suppliers"] = suppliers

    result = run_pandas(code, df_dict)

    # If code failed, ask LLM to answer directly
    if "Error" in result:
        fallback_prompt = (
            f"Answer this inventory question based on the data summary:\n"
            f"Total products: {len(inventory)}\n"
            f"Columns: {list(inventory.columns)}\n"
            f"Sample:\n{sample}\n\n"
            f"QUESTION: {question}\n\n"
            "Give a direct answer:"
        )
        result = call_llm(fallback_prompt, max_tokens=256)

    return {"answer": result, "code_used": code}


def generate_inventory_insights(
    inventory:  pd.DataFrame,
    anomalies:  list,
    summary:    dict
) -> str:
    """Generate executive AI insights about inventory health."""
    critical   = inventory[inventory.get("Days Until Stockout", 999) <= 7] if "Days Until Stockout" in inventory.columns else pd.DataFrame()
    top_value  = inventory.nlargest(3, "Stock Value") if "Stock Value" in inventory.columns else inventory.head(3)

    prompt = (
        "You are a supply chain consultant.\n"
        "Generate a concise executive inventory health briefing.\n\n"
        f"INVENTORY SUMMARY:\n"
        f"Total SKUs: {summary['total_skus']}\n"
        f"Total inventory value: Rs. {summary['total_value']:,.0f}\n"
        f"Critical items (< 7 days stock): {summary['critical_items']}\n"
        f"Out of stock: {summary['out_of_stock']}\n"
        f"Needs reorder: {summary['needs_reorder']}\n"
        f"Health score: {summary['health_score']}/100\n\n"
        f"CRITICAL ITEMS:\n{critical[['Product Name', 'Current Stock', 'Days Until Stockout']].to_string() if not critical.empty else 'None'}\n\n"
        f"ANOMALIES DETECTED: {len(anomalies)}\n"
        f"{chr(10).join(a['description'] for a in anomalies[:3])}\n\n"
        "Write a 4-5 sentence executive briefing covering:\n"
        "1. Overall inventory health\n"
        "2. Most urgent actions needed\n"
        "3. Key risks\n"
        "4. One strategic recommendation"
    )
    return call_llm(prompt, max_tokens=512)