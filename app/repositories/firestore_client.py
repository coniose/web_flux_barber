"""Singleton do cliente Firestore.

Lê credenciais de:
  FIREBASE_CREDENTIALS_JSON — conteúdo JSON (Railway/produção)
  GOOGLE_APPLICATION_CREDENTIALS — caminho para o arquivo JSON (dev local)
"""

from __future__ import annotations

import json
import os
from typing import Optional

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import Client

_client: Optional[Client] = None


def get_firestore_client() -> Client:
    global _client
    if _client is not None:
        return _client

    if not firebase_admin._apps:
        creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
        creds_file = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

        if creds_json:
            cred = credentials.Certificate(json.loads(creds_json))
        elif creds_file:
            cred = credentials.Certificate(creds_file)
        else:
            raise RuntimeError(
                "Firebase: configure FIREBASE_CREDENTIALS_JSON (Railway) "
                "ou GOOGLE_APPLICATION_CREDENTIALS (local)."
            )
        firebase_admin.initialize_app(cred)

    _client = firestore.client()
    return _client
