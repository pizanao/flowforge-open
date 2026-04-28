"""
Validação de DAG do FlowForge.

Detecta ciclos via DFS com coloração (white/gray/black)
e identifica nós não alcançáveis a partir do trigger.
"""

from collections import defaultdict
from typing import Any


def validate_dag(workflow_id: str) -> dict[str, Any]:
    """
    Valida se o grafo do workflow é um DAG válido.

    Verifica:
    - Existência de exatamente um nó trigger
    - Ausência de ciclos (DFS com white/gray/black)
    - Nós não alcançáveis a partir do trigger

    Args:
        workflow_id: UUID do workflow a validar.

    Returns:
        Dict com chaves ``valid`` (bool) e ``errors``
        (lista de dicts ``{node_id, message}``).
    """
    from flowforge.models import Node, Edge, Workflow

    try:
        workflow = Workflow.objects.get(pk=workflow_id)
    except Workflow.DoesNotExist:
        return {"valid": False, "errors": [{"node_id": None, "message": "Workflow não encontrado."}]}

    nodes = list(workflow.nodes.all())
    edges = list(workflow.edges.all())

    if not nodes:
        return {"valid": False, "errors": [{"node_id": None, "message": "O workflow não possui nós."}]}

    node_map = {str(n.id): n for n in nodes}
    errors: list[dict] = []

    # ── 1. Trigger único ──────────────────────────────────────────────────────
    triggers = [n for n in nodes if n.node_type == "trigger"]
    if len(triggers) == 0:
        errors.append({"node_id": None, "message": "O workflow não possui nenhum nó trigger."})
    elif len(triggers) > 1:
        for t in triggers[1:]:
            errors.append({"node_id": str(t.id), "message": "Nó trigger duplicado — só pode existir um trigger por workflow."})

    # ── 2. Grafo de adjacência ────────────────────────────────────────────────
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        src = str(edge.source_node_id)
        tgt = str(edge.target_node_id)
        if src in node_map and tgt in node_map:
            adjacency[src].append(tgt)

    # ── 3. Detecção de ciclos via DFS (white/gray/black) ─────────────────────
    color = {nid: "white" for nid in node_map}
    cycle_nodes: set[str] = set()

    def dfs(nid: str) -> bool:
        """Retorna True se detectar ciclo."""
        color[nid] = "gray"
        for neighbor in adjacency[nid]:
            if color[neighbor] == "gray":
                cycle_nodes.add(neighbor)
                return True
            if color[neighbor] == "white":
                if dfs(neighbor):
                    cycle_nodes.add(nid)
                    return True
        color[nid] = "black"
        return False

    for nid in node_map:
        if color[nid] == "white":
            dfs(nid)

    for nid in cycle_nodes:
        errors.append({"node_id": nid, "message": f"Nó pertence a um ciclo — o workflow não é um DAG válido."})

    # ── 4. Nós não alcançáveis ────────────────────────────────────────────────
    unreachable = find_unreachable_nodes(workflow_id, node_map=node_map, adjacency=adjacency, triggers=triggers)
    for nid in unreachable:
        errors.append({"node_id": nid, "message": "Nó não alcançável a partir do trigger."})

    return {"valid": len(errors) == 0, "errors": errors}


def find_unreachable_nodes(
    workflow_id: str,
    *,
    node_map: dict | None = None,
    adjacency: dict | None = None,
    triggers: list | None = None,
) -> list[str]:
    """
    Retorna IDs de nós não alcançáveis a partir do trigger.

    Pode receber estruturas pré-computadas para evitar queries extras
    quando chamado de ``validate_dag()``.

    Args:
        workflow_id: UUID do workflow.
        node_map: Mapa id→Node (opcional, evita query extra).
        adjacency: Grafo de adjacência id→[ids] (opcional).
        triggers: Lista de nós trigger (opcional).

    Returns:
        Lista de UUIDs (str) dos nós não alcançáveis.
    """
    from flowforge.models import Node, Edge, Workflow

    if node_map is None or adjacency is None or triggers is None:
        try:
            workflow = Workflow.objects.get(pk=workflow_id)
        except Workflow.DoesNotExist:
            return []

        nodes = list(workflow.nodes.all())
        edges = list(workflow.edges.all())
        node_map = {str(n.id): n for n in nodes}
        adjacency = defaultdict(list)
        for edge in edges:
            src = str(edge.source_node_id)
            tgt = str(edge.target_node_id)
            if src in node_map and tgt in node_map:
                adjacency[src].append(tgt)
        triggers = [n for n in nodes if n.node_type == "trigger"]

    if not triggers:
        return list(node_map.keys())

    # BFS/DFS a partir do trigger
    trigger_id = str(triggers[0].id)
    visited: set[str] = set()
    stack = [trigger_id]

    while stack:
        nid = stack.pop()
        if nid in visited:
            continue
        visited.add(nid)
        for neighbor in adjacency[nid]:
            if neighbor not in visited:
                stack.append(neighbor)

    unreachable = [nid for nid in node_map if nid not in visited and nid != trigger_id]
    return unreachable
