from mockfirestore.client import MockFirestore
from typing import AsyncIterator
from google.cloud import firestore
import inspect
from mockfirestore.document import DocumentReference
from mockfirestore.collection import CollectionReference

class AsyncCollectionReference:
    def __init__(self, collection_reference: CollectionReference):
        _async_proxy_methods(
                source = self,
                target = collection_reference,
                model = firestore.AsyncCollectionReference,
                wrap_name_type_dict = {
                    'document': AsyncDocumentReference,
                    'order_by': AsyncCollectionReference,
                    'limit': AsyncCollectionReference,
                    'start_after': AsyncCollectionReference,
                    }
                )

class AsyncDocumentReference:
    def __init__(self, document_reference: DocumentReference):
        _async_proxy_methods(
                source = self,
                target = document_reference,
                model = firestore.AsyncDocumentReference,
                wrap_name_type_dict = {
                    'collection': AsyncCollectionReference
                    }
                )

class AsyncMockFirestore(MockFirestore):
    def collection(self, path: str) -> AsyncCollectionReference:
        return AsyncCollectionReference(super().collection(path))

def _async_proxy_methods(
        source,
        target,
        model,
        wrap_name_type_dict: dict[str, type] | None = None):
    wrap_name_type_dict = wrap_name_type_dict or {}
    for member_name, member_type in inspect.getmembers(model):
        if wrap_type := wrap_name_type_dict.get(member_name):
            _async_wrap_method(source, target, member_name, wrap_type)
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

def _async_wrap_method(you, target, method_name: str, wrap_type: type):
    def wrapper(*args, **kwargs):
        return wrap_type(getattr(target, method_name)(*args, **kwargs))
    setattr(you, method_name, wrapper)
