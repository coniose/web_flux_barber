"""BarberStore — contexto de acesso ao Firestore de um usuário."""

from __future__ import annotations

from dataclasses import dataclass

from google.cloud.firestore import Client, CollectionReference


@dataclass
class BarberStore:
    db: Client
    device_id: str

    def col(self, name: str) -> CollectionReference:
        """Retorna a subcoleção do usuário: barbearias/{device_id}/{name}."""
        return (
            self.db.collection("barbearias")
            .document(self.device_id)
            .collection(name)
        )
