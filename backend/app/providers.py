"""Provider boundary: explicit demo only; external adapters fail closed."""
import os
from typing import Protocol
from fastapi import HTTPException
class Provider(Protocol):
    def generate(self,scenario:str,title:str)->dict:...
class MockDemoProvider:
    def generate(self,scenario,title):
        outcome={'success':'success','failure':'failed','timeout':'timeout','invalid':'invalid_output','abstain':'abstained'}[scenario]
        return {'outcome':outcome,'action':{'text':'DEMO — ตรวจทบทวนเอกสาร: '+title+'; ผู้ตรวจต้องตรวจหลักฐานต้นฉบับก่อนรับรอง'} if outcome=='success' else None,'demo':True}
class UnconfiguredProvider:
    def __init__(self,name):self.name=name
    def generate(self,*args):raise HTTPException(503,detail={'code':'LIVE_PROVIDER_NOT_CONFIGURED','provider':self.name,'outcome':'not_written','fallback':False})
def resolve_provider():
    provider=os.getenv('HIS_AI_PROVIDER','mock_demo')
    if provider=='mock_demo':return MockDemoProvider()
    # Cloud/dr-train/local require a future adapter, verified identity, policy AND budget.
    raise HTTPException(503,detail={'code':'LIVE_PROVIDER_NOT_CONFIGURED','provider':provider,'outcome':'not_written','fallback':False})
