from __future__ import annotations

from pathlib import Path

from core.dynamodb_contract import (
    GSI1_INDEX_NAME,
    GSI1_PARTITION_KEY,
    GSI1_PROJECTION_TYPE,
    GSI1_SORT_KEY,
)
from core.keys import (
    base_keys,
    outbox_status_pk,
    outbox_status_sk,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_gsi1_constants_match_table_terraform():
    table_source = (
        REPOSITORY_ROOT / "infra" / "data.tf"
    ).read_text()

    assert 'hash_key  = "pk"' in table_source
    assert 'range_key = "sk"' in table_source
    assert f'name = "{GSI1_PARTITION_KEY}"' in table_source
    assert f'name = "{GSI1_SORT_KEY}"' in table_source
    assert f'name = "{GSI1_INDEX_NAME}"' in table_source
    assert f'attribute_name = "{GSI1_PARTITION_KEY}"' in table_source
    assert f'attribute_name = "{GSI1_SORT_KEY}"' in table_source
    assert 'key_type       = "HASH"' in table_source
    assert 'key_type       = "RANGE"' in table_source
    assert (
        f'projection_type = "{GSI1_PROJECTION_TYPE}"'
        in table_source
    )


def test_all_global_secondary_indexes_use_key_schema():
    table_source = (
        REPOSITORY_ROOT / "infra" / "data.tf"
    ).read_text()

    gsi_source = table_source.split("global_secondary_index", 1)[1]
    assert "hash_key" not in gsi_source
    assert "range_key" not in gsi_source
    assert gsi_source.count("key_schema {") == 4


def test_entity_base_keys_populate_sparse_gsi_keys():
    keys = base_keys(
        pk="USER#user-123",
        sk="RESUME#analysis-123",
        entity_id="analysis-123",
        record_type="resumeAnalysis",
    )

    assert keys == {
        "pk": "USER#user-123",
        "sk": "RESUME#analysis-123",
        GSI1_PARTITION_KEY: "ENTITY#analysis-123",
        GSI1_SORT_KEY: "resumeAnalysis",
    }


def test_outbox_status_key_contract_is_deterministic():
    assert (
        outbox_status_pk("PENDING")
        == "OUTBOX_STATUS#PENDING"
    )
    assert outbox_status_sk(
        created_at="2026-07-18T19:00:00+00:00",
        event_id="event-123",
    ) == "2026-07-18T19:00:00+00:00#event-123"
