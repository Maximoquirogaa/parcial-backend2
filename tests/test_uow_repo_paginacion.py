import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import HTTPException
from app.core.repository import BaseRepository, SoftDeleteRepository
from app.core.unit_of_work import UnitOfWork
from app.core.paginacion import ParametrosPagina, Pagina, paginar


class DummyModel:
    id = 1


class DummySoftDeleteModel:
    id = 1
    borrado_en = None


def test_base_repository_requires_model_class():
    session = MagicMock()
    with pytest.raises(ValueError):
        BaseRepository(session=session, model_cls=None)


@pytest.mark.asyncio
async def test_base_repository_add_and_update_call_flush_not_commit():
    session = AsyncMock()
    # Mock synchronous session.add as MagicMock to avoid coroutine warning
    session.add = MagicMock()
    repo = BaseRepository(session=session, model_cls=DummyModel)
    
    item = DummyModel()
    await repo.add(item)
    assert session.add.called
    assert session.flush.called
    assert not session.commit.called
    assert not session.close.called

    session.reset_mock()
    session.add = MagicMock()
    await repo.update(item)
    assert session.flush.called
    assert not session.commit.called
    assert not session.close.called


def test_soft_delete_methods_not_in_base_repository():
    base_repo = BaseRepository(session=MagicMock(), model_cls=DummyModel)
    assert not hasattr(base_repo, "soft_delete")
    assert not hasattr(base_repo, "get_by_id_including_deleted")

    soft_repo = SoftDeleteRepository(session=MagicMock(), model_cls=DummySoftDeleteModel)
    assert hasattr(soft_repo, "soft_delete")
    assert hasattr(soft_repo, "get_by_id_including_deleted")


@pytest.mark.asyncio
async def test_unit_of_work_commits_on_exit():
    session = AsyncMock()
    uow = UnitOfWork(session=session)
    async with uow:
        pass
    assert session.commit.called
    assert not session.rollback.called
    assert not session.close.called


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_on_exception():
    session = AsyncMock()
    uow = UnitOfWork(session=session)
    with pytest.raises(RuntimeError):
        async with uow:
            raise RuntimeError("Operation failed")
    assert session.rollback.called
    assert not session.commit.called
    assert not session.close.called


def test_paginacion_calculates_pages_and_rejects_out_of_range():
    # total = 0 -> pages = 1
    res = paginar(items=[], total=0, page=1, size=20)
    assert res.pages == 1
    assert res.total == 0

    # total = 5, size = 2 -> pages = 3
    res = paginar(items=[1, 2], total=5, page=1, size=2)
    assert res.pages == 3

    # page exceeds last page -> 422
    with pytest.raises(HTTPException) as exc_info:
        paginar(items=[], total=5, page=4, size=2)
    assert exc_info.value.status_code == 422


def test_paginacion_validation_constraints():
    params = ParametrosPagina(page=1, size=50)
    assert params.page == 1
    assert params.size == 50

    with pytest.raises(ValueError):
        ParametrosPagina(page=0, size=20)

    with pytest.raises(ValueError):
        ParametrosPagina(page=1, size=101)


@pytest.mark.asyncio
async def test_soft_delete_repository_marks_timestamp():
    session = AsyncMock()
    repo = SoftDeleteRepository(session=session, model_cls=DummySoftDeleteModel)
    item = DummySoftDeleteModel()
    assert item.borrado_en is None
    await repo.soft_delete(item)
    assert item.borrado_en is not None
    assert session.flush.called
