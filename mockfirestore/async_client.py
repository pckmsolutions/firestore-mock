from mockfirestore.client import MockFirestore
from typing import AsyncIterator, Any
from google.cloud import firestore
import inspect
from mockfirestore.document import DocumentReference, DocumentSnapshot
from mockfirestore.collection import CollectionReference
from mockfirestore._helpers import get_by_path

class AsyncCollectionReference:
    def __init__(self, collection_reference: CollectionReference):
        _async_proxy_methods(
                source = self,
                target = collection_reference,
                model = firestore.AsyncCollectionReference,
                wrap_name_type_dict = {
                    'document': (AsyncDocumentReference,False),
                    'order_by': (AsyncCollectionReference,False),
                    'limit': (AsyncCollectionReference,False),
                    'start_after': (AsyncCollectionReference,False),
                    }
                )

class AsyncDocumentReference:
    def __init__(self, document_reference: DocumentReference):

        _async_proxy_methods(
                source = self,
                target = document_reference,
                model = firestore.AsyncDocumentReference,
                wrap_name_type_dict = {
                    'collection': (AsyncCollectionReference,False),
                    }
                )
        self.document_reference = document_reference

        async def get_wrapper(*args, **kwargs):
            return DocumentSnapshot(self, get_by_path(document_reference._data, document_reference._path))
        setattr(self, 'get', get_wrapper)

class Batch:
    def __init__(self):
        self.ops = []

    def set(self, ref: AsyncDocumentReference, data: dict[str, Any]):
        self.ops.append(('set', ref, data))

    async def commit(self):
        for op_meth, op_p1, op_p2 in self.ops:
            if op_meth == 'set':
                await op_p1.set(op_p2)

class AsyncMockFirestore(MockFirestore):
    def collection(self, path: str) -> AsyncCollectionReference:
        return AsyncCollectionReference(super().collection(path))

    def batch(self):
        return Batch()

def _async_proxy_methods(
        source,
        target,
        model,
        wrap_name_type_dict: dict[str, tuple[type, bool]] | None = None):
    wrap_name_type_dict = wrap_name_type_dict or {}
    for member_name, member_type in inspect.getmembers(model):
        if wrap_type_is_async := wrap_name_type_dict.get(member_name):
            _async_wrap_method(source, target, member_name, wrap_type_is_async[0], wrap_type_is_async[1])
            continue
        target_method = getattr(target, member_name, None)
        if not target_method:
            continue
        if proxy_method := _get_proxy_method(target_method, member_type):
            setattr(source, member_name, proxy_method)

def _get_proxy_method(target_method, model_member_type):
    if inspect.isasyncgenfunction(model_member_type):
        async def proxy_method(*args, **kwargs):
            for d in target_method(*args, **kwargs):
                yield d
        return proxy_method
    if inspect.iscoroutinefunction(model_member_type):
        async def proxy_method(*args, **kwargs):
            return target_method(*args, **kwargs)
        return proxy_method
    if inspect.isfunction(model_member_type):
        return target_method
    if isinstance(model_member_type, property):
        return target_method

def _async_wrap_method(you, target, method_name: str, wrap_type: type, is_async: bool):
    if is_async:
        async def wrapper(*args, **kwargs):
            return wrap_type(getattr(target, method_name)(*args, **kwargs))
    else:
        def wrapper(*args, **kwargs):
            return wrap_type(getattr(target, method_name)(*args, **kwargs))
    setattr(you, method_name, wrapper)
