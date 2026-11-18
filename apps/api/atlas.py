"""Authenticated tax atlas routes within the existing application."""
from fastapi import APIRouter, Depends, HTTPException, Query

from apps.api.auth import required_user
from packages.chat.library_cloud import LibraryVersionChanged
from packages.domain_bridge import atlas_service, tax_atlas

router = APIRouter(prefix='/api/atlas', dependencies=[Depends(required_user)])


async def respond(operation, **selectors):
    try:
        return await atlas_service.query({'operation': operation, **selectors})
    except LibraryVersionChanged:
        raise HTTPException(409, 'atlas_snapshot_changed') from None
    except Exception:
        raise HTTPException(503, 'atlas_unavailable') from None


def checked_date(value):
    try:
        return tax_atlas.today(value)
    except ValueError:
        raise HTTPException(422, 'invalid_atlas_date') from None


@router.get('/map')
async def map_data(date: str = Query(default='', max_length=10)):
    return await respond('map', date=checked_date(date))


@router.get('/country/{code}')
async def country(code: str, date: str = Query(default='', max_length=10)):
    if code not in tax_atlas.ISO:
        raise HTTPException(404, 'atlas_not_found')
    return await respond('country', code=code, date=checked_date(date))


@router.get('/glossary')
async def glossary():
    return await respond('glossary')


@router.get('/clause')
async def clause(cite_id: str = Query(min_length=3, max_length=240,
                                     pattern=r'^[a-zA-Z0-9_.-]+#[a-zA-Z0-9_.()/-]+$')):
    return await respond('clause', cite_id=cite_id)
