import json


CONTRACT = "contracts/deliverable_verifier.py"


def deploy(direct_deploy):
    # genlayer-test 0.29.x still downloads the legacy universal bundle name.
    return direct_deploy(CONTRACT, sdk_version="v0.2.16")


def create_default_submission(contract):
    contract.create_submission(
        "brief-1",
        "Release checklist",
        "The deliverable must contain a release checklist and a rollback plan.",
        "https://example.com/release-checklist",
    )


def test_create_and_read_submission(direct_vm, direct_deploy, direct_alice):
    contract = deploy(direct_deploy)
    direct_vm.sender = direct_alice

    create_default_submission(contract)

    submission = contract.get_submission("brief-1")
    assert submission["id"] == "brief-1"
    assert submission["title"] == "Release checklist"
    assert submission["status"] == "pending"
    assert submission["passed"] is False
    assert submission["submitter"].lower() == f"0x{direct_alice.hex()}"

    assert contract.get_submission_ids() == {"0": "brief-1"}


def test_duplicate_submission_ids_revert(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    create_default_submission(contract)

    with direct_vm.expect_revert("Submission ID already exists"):
        create_default_submission(contract)


def test_invalid_submission_input_reverts(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy(direct_deploy)
    direct_vm.sender = direct_alice

    with direct_vm.expect_revert("deliverable_url must start"):
        contract.create_submission(
            "brief-1",
            "Release checklist",
            "A checklist",
            "ftp://example.com/file",
        )

    with direct_vm.expect_revert("requirements is required"):
        contract.create_submission(
            "brief-2",
            "Release checklist",
            "   ",
            "https://example.com/release-checklist",
        )


def test_evaluation_updates_state_from_mocked_web_and_llm(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    create_default_submission(contract)

    direct_vm.mock_web(
        r"https://example\.com/release-checklist",
        {
            "status": 200,
            "body": (
                "Release checklist\n"
                "Rollback plan: restore the previous version within 15 minutes."
            ),
        },
    )
    direct_vm.mock_llm(
        r"(?s).*Release checklist.*rollback plan.*",
        json.dumps(
            {
                "passed": True,
                "score": 94,
                "summary": "The deliverable includes both required sections.",
                "evidence": "It includes a release checklist and a rollback plan.",
            }
        ),
    )

    contract.evaluate_submission("brief-1")

    submission = contract.get_submission("brief-1")
    assert submission["status"] == "approved"
    assert submission["passed"] is True
    assert submission["score"] == 94
    assert "both required sections" in submission["summary"]


def test_evaluation_can_reject_a_deliverable(
    direct_vm, direct_deploy, direct_alice
):
    contract = deploy(direct_deploy)
    direct_vm.sender = direct_alice
    create_default_submission(contract)

    direct_vm.mock_web(
        r"https://example\.com/release-checklist",
        {"status": 200, "body": "A release note without a rollback plan."},
    )
    direct_vm.mock_llm(
        r"(?s).*Release checklist.*rollback plan.*",
        json.dumps(
            {
                "passed": False,
                "score": 28,
                "summary": "The rollback plan is missing.",
                "evidence": "The page contains a release note only.",
            }
        ),
    )

    contract.evaluate_submission("brief-1")

    submission = contract.get_submission("brief-1")
    assert submission["status"] == "rejected"
    assert submission["passed"] is False
    assert submission["score"] == 28
