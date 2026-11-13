"""Explicit mock and opt-in private Ollama provider. Never silently falls back."""
from __future__ import annotations
from dataclasses import dataclass
import asyncio
import ipaddress
import json
import math
import os
import re
import time
from typing import Protocol
from urllib.parse import urlsplit
import httpx
from fastapi import HTTPException
from pydantic import ValidationError
from .document_completeness import (
    CHECKLIST_ID, PROMPT_VERSION, SYSTEM_PROMPT, action_for, input_envelope,
    json_canonical, output_schema, sha256, validate_report,
)

class Provider(Protocol):
    def generate(self, scenario: str, title: str) -> dict: ...

class MockDemoProvider:
    name = 'mock_demo'
    demo = True
    is_live = False

    def generate(self, scenario, title):
        outcome = {'success': 'success', 'failure': 'failed', 'timeout': 'timeout',
                   'invalid': 'invalid_output', 'abstain': 'abstained'}[scenario]
        return {'outcome': outcome, 'action': {'text': 'DEMO — ตรวจทบทวนเอกสาร: ' + title +
                '; ผู้ตรวจต้องตรวจหลักฐานต้นฉบับก่อนรับรอง'} if outcome == 'success' else None, 'demo': True}

    def public_config(self):
        return {'active_provider': self.name, 'demo': True, 'live_routes_enabled': False}

class ProviderFailure(Exception):
    """Only fixed, credential-free codes escape this boundary."""

@dataclass(frozen=True)
class OllamaSettings:
    base_url: str
    model: str
    model_digest: str
    engine_version: str
    timeout_seconds: float = 180
    max_output_tokens: int = 1024
    context_tokens: int = 4096
    max_document_chars: int = 6000
    keep_alive_seconds: int = 0

    def __post_init__(self):
        url = urlsplit(self.base_url)
        if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('', '/'):
            raise ValueError('INVALID_PRIVATE_ENDPOINT')
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError('INVALID_PRIVATE_ENDPOINT_PORT')
        if url.scheme == 'http':
            try:
                address = ipaddress.ip_address(url.hostname)
                allowed = address.is_private or address.is_loopback or address in ipaddress.ip_network('100.64.0.0/10')
            except ValueError:
                allowed = url.hostname in ('localhost', 'host.docker.internal', 'dr-train')
            if not allowed:
                raise ValueError('PLAINTEXT_ENDPOINT_NOT_PRIVATE')
        if not self.model or len(self.model) > 250 or any(c.isspace() for c in self.model):
            raise ValueError('MODEL_REQUIRED')
        if not re.fullmatch('[a-f0-9]{64}', self.model_digest):
            raise ValueError('MODEL_DIGEST_REQUIRED')
        if not re.fullmatch(r'\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.]+)?', self.engine_version):
            raise ValueError('ENGINE_VERSION_REQUIRED')
        if not math.isfinite(self.timeout_seconds) or not 5 <= self.timeout_seconds <= 300:
            raise ValueError('TIMEOUT_OUT_OF_RANGE')
        if not 256 <= self.max_output_tokens <= 1536 or not 2048 <= self.context_tokens <= 8192:
            raise ValueError('TOKEN_LIMIT_OUT_OF_RANGE')
        if not 1 <= self.max_document_chars <= 8000 or not 0 <= self.keep_alive_seconds <= 60:
            raise ValueError('RESOURCE_LIMIT_OUT_OF_RANGE')

    @classmethod
    def from_env(cls):
        if os.getenv('HIS_LIVE_SYNTHETIC_ENABLED', '').lower() != 'true':
            raise ValueError('LIVE_SYNTHETIC_OPT_IN_REQUIRED')
        return cls(base_url=os.getenv('DR_TRAIN_BASE_URL', '').rstrip('/'),
                   model=os.getenv('DR_TRAIN_MODEL', ''), model_digest=os.getenv('DR_TRAIN_MODEL_DIGEST', ''),
                   engine_version=os.getenv('DR_TRAIN_OLLAMA_VERSION', ''),
                   timeout_seconds=float(os.getenv('DR_TRAIN_TIMEOUT_SECONDS', '180')),
                   max_output_tokens=int(os.getenv('DR_TRAIN_MAX_OUTPUT_TOKENS', '1024')),
                   context_tokens=int(os.getenv('DR_TRAIN_CONTEXT_TOKENS', '4096')),
                   max_document_chars=int(os.getenv('DR_TRAIN_MAX_DOCUMENT_CHARS', '6000')),
                   keep_alive_seconds=int(os.getenv('DR_TRAIN_KEEP_ALIVE_SECONDS', '0')))

class DrTrainOllamaProvider:
    name = 'dr_train_ollama'
    demo = False
    is_live = True

    def __init__(self, settings: OllamaSettings, *, transport=None):
        self.settings = settings
        self.transport = transport

    def public_config(self):
        s = self.settings
        return {'active_provider': self.name, 'demo': False, 'live_routes_enabled': True,
                'use_case': 'document_completeness', 'data_class': 'synthetic',
                'checklist_id': CHECKLIST_ID, 'model': s.model, 'model_digest': s.model_digest,
                'engine': 'ollama', 'engine_version': s.engine_version,
                'max_document_chars': s.max_document_chars, 'max_output_tokens': s.max_output_tokens,
                'context_tokens': s.context_tokens, 'input_budget_policy': 'conservative_utf8_bytes',
                'supported_task_kinds': ['document_review'],
                'verification_status': 'CONFIGURED_NOT_PROBED',
                'requires_human_review': True}

    @staticmethod
    async def _json(client, method, path, *, payload=None, limit=262144, deadline=None):
        remaining = deadline - time.monotonic() if deadline is not None else 180
        if remaining <= 0:
            raise httpx.ReadTimeout('Provider deadline reached')
        timeout = httpx.Timeout(remaining, connect=min(5, remaining), write=min(10, remaining), pool=min(5, remaining))
        async with client.stream(method, path, json=payload, timeout=timeout) as response:
            if response.status_code != 200:
                raise ProviderFailure('PROVIDER_HTTP_REJECTED')
            if 'application/json' not in response.headers.get('content-type', '').lower():
                raise ProviderFailure('PROVIDER_RESPONSE_NOT_JSON')
            content = bytearray()
            async for chunk in response.aiter_bytes():
                if deadline is not None and time.monotonic() > deadline:
                    raise httpx.ReadTimeout('Provider deadline reached')
                content.extend(chunk)
                if len(content) > limit:
                    raise ProviderFailure('PROVIDER_RESPONSE_TOO_LARGE')
        try:
            value = json.loads(content)
        except (ValueError, UnicodeError):
            raise ProviderFailure('PROVIDER_RESPONSE_INVALID_JSON') from None
        if not isinstance(value, dict):
            raise ProviderFailure('PROVIDER_RESPONSE_NOT_OBJECT')
        return value

    async def _verify_identity(self, client, deadline=None):
        version = (await self._json(client, 'GET', '/api/version', deadline=deadline)).get('version')
        if version != self.settings.engine_version:
            raise ProviderFailure('ENGINE_IDENTITY_MISMATCH')
        models = (await self._json(client, 'GET', '/api/tags', deadline=deadline)).get('models')
        if not isinstance(models, list):
            raise ProviderFailure('MODEL_INVENTORY_INVALID')
        matches = [m for m in models if isinstance(m, dict) and m.get('name') == self.settings.model]
        if len(matches) != 1 or matches[0].get('digest') != self.settings.model_digest:
            raise ProviderFailure('MODEL_IDENTITY_MISMATCH')
        if not isinstance(matches[0].get('details', {}), dict):
            raise ProviderFailure('MODEL_DETAILS_INVALID')
        return matches[0]

    async def _network(self, envelope, schema, provenance, result, deadline):
        """One absolute deadline cancels the active transport, including dribble reads.

        Cancelling/closing our HTTP request does not establish server-side inference
        cancellation. That remains an independently unverified capability.
        """
        s = self.settings
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('Provider deadline reached')
        async with asyncio.timeout(remaining):
            timeout = httpx.Timeout(s.timeout_seconds, connect=5, pool=5, write=10)
            async with httpx.AsyncClient(base_url=s.base_url, timeout=timeout, follow_redirects=False,
                                         trust_env=False, transport=self.transport) as client:
                inventory = await self._verify_identity(client, deadline)
                show = await self._json(client, 'POST', '/api/show', payload={'model': s.model, 'verbose': False}, limit=2097152, deadline=deadline)
                capabilities = show.get('capabilities')
                if not isinstance(capabilities, list) or 'completion' not in capabilities:
                    raise ProviderFailure('TEXT_COMPLETION_NOT_DECLARED')
                template = show.get('template')
                if not isinstance(template, str) or not template:
                    raise ProviderFailure('CHAT_TEMPLATE_IDENTITY_MISSING')
                provenance.update(chat_template_sha256=sha256(template), template_sha256=sha256(template),
                                  parameters_sha256=sha256(str(show.get('parameters', ''))),
                                  model_details={key: value for key, value in (inventory.get('details') or {}).items()
                                                 if key in ('format', 'family', 'families', 'parameter_size', 'quantization_level')},
                                  declared_capabilities=[value for value in capabilities
                                                         if value in ('completion', 'vision', 'tools', 'thinking', 'embedding')])
                response = await self._json(client, 'POST', '/api/chat', payload={
                    'model': s.model, 'stream': False, 'format': schema,
                    'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                                 {'role': 'user', 'content': envelope}],
                    'options': {'temperature': 0, 'seed': 0, 'num_ctx': s.context_tokens,
                                'num_predict': s.max_output_tokens},
                    'keep_alive': s.keep_alive_seconds,
                }, deadline=deadline)
                usage_fields = ('prompt_eval_count', 'eval_count', 'total_duration', 'load_duration',
                                'prompt_eval_duration', 'eval_duration')
                result['usage'] = {key: value for key in usage_fields
                                   if isinstance((value := response.get(key)), int) and not isinstance(value, bool) and value >= 0} or None
                provenance['response_sha256'] = sha256(json_canonical(response))
                await self._verify_identity(client, deadline)
                return response

    def generate_document(self, title: str, content: str, checklist_id=CHECKLIST_ID) -> dict:
        """Network work only: callers must release every database transaction first."""
        started = time.monotonic()
        s = self.settings
        deadline = started + s.timeout_seconds
        schema = output_schema()
        envelope = input_envelope(title, content) if isinstance(title, str) and isinstance(content, str) else ''
        provenance = {'provider': self.name, 'model': s.model, 'model_digest': s.model_digest,
                      'engine': 'ollama', 'engine_version': s.engine_version,
                      'prompt_version': PROMPT_VERSION, 'system_prompt_sha256': sha256(SYSTEM_PROMPT),
                      'input_sha256': sha256(envelope), 'schema_sha256': sha256(json_canonical(schema)),
                      'checklist_id': checklist_id, 'temperature': 0, 'seed': 0,
                      'num_ctx': s.context_tokens, 'num_predict': s.max_output_tokens,
                      'keep_alive_seconds': s.keep_alive_seconds, 'data_class': 'synthetic',
                      'artifact_revision': 'ollama_manifest_digest', 'hf_revision': None}
        result = {'provider': self.name, 'demo': False, 'outcome': 'failed', 'action': None,
                  'reason': None, 'provenance': provenance, 'usage': None, 'measured_cost': None}
        try:
            if checklist_id != CHECKLIST_ID:
                raise ProviderFailure('CHECKLIST_NOT_SUPPORTED')
            if not isinstance(title, str) or len(title) > 200 or not isinstance(content, str) or not content.strip() or len(content) > s.max_document_chars:
                raise ProviderFailure('DOCUMENT_INPUT_LIMIT_EXCEEDED')
            # Conservative byte upper bound prevents silently truncating source
            # evidence inside a fixed-size model context window.
            if len((SYSTEM_PROMPT + envelope).encode('utf-8')) + 512 + s.max_output_tokens > s.context_tokens:
                raise ProviderFailure('DOCUMENT_CONTEXT_BUDGET_EXCEEDED')
            response = asyncio.run(self._network(envelope, schema, provenance, result, deadline))
            if response.get('model') != s.model or response.get('done') is not True:
                raise ProviderFailure('INFERENCE_RESPONSE_IDENTITY_OR_COMPLETION_INVALID')
            if response.get('done_reason') != 'stop':
                raise ProviderFailure('INFERENCE_STOP_REASON_NOT_COMPLETE')
            if result['usage'] and result['usage'].get('prompt_eval_count', 0) + s.max_output_tokens > s.context_tokens:
                raise ProviderFailure('INFERENCE_CONTEXT_BUDGET_EXCEEDED')
            message = response.get('message')
            if not isinstance(message, dict) or message.get('role') != 'assistant' or message.get('tool_calls'):
                raise ProviderFailure('ASSISTANT_RESPONSE_INVALID')
            report = validate_report(message.get('content'), content)
            if all(item['status'] == 'unclear' for item in report['items']):
                result.update(outcome='abstained', reason='NO_RELIABLE_DOCUMENT_EVIDENCE')
            else:
                result.update(outcome='success', action=action_for(report))
        except (httpx.TimeoutException, TimeoutError):
            result.update(outcome='timeout', reason='PROVIDER_TIMEOUT')
        except httpx.HTTPError:
            result.update(outcome='failed', reason='PROVIDER_CONNECTION_FAILED')
        except ProviderFailure as error:
            output_errors = {'INFERENCE_RESPONSE_IDENTITY_OR_COMPLETION_INVALID',
                             'INFERENCE_STOP_REASON_NOT_COMPLETE', 'ASSISTANT_RESPONSE_INVALID',
                             'INFERENCE_CONTEXT_BUDGET_EXCEEDED'}
            result.update(outcome='invalid_output' if str(error) in output_errors else 'failed', reason=str(error))
        except (ValueError, TypeError, ValidationError):
            result.update(outcome='invalid_output', reason='DOCUMENT_CHECKLIST_OUTPUT_INVALID')
        finally:
            result['elapsed_ms'] = round((time.monotonic() - started) * 1000)
        return result

class UnconfiguredProvider:
    def __init__(self, name):
        self.name = name

    def generate(self, *args):
        raise HTTPException(503, detail={'code': 'LIVE_PROVIDER_NOT_CONFIGURED',
                            'provider': self.name, 'outcome': 'not_written', 'fallback': False})

def resolve_provider():
    provider = os.getenv('HIS_AI_PROVIDER', 'mock_demo')
    if provider == 'mock_demo':
        return MockDemoProvider()
    if provider == 'dr_train_ollama':
        try:
            return DrTrainOllamaProvider(OllamaSettings.from_env())
        except (ValueError, TypeError, OverflowError):
            raise HTTPException(503, detail={'code': 'LIVE_PROVIDER_NOT_CONFIGURED',
                                'provider': provider, 'outcome': 'not_written', 'fallback': False}) from None
    raise HTTPException(503, detail={'code': 'LIVE_PROVIDER_NOT_CONFIGURED',
                        'provider': provider, 'outcome': 'not_written', 'fallback': False})
