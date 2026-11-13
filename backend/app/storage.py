"""Content-addressed development storage; authorization remains at the API boundary."""
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
import hashlib,os,re,tempfile

@dataclass(frozen=True)
class StoredObject:
    key:str
    sha256:str
    size:int

class FileStore(Protocol):
    def put(self,content:bytes)->StoredObject: ...
    def read(self,key:str,expected_sha256:str)->bytes: ...

class LocalFileStore:
    def __init__(self,root:Path):self.root=root.resolve()
    def put(self,content:bytes)->StoredObject:
        digest=hashlib.sha256(content).hexdigest();key=digest+'.bin'
        self.root.mkdir(parents=True,exist_ok=True)
        dest=self.root/key
        if dest.exists():self.read(key,digest)
        else:
            fd,path=tempfile.mkstemp(prefix='.upload-',dir=self.root)
            try:
                with os.fdopen(fd,'wb') as f:f.write(content);f.flush();os.fsync(f.fileno())
                os.replace(path,dest)
            finally:
                if os.path.exists(path):os.unlink(path)
        return StoredObject(key,digest,len(content))
    def read(self,key,expected_sha256):
        if not re.fullmatch(r'[a-f0-9]{64}\.bin',key):raise ValueError('Invalid object key')
        file=self.root/key
        if file.is_symlink():raise ValueError('Symlinks are not storage objects')
        content=file.read_bytes()
        if hashlib.sha256(content).hexdigest()!=expected_sha256:raise ValueError('Stored object checksum mismatch')
        return content

def file_store()->FileStore:
    provider=os.environ.get('FILE_STORAGE_PROVIDER','local')
    if provider!='local':raise RuntimeError('Object storage is NOT_CONFIGURED; no fallback is permitted')
    return LocalFileStore(Path(os.environ.get('FILE_STORAGE_ROOT','var/files')))
