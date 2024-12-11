import pytest
from pydantic import ValidationError

from scim2_models import PatchOp
from scim2_models import PatchOperation


def test_validate_patchop_case_insensitivith():
    """Validate that a patch operation's Op declaration is case-insensitive."""
    assert PatchOp.model_validate(
        {
            "operations": [
                {"op": "Replace", "path": "userName", "value": "Rivard"},
                {"op": "ADD", "path": "userName", "value": "Rivard"},
                {"op": "ReMove", "path": "userName", "value": "Rivard"},
            ],
        },
    ) == PatchOp(
        operations=[
            PatchOperation(
                op=PatchOperation.Op.replace_, path="userName", value="Rivard"
            ),
            PatchOperation(op=PatchOperation.Op.add, path="userName", value="Rivard"),
            PatchOperation(
                op=PatchOperation.Op.remove, path="userName", value="Rivard"
            ),
        ]
    )
    with pytest.raises(
        ValidationError,
        match="1 validation error for PatchOp",
    ):
        PatchOp.model_validate(
            {
                "operations": [{"op": 42, "path": "userName", "value": "Rivard"}],
            },
        )
