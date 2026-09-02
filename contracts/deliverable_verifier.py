# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from dataclasses import dataclass

from genlayer import *


ERROR_EXPECTED = "[EXPECTED]"
ERROR_EXTERNAL = "[EXTERNAL]"
ERROR_TRANSIENT = "[TRANSIENT]"
ERROR_LLM = "[LLM_ERROR]"

MAX_TITLE_LENGTH = 120
MAX_REQUIREMENTS_LENGTH = 4000
MAX_URL_LENGTH = 2000
MAX_SOURCE_LENGTH = 12000
MAX_SUMMARY_LENGTH = 600
MAX_EVIDENCE_LENGTH = 1200


@allow_storage
@dataclass
class Submission:
    id: str
    submitter: Address
    title: str
    requirements: str
    deliverable_url: str
    status: str
    score: u256
    passed: bool
    summary: str
    evidence: str


class DeliverableVerifier(gl.Contract):
    """Evaluate public deliverables against plain-English requirements.

    The contract stores the minimum authoritative state: the submitted brief,
    the source URL, and the consensus-backed evaluation. A UI can provide
    previews and indexing, but only this contract can finalize the result.
    """

    submissions: TreeMap[str, Submission]
    submission_order: DynArray[str]

    def __init__(self):
        pass

    def _require_text(self, value: str, field_name: str, max_length: int) -> None:
        if not value or not value.strip():
            raise gl.vm.UserError(f"{ERROR_EXPECTED} {field_name} is required")
        if len(value) > max_length:
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} {field_name} exceeds {max_length} characters"
            )

    def _require_url(self, deliverable_url: str) -> None:
        self._require_text(deliverable_url, "deliverable_url", MAX_URL_LENGTH)
        if not (
            deliverable_url.startswith("https://")
            or deliverable_url.startswith("http://")
        ):
            raise gl.vm.UserError(
                f"{ERROR_EXPECTED} deliverable_url must start with http:// or https://"
            )

    def _get_submission(self, submission_id: str) -> Submission:
        if submission_id not in self.submissions:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Submission not found")
        return self.submissions[submission_id]

    def _submission_to_dict(self, submission: Submission) -> dict:
        return {
            "id": submission.id,
            "submitter": submission.submitter.as_hex,
            "title": submission.title,
            "requirements": submission.requirements,
            "deliverable_url": submission.deliverable_url,
            "status": submission.status,
            "score": submission.score,
            "passed": submission.passed,
            "summary": submission.summary,
            "evidence": submission.evidence,
        }

    def _parse_bool(self, raw_value) -> bool:
        if isinstance(raw_value, bool):
            return raw_value
        if isinstance(raw_value, str):
            normalized = raw_value.strip().lower()
            if normalized in ("true", "passed", "yes"):
                return True
            if normalized in ("false", "failed", "no"):
                return False
        raise gl.vm.UserError(f"{ERROR_LLM} passed must be a boolean")

    def _parse_evaluation(self, raw_result) -> dict:
        if isinstance(raw_result, str):
            try:
                raw_result = json.loads(raw_result)
            except Exception:
                raise gl.vm.UserError(f"{ERROR_LLM} Response was not valid JSON")

        if not isinstance(raw_result, dict):
            raise gl.vm.UserError(f"{ERROR_LLM} Response was not an object")

        raw_passed = raw_result.get("passed")
        if raw_passed is None:
            raw_passed = raw_result.get("approved")
        passed = self._parse_bool(raw_passed)

        raw_score = raw_result.get("score")
        if raw_score is None:
            raw_score = raw_result.get("confidence")
        try:
            score = int(str(raw_score).strip())
        except (TypeError, ValueError):
            raise gl.vm.UserError(f"{ERROR_LLM} score must be an integer")
        if score < 0 or score > 100:
            raise gl.vm.UserError(f"{ERROR_LLM} score must be between 0 and 100")

        summary = raw_result.get("summary")
        if summary is None:
            summary = raw_result.get("reasoning")
        if summary is None:
            summary = raw_result.get("analysis")
        evidence = raw_result.get("evidence")
        if evidence is None:
            evidence = raw_result.get("source_evidence")

        summary = str(summary or "").strip()
        evidence = str(evidence or "").strip()
        if not summary or not evidence:
            raise gl.vm.UserError(
                f"{ERROR_LLM} summary and evidence are required"
            )

        return {
            "passed": passed,
            "score": score,
            "summary": summary[:MAX_SUMMARY_LENGTH],
            "evidence": evidence[:MAX_EVIDENCE_LENGTH],
        }

    def _run_evaluation(
        self, title: str, requirements: str, deliverable_url: str
    ) -> dict:
        response = gl.nondet.web.get(deliverable_url)
        if response.status >= 400 and response.status < 500:
            raise gl.vm.UserError(
                f"{ERROR_EXTERNAL} Deliverable returned HTTP {response.status}"
            )
        if response.status >= 500:
            raise gl.vm.UserError(
                f"{ERROR_TRANSIENT} Deliverable returned HTTP {response.status}"
            )

        source = response.body.decode("utf-8")
        if not source.strip():
            raise gl.vm.UserError(f"{ERROR_EXTERNAL} Deliverable was empty")
        source = source[:MAX_SOURCE_LENGTH]

        prompt = f"""
You are an impartial reviewer for an on-chain deliverable verification system.

Deliverable title:
{title}

Requirements:
{requirements}

Public deliverable content fetched from {deliverable_url}:
{source}

Decide whether the public deliverable satisfies the requirements. Use only the
content provided above. Return JSON only, with exactly these fields:
{{
  "passed": true or false,
  "score": integer from 0 to 100,
  "summary": "brief explanation of the decision",
  "evidence": "specific evidence from the deliverable"
}}
"""

        return self._parse_evaluation(
            gl.nondet.exec_prompt(prompt, response_format="json")
        )

    def _evaluate_with_consensus(
        self, title: str, requirements: str, deliverable_url: str
    ) -> dict:
        def leader_fn() -> dict:
            return self._run_evaluation(title, requirements, deliverable_url)

        def validator_fn(leaders_res: gl.vm.Result) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            try:
                leader = self._parse_evaluation(leaders_res.calldata)
                validator = self._run_evaluation(
                    title, requirements, deliverable_url
                )
            except gl.vm.UserError:
                return False

            return (
                leader["passed"] == validator["passed"]
                and abs(leader["score"] - validator["score"]) <= 15
            )

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    @gl.public.write
    def create_submission(
        self,
        submission_id: str,
        title: str,
        requirements: str,
        deliverable_url: str,
    ) -> None:
        self._require_text(submission_id, "submission_id", 100)
        self._require_text(title, "title", MAX_TITLE_LENGTH)
        self._require_text(requirements, "requirements", MAX_REQUIREMENTS_LENGTH)
        self._require_url(deliverable_url)

        if submission_id in self.submissions:
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Submission ID already exists")

        submission = Submission(
            id=submission_id,
            submitter=gl.message.sender_address,
            title=title.strip(),
            requirements=requirements.strip(),
            deliverable_url=deliverable_url.strip(),
            status="pending",
            score=0,
            passed=False,
            summary="",
            evidence="",
        )
        self.submissions[submission_id] = submission
        self.submission_order.append(submission_id)

    @gl.public.write
    def evaluate_submission(self, submission_id: str) -> None:
        submission = self._get_submission(submission_id)
        if submission.status != "pending":
            raise gl.vm.UserError(f"{ERROR_EXPECTED} Submission already evaluated")

        evaluation = self._evaluate_with_consensus(
            submission.title,
            submission.requirements,
            submission.deliverable_url,
        )
        submission.status = "approved" if evaluation["passed"] else "rejected"
        submission.score = evaluation["score"]
        submission.passed = evaluation["passed"]
        submission.summary = evaluation["summary"]
        submission.evidence = evaluation["evidence"]

    @gl.public.view
    def get_submission(self, submission_id: str) -> dict:
        return self._submission_to_dict(self._get_submission(submission_id))

    @gl.public.view
    def get_submission_ids(self) -> dict:
        return {
            str(index): self.submission_order[index]
            for index in range(len(self.submission_order))
        }
