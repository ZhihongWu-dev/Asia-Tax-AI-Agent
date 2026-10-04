"""Validated orchestration proposals; never an authority to mutate case state."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from packages.agent.providers import ROOT

EntryHint = Literal['auto', 'dividend_consultation', 'fact_intake', 'reference_lookup']
TaskKind = Literal['consultation', 'fact_intake', 'reference_lookup']


class TaskProposal(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kind: TaskKind
    query: str = Field(default='', max_length=500)
    uses_case: bool = False
    jurisdiction: str | None = Field(default=None, max_length=40)
    topic: str | None = Field(default=None, max_length=40)

    @field_validator('jurisdiction')
    @classmethod
    def normalize_jurisdiction(cls, value):
        if value and value.strip().casefold() in ('hk', 'hong kong', '香港'):
            return 'HK'
        return value

    @field_validator('topic')
    @classmethod
    def normalize_topic(cls, value):
        if value and value.strip().casefold() in ('fsie', 'dividend', 'dividends', '股息', '境外股息'):
            return 'fsie' if value.strip().casefold() == 'fsie' else 'dividend'
        return value


class NextAction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['finish', 'lookup_reference', 'prepare_analysis']
    query: str = Field(default='', max_length=500)


class OrchestrationSettings(BaseSettings):
    orchestration: Literal['legacy', 'hybrid'] = 'legacy'
    dynamic_planner: bool = False
    harness_mode: Literal['rewrite', 'tools'] = 'rewrite'
    model_config = SettingsConfigDict(env_prefix='FSIE_AGENT_', env_file=ROOT / '.env', extra='ignore')


def options(entry_hint='auto', reply_to_question_id=None):
    from pydantic import TypeAdapter
    TypeAdapter(EntryHint).validate_python(entry_hint)
    if reply_to_question_id is not None and (not isinstance(reply_to_question_id, str) or
                                             not 1 <= len(reply_to_question_id) <= 200):
        raise ValueError('Invalid question reference')
    return {'entry_hint': entry_hint, 'reply_to_question_id': reply_to_question_id}
