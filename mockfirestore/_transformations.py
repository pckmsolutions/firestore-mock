from typing import Dict, Any, List
from google.cloud import firestore
from datetime import datetime
from contextlib import contextmanager
from unittest import mock

from mockfirestore._helpers import get_document_iterator, get_by_path, set_by_path, delete_by_path

@contextmanager
def mock_firestore_server_timestamp(now: datetime):
    with mock.patch(f'{__name__}.datetime') as mock_mod_datetime:
        mock_mod_datetime.now = mock.Mock(return_value = now)
        yield None

def apply_transformations(document: Dict[str, Any], data: Dict[str, Any]):
    """Handles special fields like INCREMENT."""
    increments = {}
    arr_unions = {}
    arr_deletes = {}
    deletes = []
    timestamps = []

    for key, value in list(get_document_iterator(data)):
        if isinstance(value, firestore.Increment):
            increments[key] = value.value
        elif isinstance(value, firestore.ArrayUnion):
            arr_unions[key] = value.values
        elif isinstance(value, firestore.ArrayRemove):
            arr_deletes[key] = value.values
            delete_by_path(data, key.split('.'))
        elif isinstance(value, type(firestore.DELETE_FIELD)) and str(value) == str(firestore.DELETE_FIELD):
            deletes.append(key)
            delete_by_path(data, key.split('.'))
        elif isinstance(value, type(firestore.SERVER_TIMESTAMP)) and str(value) == str(firestore.SERVER_TIMESTAMP):
            timestamps.append(key)
            delete_by_path(data, key.split('.'))

        # All other transformations can be applied as needed.
        # See #29 for tracking.

    def _update_data(new_values: dict, default: Any):
        for key, value in new_values.items():
            path = key.split('.')

            try:
                item = get_by_path(document, path)
            except (TypeError, KeyError):
                item = default

            set_by_path(data, path, item + value, create_nested=True)

    def _update_data_to(keys: list[str], value: Any):
        for key in keys:
            path = key.split(".")
            set_by_path(data, path, value, create_nested=True)

    _update_data(increments, 0)
    _update_data(arr_unions, [])
    _update_data_to(timestamps, datetime.now().isoformat())

    _apply_updates(document, data)
    _apply_deletes(document, deletes)
    _apply_arr_deletes(document, arr_deletes)


def _apply_updates(document: Dict[str, Any], data: Dict[str, Any]):
    for key, value in data.items():
        path = key.split(".")
        set_by_path(document, path, value, create_nested=True)


def _apply_deletes(document: Dict[str, Any], data: List[str]):
    for key in data:
        path = key.split(".")
        delete_by_path(document, path)


def _apply_arr_deletes(document: Dict[str, Any], data: Dict[str, Any]):
    for key, values_to_delete in data.items():
        path = key.split(".")
        try:
            value = get_by_path(document, path)
        except KeyError:
            continue
        for value_to_delete in values_to_delete:
            try:
                value.remove(value_to_delete)
            except ValueError:
                pass
        set_by_path(document, path, value)
