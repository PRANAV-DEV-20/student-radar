from sqlalchemy import select

from app.api.v1.dossiers import _PUBLIC_DOSSIER_LOAD
from app.models.dossier import ProjectDossier


def test_public_dossier_queries_do_not_select_vector_columns():
    """Read-only dossier feeds must not load pgvector columns.

    Selecting the vector columns forces pgvector's shared library to load in
    the backend process. On the native Windows install this has caused stale
    pooled connections to fail with `attempt to redefine parameter
    "hnsw.ef_search"`.
    """
    statement = select(ProjectDossier).options(*_PUBLIC_DOSSIER_LOAD)
    compiled = str(statement.compile(compile_kwargs={"literal_binds": True}))

    assert "embedding" not in compiled
    assert "missing_roles_embedding" not in compiled
