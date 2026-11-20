"""Contracts: validation, acceptance checks, idempotency keys."""

from airlangga.contracts import AcceptanceCheck, Contract, Report, check_acceptance, validate_report


def _contract(**overrides):
    data = {"goal": "do the thing", "team_id": "t1", "member_id": "m1"}
    data.update(overrides)
    return Contract(**data)


def test_idempotency_key_is_deterministic():
    c1 = _contract(id="c1")
    c2 = _contract(id="c1")
    assert c1.idempotency_key == c2.idempotency_key
    assert c1.idempotency_key.startswith("c1-")


def test_report_contract_mismatch_is_an_error():
    contract = _contract(id="c1")
    report = Report(contract_id="other", member_id="m1")
    assert validate_report(report, contract)


def test_schema_acceptance_requires_fields():
    contract = _contract(
        acceptance=AcceptanceCheck(kind="schema", required_fields=["claims"])
    )
    report = Report(contract_id=contract.id, member_id="m1")
    passed, _ = check_acceptance(contract, report)
    assert passed


def test_shell_acceptance_pass_and_fail():
    good = _contract(acceptance=AcceptanceCheck(kind="shell", command=["true"]))
    report = Report(contract_id=good.id, member_id="m1")
    assert check_acceptance(good, report)[0] is True
    bad = _contract(acceptance=AcceptanceCheck(kind="shell", command=["false"]))
    assert check_acceptance(bad, report)[0] is False


def test_judge_fail_rejects():
    contract = _contract(acceptance=AcceptanceCheck(kind="judge"))
    report = Report(contract_id=contract.id, member_id="m1", verdict_self="fail")
    assert check_acceptance(contract, report)[0] is False
