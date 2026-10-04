"""Real provider deltas; incomplete turns never mutate facts or stored messages."""
import asyncio
import json
import logging
import re
from contextlib import aclosing

import httpx
from packages.model_adapter.client import structured_options

from packages.chat.service import current_model_config, turn_prompt, validate_turn, research_query, WorkflowError


def reply_prefix(raw: str) -> str:
    """Read only the top-level JSON reply string, tolerating a partial escape."""
    decoder = json.JSONDecoder()
    rest = raw.lstrip()
    if not rest.startswith('{'):
        return ''
    rest = rest[1:].lstrip()
    try:
        while rest:
            key, end = decoder.raw_decode(rest)
            rest = rest[end:].lstrip()
            if not rest.startswith(':'):
                return ''
            rest = rest[1:].lstrip()
            if key == 'reply':
                if not rest.startswith('"'):
                    return ''
                try:
                    value, _ = decoder.raw_decode(rest)
                    return value if isinstance(value, str) else ''
                except ValueError:
                    # At most a surrogate pair can be unfinished at a chunk boundary.
                    for trim in range(13):
                        candidate = rest if trim == 0 else rest[:-trim]
                        try:
                            value = json.loads(candidate + '"')
                            value.encode('utf-8')
                            return value
                        except (ValueError, UnicodeError):
                            continue
                    return ''
            _, end = decoder.raw_decode(rest)
            rest = rest[end:].lstrip()
            if not rest.startswith(','):
                return ''
            rest = rest[1:].lstrip()
    except ValueError:
        pass
    return ''


async def _model_turn_once(doc, text):
    cfg = current_model_config()
    if not cfg.is_configured:
        raise WorkflowError('model_not_configured')
    system, user = turn_prompt(doc, text)
    payload = {'model': cfg.model_name, 'messages': [
        {'role': 'system', 'content': system}, {'role': 'user', 'content': user}],
        'temperature': 0, 'max_tokens': 3500, 'stream': True,
        'response_format': {'type': 'json_object'}}
    payload.update(structured_options(cfg))
    raw, shown = '', ''
    complete = False
    try:
        async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
            async with client.stream('POST', cfg.base_url + '/chat/completions',
                                     headers={'Authorization': 'Bearer ' + cfg.api_key}, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith('data:'):
                        continue
                    value = line[5:].strip()
                    if value == '[DONE]':
                        break
                    data = json.loads(value)
                    choices = data.get('choices', [])
                    if not choices:
                        continue
                    item = choices[0]
                    if item.get('finish_reason') == 'stop':
                        complete = True
                    raw += item.get('delta', {}).get('content') or ''
                    if len(raw) > 40000:
                        raise ValueError('Excessive turn')
                    prefix = reply_prefix(raw)
                    visible = re.search(r'"intent"\s*:\s*"(chat|intake)"', raw)
                    if visible and prefix.startswith(shown) and len(prefix) > len(shown):
                        yield {'type': 'delta', 'text': prefix[len(shown):]}
                        shown = prefix
        if not complete:
            raise ValueError('Incomplete turn')
        yield {'type': 'turn', 'turn': validate_turn(json.loads(raw), text)}
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError) as exc:
        logging.getLogger(__name__).warning('stream_failure stage=%s', type(exc).__name__)
        raise WorkflowError('model_failed') from None


async def model_turn(doc, text):
    for attempt in range(2):
        try:
            async with aclosing(_model_turn_once(doc, text)) as stream:
                async for event in stream:
                    yield event
            return
        except WorkflowError as exc:
            if exc.code != 'model_failed' or attempt:
                raise
            yield {'type': 'reset'}


async def events(service, doc, owner, revision, request_id, text, disconnected,
                 entry_hint='auto', reply_to_question_id=None, data_approved=True):
    # Ordinary HTTP and SSE use the same graph. Never expose unvalidated route text.
    turn = None
    if getattr(service, 'streamer', None) and service.orchestration != 'hybrid':
        async with aclosing(service.streamer(doc, text)) as stream:
            async for event in stream:
                if await disconnected():
                    return
                if event['type'] == 'turn':
                    turn = event['turn']
    if await disconnected():
        return
    prepared = await asyncio.to_thread(service.prepare_turn, owner, doc, request_id, text, turn,
                                       entry_hint=entry_hint, reply_to_question_id=reply_to_question_id)
    prepared['payload_hash'] = service.message_hash(text, data_approved, entry_hint, reply_to_question_id)
    if await disconnected():
        return
    result = await asyncio.to_thread(service.commit_prepared, owner, doc, revision, request_id, text, prepared)
    # The complete validated answer is now authoritative; A accepts done-only SSE.
    yield {'type': 'done', 'case': result}
