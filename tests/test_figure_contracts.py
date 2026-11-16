import pytest

from scripts.check_figures import validate_declaration


def declaration():
    return {
        "semantic_kind": "timeline",
        "expected_title": "Execution timeline",
        "required_labels": ["Milliseconds"],
        "plots_values": True,
        "measurement_kind": "live measurement",
        "manual_readability_review": {
            key: "pending_human_review"
            for key in ["arrow_direction", "overlap", "text_legibility", "mechanism_communicated"]
        },
    }


def test_value_figures_require_measurement_semantics():
    valid = declaration()
    validate_declaration(valid)
    with pytest.raises(ValueError, match="measurement kind"):
        validate_declaration({**valid, "measurement_kind": None})


def test_pixel_checks_do_not_replace_manual_review_fields():
    valid = declaration()
    with pytest.raises(ValueError, match="Manual readability"):
        validate_declaration({**valid, "manual_readability_review": {}})
