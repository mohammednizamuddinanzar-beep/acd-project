"""
nl_to_dsl.py — Natural Language → Business Workflow DSL Converter
==================================================================

Converts a plain-English workflow description into a valid Business
Workflow DSL source string, which is then fed into the normal compiler
pipeline unchanged:

    Natural Language
        → NLToDSLConverter.convert()    ← this module
        → DSL source string
        → compile_any_source()          ← deterministic compiler (unchanged)
        → Lexer → Parser → Semantic Analysis → IR → Execution

Architecture mirrors OptionalLLMReviewer in llm_layer.py:
  - Optional: works with or without an API key / network.
  - When disabled, returns a RuleBasedFallback DSL instead.
  - Never executes workflows directly — only produces DSL text.
  - Provider selection via environment variables or constructor args.

Supported providers (same env vars as llm_layer.py):
  AI_COMPILER_LLM_PROVIDER = openai | gemini | none
  AI_COMPILER_LLM_MODEL    = <model name>
  OPENAI_API_KEY            = sk-...
  GOOGLE_API_KEY            = AI...

Rule-based fallback is always available and requires no API key.
"""

from __future__ import annotations

import os
import re
import json
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
#  Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class NLConversionResult:
    """
    Returned by NLToDSLConverter.convert().

    Attributes:
        dsl           : The generated Business Workflow DSL source string.
        workflow_name : Extracted workflow name (used as program_name).
        method        : 'llm_openai' | 'llm_gemini' | 'rule_based'
        provider      : LLM provider name, or 'rule_based'
        model         : Model name, or 'rule_based'
        confidence    : 'high' | 'medium' | 'low'
        nl_input      : Original natural-language input (for traceability)
        notes         : Any warnings or fallback explanation
    """
    dsl: str
    workflow_name: str
    method: str
    provider: str
    model: str
    confidence: str
    nl_input: str
    notes: str = ""


# ─────────────────────────────────────────────────────────────────────────────
#  System prompt — injected into every LLM call
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a Business Workflow DSL compiler front-end.
Your ONLY job is to convert natural-language workflow descriptions into
valid Business Workflow DSL source code.

IMPORTANT RULES:
1. Output ONLY the DSL code — no explanations, no markdown fences.
2. Never execute or simulate the workflow yourself.
3. Use only these supported keywords:
       WORKFLOW <Name> { ... }
       ON <domain>.<event>
       EXTRACT <var> FROM <source>
       SET <var> = <integer>
       IF <condition> { ... }
       ELSE { ... }
       NOTIFY <recipient>
       SAVE <entity> TO <destination>
       LOG '<message>'
4. Conditions use: > < >= <= == and/or/not with integer variables.
5. Variable names: lowercase letters/numbers/underscores only.
6. Workflow name: PascalCase, no spaces.
7. Always start with WORKFLOW and end with the closing brace.
8. Every workflow MUST have exactly one ON statement.

DSL GRAMMAR (BNF):
  workflow     ::= 'WORKFLOW' Name '{' statement* '}'
  statement    ::= on | extract | set | if_stmt | notify | save | log
  on           ::= 'ON' domain '.' event
  extract      ::= 'EXTRACT' var 'FROM' source
  set          ::= 'SET' var '=' integer
  if_stmt      ::= 'IF' condition '{' statement* '}' ( 'ELSE' '{' statement* '}' )?
  condition    ::= var op literal  |  condition ('and'|'or') condition
  notify       ::= 'NOTIFY' recipient
  save         ::= 'SAVE' entity 'TO' destination
  log          ::= "LOG" "'" message "'"

EXAMPLE INPUT:
  "When an invoice arrives by email, extract the amount and notify finance
   if it is above 50000, then save it to the database."

EXAMPLE OUTPUT:
WORKFLOW InvoiceProcessing {
    ON email.received
    EXTRACT amount FROM email
    IF amount > 50000 {
        NOTIFY finance
    }
    SAVE invoice TO database
}

Now convert the following description. Output ONLY the DSL.
"""


# ─────────────────────────────────────────────────────────────────────────────
#  Rule-based fallback (no API key needed)
# ─────────────────────────────────────────────────────────────────────────────

class _RuleBasedConverter:
    """
    Lightweight regex/keyword heuristic converter.
    Produces syntactically valid DSL from common English patterns.
    Confidence is 'low' — user should review the output before compiling.
    """

    _EVENT_MAP = {
        'email':    'email.received',
        'invoice':  'invoice.received',
        'order':    'order.created',
        'payment':  'payment.initiated',
        'purchase': 'purchase.requested',
        'form':     'form.submitted',
        'request':  'request.received',
        'message':  'message.received',
        'alert':    'alert.triggered',
        'report':   'report.generated',
        'supplier': 'supplier.registered',
        'customer': 'customer.created',
        'ticket':   'ticket.opened',
    }

    _NOTIFY_PATTERNS = [
        r'notify\s+(\w+)',
        r'alert\s+(\w+)',
        r'inform\s+(\w+)',
        r'send\s+(?:a\s+)?notification\s+to\s+(\w+)',
        r'email\s+(\w+)',
    ]

    _EXTRACT_PATTERNS = [
        r'extract\s+(?:the\s+)?(\w+)',
        r'get\s+(?:the\s+)?(\w+)\s+from',
        r'read\s+(?:the\s+)?(\w+)',
        r'retrieve\s+(?:the\s+)?(\w+)',
    ]

    _SAVE_PATTERNS = [
        r'save\s+(?:it\s+)?(?:the\s+)?(\w+)?\s+to\s+(?:the\s+)?(\w+)',
        r'store\s+(?:it\s+)?(?:the\s+)?(\w+)?\s+in(?:to)?\s+(?:the\s+)?(\w+)',
        r'record\s+(?:it\s+)?(?:the\s+)?(\w+)?\s+(?:in|to)\s+(?:the\s+)?(\w+)',
        r'persist\s+(?:it\s+)?(?:the\s+)?(\w+)?\s+(?:in|to)\s+(?:the\s+)?(\w+)',
    ]

    _CONDITION_PATTERNS = [
        r'if\s+(?:it\s+is\s+)?(?:the\s+)?(\w+)\s+(?:is\s+)?(?:greater\s+than|above|exceeds?|over)\s+(\d+)',
        r'if\s+(?:it\s+is\s+)?(?:the\s+)?(\w+)\s+(?:is\s+)?(?:less\s+than|below|under)\s+(\d+)',
        r'if\s+(?:it\s+is\s+)?(?:the\s+)?(\w+)\s+(?:is\s+)?(?:equal\s+to|equals?|=)\s+(\d+)',
        r'when\s+(?:the\s+)?(\w+)\s+(?:is\s+)?(?:greater\s+than|above|exceeds?|over)\s+(\d+)',
    ]

    _OP_MAP = {
        'greater than': '>', 'above': '>', 'exceeds': '>', 'exceed': '>', 'over': '>',
        'less than': '<', 'below': '<', 'under': '<',
        'equal to': '==', 'equals': '==', 'equal': '==',
    }

    def convert(self, text: str) -> NLConversionResult:
        lower = text.lower()
        lines: list[str] = []

        # 1. Detect workflow name from first noun phrase
        wf_name = self._extract_workflow_name(text)

        # 2. Detect trigger event
        event = self._detect_event(lower)
        lines.append(f"    ON {event}")

        # 3. Detect extractions
        source_entity = event.split('.')[0]
        extractions = self._detect_extractions(lower, source_entity)
        for var, src in extractions:
            lines.append(f"    EXTRACT {var} FROM {src}")

        # 4. Detect conditions + notifications inside them
        conditions = self._detect_conditions(lower, extractions)
        notifications = self._detect_notifications(lower)
        saves = self._detect_saves(lower, extractions, source_entity)

        if conditions:
            var, op, val = conditions[0]
            notifs_in_if = notifications[:1]
            remaining_notifs = notifications[1:]
            lines.append(f"    IF {var} {op} {val} {{")
            for n in notifs_in_if:
                lines.append(f"        NOTIFY {n}")
            lines.append("    }")
            for n in remaining_notifs:
                lines.append(f"    NOTIFY {n}")
        else:
            for n in notifications:
                lines.append(f"    NOTIFY {n}")

        # 5. SAVE statements
        for entity, dest in saves:
            lines.append(f"    SAVE {entity} TO {dest}")

        body = "\n".join(lines)
        dsl = f"WORKFLOW {wf_name} {{\n{body}\n}}"

        notes = (
            "Generated by rule-based fallback (no LLM). "
            "Please review the DSL before running. "
            "Set AI_COMPILER_LLM_PROVIDER=openai or gemini for higher accuracy."
        )

        return NLConversionResult(
            dsl=dsl,
            workflow_name=wf_name,
            method='rule_based',
            provider='rule_based',
            model='rule_based',
            confidence='low',
            nl_input=text,
            notes=notes,
        )

    # ── helpers ──────────────────────────────────────────────

    def _extract_workflow_name(self, text: str) -> str:
        # Look for key nouns
        for word in ('invoice', 'payment', 'order', 'purchase', 'supplier',
                     'customer', 'ticket', 'report', 'approval', 'onboarding',
                     'request', 'alert', 'notification', 'form'):
            if word in text.lower():
                return word.capitalize() + 'Workflow'
        # Use first two capitalised words
        words = [w for w in re.findall(r'[A-Za-z]+', text) if w[0].isupper()]
        if words:
            return ''.join(words[:2]) + 'Workflow'
        return 'BusinessWorkflow'

    def _detect_event(self, lower: str) -> str:
        for keyword, event in self._EVENT_MAP.items():
            if keyword in lower:
                return event
        return 'workflow.started'

    def _detect_extractions(self, lower: str, source: str) -> list[tuple[str, str]]:
        results = []
        seen = set()
        for pat in self._EXTRACT_PATTERNS:
            for m in re.finditer(pat, lower):
                var = m.group(1)
                if var not in seen and var not in ('the', 'a', 'an', 'it', 'its', 'from'):
                    results.append((var, source))
                    seen.add(var)
        # Common implicit extractions
        for field_name in ('amount', 'total', 'quantity', 'price', 'cost',
                           'vendor', 'supplier', 'customer', 'company',
                           'name', 'email', 'status', 'id'):
            if field_name in lower and field_name not in seen:
                results.append((field_name, source))
                seen.add(field_name)
        return results[:4]   # cap at 4 extractions

    def _detect_notifications(self, lower: str) -> list[str]:
        results = []
        seen = set()
        for pat in self._NOTIFY_PATTERNS:
            for m in re.finditer(pat, lower):
                target = m.group(1)
                if target not in seen and target not in ('it', 'the', 'a', 'an', 'them'):
                    results.append(target)
                    seen.add(target)
        return results

    def _detect_conditions(self, lower: str, extractions: list | None = None) -> list[tuple[str, str, str]]:
        results = []
        # Match "if amount is above 50000" or "if it is above 50000"
        for pat in self._CONDITION_PATTERNS:
            m = re.search(pat, lower)
            if m:
                var = m.group(1)
                val = m.group(2)
                # If var is a pronoun, resolve to first extraction
                if var in ('it', 'this', 'that', 'the', 'value', 'total') and extractions:
                    var = extractions[0][0]
                # Determine operator
                op = '>'
                for kw, sym in self._OP_MAP.items():
                    if kw in lower[m.start():m.end()]:
                        op = sym
                        break
                results.append((var, op, val))
        return results

    def _detect_saves(self, lower: str, extractions: list, source: str) -> list[tuple[str, str]]:
        results = []
        seen_pairs: set = set()
        for pat in self._SAVE_PATTERNS:
            for m in re.finditer(pat, lower):
                entity = m.group(1) if m.group(1) else (extractions[0][0] if extractions else source)
                dest   = m.group(2) if m.group(2) else 'database'
                # Skip common filler words
                if entity in ('it', 'the', 'a', 'an', 'them', None):
                    entity = extractions[0][0] if extractions else source
                if dest in ('it', 'the', 'a', 'an', 'them', None):
                    dest = 'database'
                pair = (entity, dest)
                if pair not in seen_pairs:
                    results.append(pair)
                    seen_pairs.add(pair)
        # Implicit: if 'database' or 'store' mentioned without a full match
        if not results and any(w in lower for w in ('database', 'store', 'save', 'persist', 'record')):
            entity = extractions[0][0] if extractions else source
            results.append((entity, 'database'))
        return results[:3]


# ─────────────────────────────────────────────────────────────────────────────
#  Main converter class
# ─────────────────────────────────────────────────────────────────────────────

class NLToDSLConverter:
    """
    Converts natural language → Business Workflow DSL.

    Usage:
        converter = NLToDSLConverter()          # reads env vars
        result    = converter.convert(nl_text)
        # result.dsl is ready to pass to compile_any_source()

    The converter NEVER executes the resulting DSL itself.
    It only produces a source string for the deterministic pipeline.
    """

    def __init__(self,
                 provider: Optional[str] = None,
                 model: Optional[str] = None):
        self.provider = (provider or
                         os.getenv('AI_COMPILER_LLM_PROVIDER') or
                         'none').lower()
        self.model = (model or
                      os.getenv('AI_COMPILER_LLM_MODEL') or
                      self._default_model(self.provider))
        self._fallback = _RuleBasedConverter()

    # ── Public API ────────────────────────────────────────────

    def convert(self, nl_text: str) -> NLConversionResult:
        """
        Convert a natural-language description to Business Workflow DSL.

        Returns a NLConversionResult. The .dsl field is the only thing
        that should be passed to compile_any_source().
        """
        if not nl_text or not nl_text.strip():
            return NLConversionResult(
                dsl='',
                workflow_name='',
                method='none',
                provider='none',
                model='none',
                confidence='low',
                nl_input=nl_text,
                notes='Empty input — nothing to convert.',
            )

        if self.provider in ('', 'none', 'off', 'disabled', 'rule_based'):
            return self._fallback.convert(nl_text)

        try:
            if self.provider == 'openai':
                return self._convert_openai(nl_text)
            if self.provider in ('gemini', 'google'):
                return self._convert_gemini(nl_text)
            # Unknown provider → rule-based
            result = self._fallback.convert(nl_text)
            result.notes = (f"Unknown provider '{self.provider}'. "
                            "Used rule-based fallback instead. " + result.notes)
            return result
        except Exception as exc:
            result = self._fallback.convert(nl_text)
            result.notes = (f"LLM call failed ({exc}). "
                            "Used rule-based fallback instead. " + result.notes)
            return result

    # ── LLM backends ─────────────────────────────────────────

    def _convert_openai(self, nl_text: str) -> NLConversionResult:
        if not os.getenv('OPENAI_API_KEY'):
            result = self._fallback.convert(nl_text)
            result.notes = 'OPENAI_API_KEY not set — used rule-based fallback. ' + result.notes
            return result
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as e:
            raise ImportError(
                "Install optional deps: pip install langchain-openai"
            ) from e

        llm = ChatOpenAI(model=self.model, temperature=0)
        messages = [
            ('system', _SYSTEM_PROMPT),
            ('human', nl_text),
        ]
        response = llm.invoke(messages)
        raw_dsl = self._clean_llm_output(
            getattr(response, 'content', str(response))
        )
        wf_name = self._extract_name_from_dsl(raw_dsl)
        return NLConversionResult(
            dsl=raw_dsl,
            workflow_name=wf_name,
            method='llm_openai',
            provider='openai',
            model=self.model,
            confidence='high',
            nl_input=nl_text,
            notes='Generated by OpenAI LLM. Validated by deterministic compiler.',
        )

    def _convert_gemini(self, nl_text: str) -> NLConversionResult:
        if not os.getenv('GOOGLE_API_KEY'):
            result = self._fallback.convert(nl_text)
            result.notes = 'GOOGLE_API_KEY not set — used rule-based fallback. ' + result.notes
            return result
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as e:
            raise ImportError(
                "Install optional deps: pip install langchain-google-genai"
            ) from e

        llm = ChatGoogleGenerativeAI(model=self.model, temperature=0)
        prompt = _SYSTEM_PROMPT + '\n\nDescription:\n' + nl_text
        response = llm.invoke(prompt)
        raw_dsl = self._clean_llm_output(
            getattr(response, 'content', str(response))
        )
        wf_name = self._extract_name_from_dsl(raw_dsl)
        return NLConversionResult(
            dsl=raw_dsl,
            workflow_name=wf_name,
            method='llm_gemini',
            provider='gemini',
            model=self.model,
            confidence='high',
            nl_input=nl_text,
            notes='Generated by Gemini LLM. Validated by deterministic compiler.',
        )

    # ── Helpers ───────────────────────────────────────────────

    def _default_model(self, provider: str) -> str:
        if provider == 'openai':
            return 'gpt-4o-mini'
        if provider in ('gemini', 'google'):
            return 'gemini-1.5-flash'
        return 'rule_based'

    def _clean_llm_output(self, text: str) -> str:
        """Strip markdown fences and leading/trailing whitespace from LLM output."""
        text = text.strip()
        # Remove ```dsl ... ``` or ``` ... ``` fences
        text = re.sub(r'^```[a-zA-Z]*\n?', '', text)
        text = re.sub(r'\n?```$', '', text)
        # Ensure it starts with WORKFLOW
        if 'WORKFLOW' not in text.upper():
            raise ValueError("LLM did not return a WORKFLOW block. Falling back.")
        # Trim anything before WORKFLOW
        idx = text.upper().find('WORKFLOW')
        return text[idx:].strip()

    def _extract_name_from_dsl(self, dsl: str) -> str:
        m = re.match(r'WORKFLOW\s+(\w+)', dsl, re.IGNORECASE)
        return m.group(1) if m else 'BusinessWorkflow'


# ─────────────────────────────────────────────────────────────────────────────
#  Convenience function for use from main.py / CLI
# ─────────────────────────────────────────────────────────────────────────────

def nl_to_dsl(
    nl_text: str,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    verbose: bool = True,
) -> NLConversionResult:
    """
    Top-level convenience wrapper.

    Example:
        result = nl_to_dsl("When an invoice arrives, extract amount, notify finance.")
        dsl_source = result.dsl
        compile_results = compile_any_source(dsl_source, ...)
    """
    converter = NLToDSLConverter(provider=provider, model=model)
    result = converter.convert(nl_text)

    if verbose:
        W = 60
        print('\n' + '=' * W)
        print('  NATURAL LANGUAGE -> DSL CONVERSION')
        print('=' * W)
        print(f'  Method   : {result.method}')
        print(f'  Provider : {result.provider}')
        print(f'  Model    : {result.model}')
        print(f'  Confidence: {result.confidence}')
        if result.notes:
            print(f'  Notes    : {result.notes}')
        print()
        print('  Input:')
        for line in result.nl_input.splitlines():
            print(f'    {line}')
        print()
        print('  Generated DSL:')
        print('  ' + '-' * (W - 2))
        for line in result.dsl.splitlines():
            print(f'  {line}')
        print('  ' + '-' * (W - 2))

    return result
