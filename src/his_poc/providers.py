"""Provider boundary. No network, SDK or live provider is enabled in this starter."""
from typing import Protocol

class ProviderError(Exception):
    pass

class Provider(Protocol):
    def generate(self, request: dict) -> dict: ...

class MockProvider:
    name = 'mock'
    revision = 'synthetic_fixture_v1'
    def generate(self, request):
        scenario = request.get('scenario', 'success')
        if scenario == 'timeout': raise TimeoutError('simulated timeout')
        if scenario == 'failure': raise ProviderError('simulated provider failure')
        if scenario == 'invalid': return {'malformed': True}
        if scenario == 'abstain': return {'outcome': 'abstained', 'reason': 'synthetic insufficient evidence'}
        return {'outcome': 'success', 'action': {'kind': 'document_completeness',
            'summary': 'DEMO: ตรวจทานความครบถ้วนเอกสารเท่านั้น',
            'missing_fields': [x for x in ('author', 'signed_at') if not request['document'].get(x)]}}

def resolve_provider(config, data_class):
    # Fail before outbound calls. No SDK/network implementation exists here.
    if data_class != 'synthetic': raise ProviderError('DATA_POLICY_DENIED')
    if config.get('inference_profile') != 'mock_demo' or config.get('provider', 'mock') != 'mock': raise ProviderError('LIVE_PROVIDER_NOT_IMPLEMENTED')
    return MockProvider()
