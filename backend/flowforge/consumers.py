"""
WebSocket consumers do FlowForge.

WorkflowRunConsumer: entrega eventos de execução em tempo real para o cliente.
Room group: workflow_run_{run_id}
"""

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class WorkflowRunConsumer(AsyncWebsocketConsumer):
    """Consumer WebSocket para acompanhar a execução de um workflow em tempo real."""

    async def connect(self) -> None:
        """Aceita a conexão autenticada e entra no grupo da run."""
        token = self._extract_token()
        user = await self._authenticate(token)
        if user is None:
            await self.close(code=4001)
            return

        self.scope["user"] = user
        self.run_id = self.scope["url_route"]["kwargs"]["run_id"]
        self.group_name = f"workflow_run_{self.run_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        subprotocol = "flowforge.jwt" if "flowforge.jwt" in self.scope.get("subprotocols", []) else None
        await self.accept(subprotocol=subprotocol)

        # Envia snapshot do estado atual para clientes que conectam tarde
        snapshot = await self._build_snapshot()
        if snapshot:
            await self.send(text_data=json.dumps({"type": "run_snapshot", **snapshot}))

        logger.debug("WebSocket conectado: run_id=%s", self.run_id)

    async def disconnect(self, close_code: int) -> None:
        """Remove o canal do grupo ao desconectar."""
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug("WebSocket desconectado: run_id=%s code=%s", getattr(self, "run_id", ""), close_code)

    async def receive(self, text_data: str = "", bytes_data: bytes = b"") -> None:
        """Recebe mensagens do cliente (ping/keepalive — sem lógica de negócio)."""
        pass

    # -------------------------------------------------------------------------
    # Handlers de eventos — o Channels despacha pelo campo "type" do evento,
    # substituindo "." por "_" no nome do método.
    # -------------------------------------------------------------------------

    async def node_started(self, event: dict) -> None:
        """Nó iniciou execução."""
        await self.send(text_data=json.dumps(event))

    async def node_completed(self, event: dict) -> None:
        """Nó completou com sucesso."""
        await self.send(text_data=json.dumps(event))

    async def node_failed(self, event: dict) -> None:
        """Nó falhou."""
        await self.send(text_data=json.dumps(event))

    async def run_completed(self, event: dict) -> None:
        """Run completou com sucesso."""
        await self.send(text_data=json.dumps(event))

    async def run_failed(self, event: dict) -> None:
        """Run falhou."""
        await self.send(text_data=json.dumps(event))

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _extract_token(self) -> str:
        """
        Extrai o token JWT dos subprotocolos WebSocket.

        Returns:
            Token JWT informado como subprotocolo jwt.<token> ou string vazia.
        """
        for subprotocol in self.scope.get("subprotocols", []):
            if subprotocol.startswith("jwt."):
                return subprotocol.removeprefix("jwt.")
        return ""

    @database_sync_to_async
    def _authenticate(self, token: str):
        """
        Valida o JWT e retorna o usuário autenticado.

        Args:
            token: JWT enviado por subprotocolo WebSocket.

        Returns:
            Usuário autenticado ou None quando o token for inválido.
        """
        if not token:
            return None

        from rest_framework_simplejwt.authentication import JWTAuthentication

        authenticator = JWTAuthentication()
        try:
            validated_token = authenticator.get_validated_token(token)
            return authenticator.get_user(validated_token)
        except Exception:
            return None

    @database_sync_to_async
    def _build_snapshot(self) -> dict | None:
        """
        Constrói snapshot do estado atual da run para clients que conectam tarde.

        Returns:
            Dict com node_executions e run status, ou None se run não existir.
        """
        from flowforge.models import NodeExecution, Run

        try:
            run = Run.objects.get(id=self.run_id)
        except Run.DoesNotExist:
            return None

        if run.status == Run.Status.PENDING:
            return None

        node_executions = list(
            NodeExecution.objects.filter(run=run).values(
                "node_id",
                "status",
                "output_data",
                "error_message",
                "duration_ms",
                "execution_order",
            )
        )

        return {
            "run_status": run.status,
            "nodes_completed": run.nodes_completed,
            "nodes_total": run.nodes_total,
            "node_executions": [
                {
                    "node_id": str(ne["node_id"]),
                    "status": ne["status"],
                    "output_data": ne["output_data"],
                    "error_message": ne["error_message"],
                    "duration_ms": ne["duration_ms"],
                    "execution_order": ne["execution_order"],
                }
                for ne in node_executions
            ],
        }
