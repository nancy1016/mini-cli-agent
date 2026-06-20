from jobhunt.missing import (
    check_all_missing_info,
    check_application_missing_fields,
    check_interview_missing_fields,
    is_missing,
)
from jobhunt.models import Application, Interview


def test_is_missing_values():
    assert is_missing(None) is True
    assert is_missing("") is True
    assert is_missing("   ") is True
    assert is_missing("待补充") is True
    assert is_missing("上海") is False


def test_application_required_and_recommended_missing_fields():
    application = Application(
        id=1,
        company="待补充",
        position="",
        location=None,
        apply_source=None,
    )

    missing = check_application_missing_fields(application)

    assert missing["required"] == ["company", "position"]
    assert missing["recommended"] == ["location", "apply_source"]


def test_application_apply_link_recommended_for_official_source():
    application = Application(
        id=1,
        company="Acme",
        position="Backend Engineer",
        apply_source="官网网申",
        apply_link="",
    )

    missing = check_application_missing_fields(application)

    assert "apply_link" in missing["recommended"]


def test_interview_required_and_recommended_missing_fields():
    interview = Interview(
        id=1,
        application_id=1,
        company="",
        position="待补充",
        stage="一面",
        interview_time=None,
        interview_method="腾讯会议",
        meeting_link="",
    )

    missing = check_interview_missing_fields(interview)

    assert missing["required"] == ["company", "position", "interview_time"]
    assert missing["recommended"] == ["meeting_link"]


def test_check_all_missing_info_groups_results_by_record():
    application = Application(
        id=1,
        company="Acme",
        position="Backend Engineer",
        location=None,
        apply_source="官网",
        apply_link=None,
    )
    interview = Interview(
        id=2,
        application_id=1,
        company="Acme",
        position="Backend Engineer",
        stage="一面",
        interview_time="待补充",
        interview_method="线上",
        meeting_link=None,
    )

    result = check_all_missing_info([application], [interview])

    assert result["applications"] == [
        {
            "id": 1,
            "missing": {
                "required": [],
                "recommended": ["location", "apply_link"],
            },
        }
    ]
    assert result["interviews"] == [
        {
            "id": 2,
            "application_id": 1,
            "missing": {
                "required": ["interview_time"],
                "recommended": ["meeting_link"],
            },
        }
    ]
